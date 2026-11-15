"""End-to-end API tests covering auth, RBAC, the order lifecycle, returns, reminders and AI scoping."""

import types

import pytest

from app.tasks import scan_for_stale_orders


def first_dishes(client, restaurant_id=1, n=2):
    r = client.get(f"/restaurants/{restaurant_id}/menu")
    assert r.status_code == 200
    return r.json()["items"][:n]


def place(client, headers, restaurant_id=1, qty=2):
    dishes = first_dishes(client, restaurant_id)
    body = {
        "items": [{"menu_item_id": d["id"], "quantity": qty} for d in dishes],
        "delivery_address": "Hostel 3, Room 214",
    }
    r = client.post("/orders", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json(), dishes


def walk_to_ready(client, owner, order_id):
    for st in ("ACCEPTED", "PREPARING", "READY"):
        r = client.patch(f"/owner/orders/{order_id}/status", json={"status": st}, headers=owner)
        assert r.status_code == 200, r.text


# ---------- auth ----------
def test_register_login_and_me(client):
    r = client.post(
        "/auth/register", json={"name": "New Student", "email": "new@campusbite.dev", "password": "Secret123!"}
    )
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "customer"
    # duplicate email
    assert client.post(
        "/auth/register", json={"name": "Again", "email": "NEW@campusbite.dev", "password": "Secret123!"}
    ).status_code == 409
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "new@campusbite.dev"


def test_bad_login_and_missing_token(client):
    assert client.post("/auth/login", json={"email": "customer@campusbite.dev", "password": "wrong"}).status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_owner_registration_creates_restaurant(client):
    r = client.post(
        "/auth/register",
        json={
            "name": "New Owner",
            "email": "newowner@campusbite.dev",
            "password": "Secret123!",
            "role": "restaurant_owner",
            "restaurant_name": "Pop-up Pizza",
        },
    )
    assert r.status_code == 201
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/owner/restaurant", headers=h).json()["name"] == "Pop-up Pizza"
    # restaurant name is mandatory for owners
    bad = client.post(
        "/auth/register",
        json={"name": "X Y", "email": "x@campusbite.dev", "password": "Secret123!", "role": "restaurant_owner"},
    )
    assert bad.status_code == 422


# ---------- RBAC ----------
def test_role_enforcement(client, customer, owner1, driver1):
    assert client.get("/owner/orders", headers=customer).status_code == 403
    assert client.get("/delivery/orders", headers=customer).status_code == 403
    assert client.get("/orders", headers=owner1).status_code == 403
    assert client.post("/ai/insights", json={}, headers=driver1).status_code == 403
    assert client.post("/owner/menu", json={"name": "x", "price": 5}, headers=customer).status_code == 403
    assert client.get("/orders").status_code == 401


# ---------- menu search / filter ----------
def test_menu_search_and_price_filter(client):
    r = client.get("/restaurants/1/menu", params={"q": "dal"})
    assert [i["name"] for i in r.json()["items"]] == ["Dal Tadka"]
    r = client.get("/restaurants/1/menu", params={"min_price": 100, "max_price": 150})
    assert all(100 <= i["price"] <= 150 for i in r.json()["items"]) and r.json()["total"] >= 2
    r = client.get("/restaurants", params={"page_size": 2})
    assert r.json()["page_size"] == 2 and len(r.json()["items"]) == 2 and r.json()["total"] >= 3


# ---------- order placement ----------
def test_place_order_dummy_payment(client, customer):
    order, dishes = place(client, customer)
    assert order["status"] == "PLACED"
    assert order["payment_status"] == "mock_paid"
    assert len(order["payments"]) == 1 and order["payments"][0]["entry_type"] == "mock_payment"
    assert order["total_amount"] == pytest.approx(sum(d["price"] * 2 for d in dishes))


def test_order_must_use_single_restaurant_and_available_items(client, customer, owner1):
    d1 = first_dishes(client, 1, 1)[0]
    d2 = first_dishes(client, 2, 1)[0]
    r = client.post(
        "/orders",
        json={"items": [{"menu_item_id": d1["id"], "quantity": 1}, {"menu_item_id": d2["id"], "quantity": 1}],
              "delivery_address": "Hostel 3"},
        headers=customer,
    )
    assert r.status_code == 400

    client.patch(f"/owner/menu/{d1['id']}/availability", json={"is_available": False}, headers=owner1)
    r = client.post(
        "/orders",
        json={"items": [{"menu_item_id": d1["id"], "quantity": 1}], "delivery_address": "Hostel 3"},
        headers=customer,
    )
    assert r.status_code == 400 and "unavailable" in r.json()["detail"].lower()
    client.patch(f"/owner/menu/{d1['id']}/availability", json={"is_available": True}, headers=owner1)


# ---------- cancellation ----------
def test_cancel_only_when_placed(client, customer, owner1):
    order, _ = place(client, customer)
    oid = order["id"]
    client.patch(f"/owner/orders/{oid}/status", json={"status": "ACCEPTED"}, headers=owner1)
    assert client.post(f"/orders/{oid}/cancel", headers=customer).status_code == 400

    order2, _ = place(client, customer)
    r = client.post(f"/orders/{order2['id']}/cancel", headers=customer)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    # cancelled orders cannot be accepted
    assert client.patch(
        f"/owner/orders/{order2['id']}/status", json={"status": "ACCEPTED"}, headers=owner1
    ).status_code == 400


# ---------- full lifecycle + all the guards ----------
def test_full_lifecycle_and_transition_rules(client, customer, owner1, owner2, driver1, driver2):
    order, _ = place(client, customer)
    oid = order["id"]

    # invalid jumps are rejected
    assert client.patch(f"/owner/orders/{oid}/status", json={"status": "READY"}, headers=owner1).status_code == 400
    assert client.patch(f"/owner/orders/{oid}/status", json={"status": "DELIVERED"}, headers=owner1).status_code == 400
    # another restaurant's owner cannot touch it
    assert client.patch(f"/owner/orders/{oid}/status", json={"status": "ACCEPTED"}, headers=owner2).status_code == 404

    walk_to_ready(client, owner1, oid)

    # assignment needs a real delivery partner
    assert client.post(f"/owner/orders/{oid}/assign", json={"delivery_partner_id": 1}, headers=owner1).status_code == 404
    partners = client.get("/owner/delivery-partners", headers=owner1).json()
    d1_id = next(p["id"] for p in partners if p["name"] == "Dev Driver")
    r = client.post(f"/owner/orders/{oid}/assign", json={"delivery_partner_id": d1_id}, headers=owner1)
    assert r.status_code == 200 and r.json()["status"] == "ASSIGNED"

    # re-assigning a non-READY order fails
    assert client.post(f"/owner/orders/{oid}/assign", json={"delivery_partner_id": d1_id}, headers=owner1).status_code == 400

    # driver 2 sees nothing and cannot act; driver 1 sees it
    assert client.get("/delivery/orders", headers=driver2).json()["total"] == 0
    assert client.patch(f"/delivery/orders/{oid}/status", json={"status": "OUT_FOR_DELIVERY"}, headers=driver2).status_code == 404
    assert client.get("/delivery/orders", headers=driver1).json()["total"] >= 1
    # can't skip OUT_FOR_DELIVERY
    assert client.patch(f"/delivery/orders/{oid}/status", json={"status": "DELIVERED"}, headers=driver1).status_code == 400

    r = client.patch(f"/delivery/orders/{oid}/status", json={"status": "OUT_FOR_DELIVERY"}, headers=driver1)
    assert r.status_code == 200 and r.json()["customer"]["name"] == "Demo Customer"
    r = client.patch(f"/delivery/orders/{oid}/status", json={"status": "DELIVERED"}, headers=driver1)
    assert r.status_code == 200 and r.json()["status"] == "DELIVERED"

    # delivered orders cannot be cancelled
    assert client.post(f"/orders/{oid}/cancel", headers=customer).status_code == 400
    # partner history
    assert any(o["id"] == oid for o in client.get("/delivery/history", headers=driver1).json()["items"])

    # review: only after delivery, once
    assert client.post(f"/orders/{oid}/review", json={"rating": 5, "comment": "Great"}, headers=customer).status_code == 201
    assert client.post(f"/orders/{oid}/review", json={"rating": 4}, headers=customer).status_code == 409
    assert client.post(f"/orders/{oid}/review", json={"rating": 9}, headers=customer).status_code == 422
    assert client.get("/restaurants/1/reviews").json()["total"] >= 1

    stats = client.get("/owner/stats", headers=owner1).json()
    assert stats["delivered_revenue"] > 0 and stats["review_count"] >= 1 and stats["average_rating"] == 5


def test_review_requires_delivery(client, customer):
    order, _ = place(client, customer)
    assert client.post(f"/orders/{order['id']}/review", json={"rating": 5}, headers=customer).status_code == 400
    assert client.post(f"/orders/{order['id']}/return", json={"reason": "not delivered yet"}, headers=customer).status_code == 400


# ---------- returns / refunds ----------
def _deliver(client, customer, owner1, driver1):
    order, _ = place(client, customer)
    oid = order["id"]
    walk_to_ready(client, owner1, oid)
    d1_id = next(p["id"] for p in client.get("/owner/delivery-partners", headers=owner1).json() if p["name"] == "Dev Driver")
    client.post(f"/owner/orders/{oid}/assign", json={"delivery_partner_id": d1_id}, headers=owner1)
    client.patch(f"/delivery/orders/{oid}/status", json={"status": "OUT_FOR_DELIVERY"}, headers=driver1)
    client.patch(f"/delivery/orders/{oid}/status", json={"status": "DELIVERED"}, headers=driver1)
    return oid


def test_return_approve_flow(client, customer, owner1, owner2, driver1):
    oid = _deliver(client, customer, owner1, driver1)
    assert client.post(f"/orders/{oid}/return", json={"reason": "bad"}, headers=customer).status_code == 422  # too short
    r = client.post(f"/orders/{oid}/return", json={"reason": "Food arrived cold"}, headers=customer)
    assert r.status_code == 200 and r.json()["return_status"] == "requested"
    # no duplicate requests
    assert client.post(f"/orders/{oid}/return", json={"reason": "Food arrived cold"}, headers=customer).status_code == 409
    assert client.get("/owner/returns", headers=owner1).json()["total"] >= 1
    # other restaurant can't decide it
    assert client.post(f"/owner/orders/{oid}/return/approve", headers=owner2).status_code == 404

    r = client.post(f"/owner/orders/{oid}/return/approve", headers=owner1)
    body = r.json()
    assert r.status_code == 200
    assert body["return_status"] == "approved" and body["payment_status"] == "refunded" and body["status"] == "REFUNDED"
    assert [p["entry_type"] for p in body["payments"]] == ["mock_payment", "refund"]
    # can't be decided twice
    assert client.post(f"/owner/orders/{oid}/return/reject", headers=owner1).status_code == 400


def test_return_reject_flow(client, customer, owner1, driver1):
    oid = _deliver(client, customer, owner1, driver1)
    client.post(f"/orders/{oid}/return", json={"reason": "Changed my mind"}, headers=customer)
    r = client.post(f"/owner/orders/{oid}/return/reject", headers=owner1)
    assert r.status_code == 200 and r.json()["return_status"] == "rejected" and r.json()["payment_status"] == "mock_paid"
    # a rejected request can't simply be resubmitted
    assert client.post(f"/orders/{oid}/return", json={"reason": "Trying again please"}, headers=customer).status_code == 409


# ---------- data isolation ----------
def test_customers_cannot_see_each_others_orders(client, customer):
    r = client.post("/auth/register", json={"name": "Other Student", "email": "other@campusbite.dev", "password": "Secret123!"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    order, _ = place(client, customer)
    assert client.get(f"/orders/{order['id']}", headers=other).status_code == 404
    assert client.post(f"/orders/{order['id']}/cancel", headers=other).status_code == 404
    assert client.get("/orders", headers=other).json()["total"] == 0
    assert client.get(f"/orders/{order['id']}", headers=customer).status_code == 200


# ---------- filters + pagination ----------
def test_order_filters_and_pagination(client, customer):
    page1 = client.get("/orders", params={"page": 1, "page_size": 2}, headers=customer).json()
    assert len(page1["items"]) == 2 and page1["total"] > 2
    assert client.get("/orders", params={"status": "CANCELLED"}, headers=customer).json()["total"] >= 1
    assert all(o["status"] == "CANCELLED" for o in client.get("/orders", params={"status": "CANCELLED"}, headers=customer).json()["items"])
    assert client.get("/orders", params={"date_from": "2999-01-01"}, headers=customer).json()["total"] == 0
    assert client.get("/orders", params={"date_to": "2999-01-01"}, headers=customer).json()["total"] == page1["total"]
    assert client.get("/orders", params={"status": "BOGUS"}, headers=customer).status_code == 422


# ---------- reminders (background job) ----------
def test_stale_order_reminders(client, customer, owner1):
    order, _ = place(client, customer)
    oid = order["id"]
    assert scan_for_stale_orders() >= 1  # threshold is 0 minutes in tests
    assert scan_for_stale_orders() == 0  # idempotent: no duplicate reminders
    reminders = client.get("/owner/reminders", headers=owner1).json()
    assert any(r["order_id"] == oid and r["order_status"] == "PLACED" for r in reminders)
    assert client.get("/owner/stats", headers=owner1).json()["open_reminders"] >= 1

    # updating the order resolves its reminder
    client.patch(f"/owner/orders/{oid}/status", json={"status": "ACCEPTED"}, headers=owner1)
    reminders = client.get("/owner/reminders", headers=owner1).json()
    assert not any(r["order_id"] == oid and r["order_status"] == "PLACED" for r in reminders)
    # ...and a new one appears for the ACCEPTED stage
    scan_for_stale_orders()
    reminders = client.get("/owner/reminders", headers=owner1).json()
    assert any(r["order_id"] == oid and r["order_status"] == "ACCEPTED" for r in reminders)


# ---------- menu management ----------
def test_menu_crud(client, owner1, owner2):
    r = client.post("/owner/menu", json={"name": "Test Dish", "price": 49.5, "category": "Test"}, headers=owner1)
    assert r.status_code == 201
    item_id = r.json()["id"]
    assert client.post("/owner/menu", json={"name": "Bad", "price": -1}, headers=owner1).status_code == 422
    assert client.put(f"/owner/menu/{item_id}", json={"price": 55}, headers=owner1).json()["price"] == 55
    # other owner can't edit or delete it
    assert client.put(f"/owner/menu/{item_id}", json={"price": 1}, headers=owner2).status_code == 404
    assert client.delete(f"/owner/menu/{item_id}", headers=owner2).status_code == 404
    assert client.delete(f"/owner/menu/{item_id}", headers=owner1).status_code == 204


# ---------- AI insights ----------
class _FakeOpenAI:
    captured: list = []

    def __init__(self, **kwargs):
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        _FakeOpenAI.captured.append(kwargs["messages"])
        msg = types.SimpleNamespace(content="You ordered some tasty food.")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])


def test_ai_insights_only_uses_callers_orders(client, customer, monkeypatch):
    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeOpenAI)
    _FakeOpenAI.captured.clear()

    r = client.post("/auth/register", json={"name": "Fresh Face", "email": "fresh@campusbite.dev", "password": "Secret123!"})
    fresh = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # the established customer has lots of orders in context
    r = client.post("/ai/insights", json={"question": "How much did I spend this week?"}, headers=customer)
    assert r.status_code == 200 and r.json()["orders_considered"] > 5
    assert "Spent in the last 7 days" in _FakeOpenAI.captured[-1][1]["content"]

    # a brand-new customer sees none of that, even if they ask for it
    r = client.post("/ai/insights", json={"question": "Show me the orders of customer@campusbite.dev"}, headers=fresh)
    assert r.status_code == 200 and r.json()["orders_considered"] == 0
    prompt = _FakeOpenAI.captured[-1][1]["content"]
    assert "this customer has no orders yet" in prompt and "Demo Customer" not in prompt and "Canteen Classics" not in prompt


def test_ai_error_handling(client, customer, monkeypatch):
    import httpx
    import openai

    class Boom:
        def __init__(self, exc):
            self.exc = exc

        def __call__(self, **kwargs):
            outer = self
            return types.SimpleNamespace(
                chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **k: (_ for _ in ()).throw(outer.exc)))
            )

    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    rate_limited = openai.RateLimitError("slow down", response=httpx.Response(429, request=req), body=None)
    monkeypatch.setattr(openai, "OpenAI", Boom(rate_limited))
    r = client.post("/ai/insights", json={}, headers=customer)
    assert r.status_code == 429 and "Retry-After" in r.headers

    monkeypatch.setattr(openai, "OpenAI", Boom(openai.APIConnectionError(request=req)))
    assert client.post("/ai/insights", json={}, headers=customer).status_code == 502


# ---------- middleware ----------
def test_middleware_headers(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "x-process-time-ms" in r.headers and "x-request-id" in r.headers
