"""Restaurant-owner endpoints. Every query is scoped to the owner's own restaurant."""

from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owner_restaurant, require_owner
from ..models import (
    AdminReminderLog,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Restaurant,
    ReturnStatus,
    Review,
    Role,
    User,
)
from ..schemas import (
    AssignRequest,
    AvailabilityUpdate,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    OrderOut,
    ReminderOut,
    RestaurantOut,
    RestaurantUpdate,
    StatsOut,
    StatusUpdate,
    TopItem,
    UserBrief,
)
from ..services import (
    PageParams,
    apply_transition,
    date_conditions,
    load_order,
    money,
    paginate_orders,
    paginate_query,
    record_refund,
)

router = APIRouter(prefix="/owner", tags=["Restaurant owner"])

# Statuses an owner may set through the generic status endpoint.
# READY -> ASSIGNED goes through /assign (needs a partner); DELIVERED -> REFUNDED through return approval.
OWNER_SETTABLE = {OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY}


def _restaurant_order(db: Session, restaurant: Restaurant, order_id: int) -> Order:
    order = load_order(db, Order.id == order_id, Order.restaurant_id == restaurant.id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


# ---------- restaurant profile ----------
@router.get("/restaurant", response_model=RestaurantOut)
def my_restaurant(db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    return get_owner_restaurant(db, owner)


@router.put("/restaurant", response_model=RestaurantOut)
def update_restaurant(payload: RestaurantUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    restaurant = get_owner_restaurant(db, owner)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and field in ("name", "is_active"):
            continue
        setattr(restaurant, field, value)
    db.commit()
    db.refresh(restaurant)
    return restaurant


# ---------- menu management ----------
def _dish(db: Session, restaurant: Restaurant, dish_id: int) -> MenuItem:
    dish = db.scalar(
        select(MenuItem).where(
            MenuItem.id == dish_id, MenuItem.restaurant_id == restaurant.id, MenuItem.is_deleted.is_(False)
        )
    )
    if dish is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dish not found")
    return dish


@router.get("/menu")
def list_menu(
    q: str | None = None,
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    restaurant = get_owner_restaurant(db, owner)
    stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant.id, MenuItem.is_deleted.is_(False))
    if q and q.strip():
        stmt = stmt.where(MenuItem.name.ilike(f"%{q.strip()}%"))
    page = paginate_query(db, stmt.order_by(MenuItem.id), params)
    page["items"] = [MenuItemOut.model_validate(i) for i in page["items"]]
    return page


@router.post("/menu", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def add_dish(payload: MenuItemCreate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    restaurant = get_owner_restaurant(db, owner)
    data = payload.model_dump()
    data["price"] = money(data["price"])
    dish = MenuItem(restaurant_id=restaurant.id, **data)
    db.add(dish)
    db.commit()
    db.refresh(dish)
    return dish


@router.put("/menu/{dish_id}", response_model=MenuItemOut)
def update_dish(
    dish_id: int, payload: MenuItemUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)
):
    dish = _dish(db, get_owner_restaurant(db, owner), dish_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and field in ("name", "price", "is_available"):
            continue
        setattr(dish, field, money(value) if field == "price" else value)
    db.commit()
    db.refresh(dish)
    return dish


@router.patch("/menu/{dish_id}/availability", response_model=MenuItemOut)
def set_availability(
    dish_id: int, payload: AvailabilityUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)
):
    dish = _dish(db, get_owner_restaurant(db, owner), dish_id)
    dish.is_available = payload.is_available
    db.commit()
    db.refresh(dish)
    return dish


@router.delete("/menu/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(dish_id: int, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    dish = _dish(db, get_owner_restaurant(db, owner), dish_id)
    dish.is_deleted = True  # soft delete: past orders keep their snapshot
    dish.is_available = False
    db.commit()


# ---------- orders ----------
@router.get("/orders")
def list_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    restaurant = get_owner_restaurant(db, owner)
    conditions = [Order.restaurant_id == restaurant.id, *date_conditions(Order.created_at, date_from, date_to)]
    if status_filter:
        conditions.append(Order.status == status_filter)
    page = paginate_orders(db, conditions, params)
    page["items"] = [OrderOut.model_validate(o) for o in page["items"]]
    return page


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int, payload: StatusUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)
):
    restaurant = get_owner_restaurant(db, owner)
    order = _restaurant_order(db, restaurant, order_id)
    if payload.status == OrderStatus.ASSIGNED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Use the assign endpoint to assign a delivery partner")
    if payload.status not in OWNER_SETTABLE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Invalid status transition: {order.status.value} -> {payload.status.value}"
        )
    apply_transition(db, order, payload.status, Role.RESTAURANT_OWNER)
    db.commit()
    return load_order(db, Order.id == order_id)


@router.get("/delivery-partners", response_model=list[UserBrief])
def delivery_partners(db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    return db.scalars(select(User).where(User.role == Role.DELIVERY_PARTNER).order_by(User.name)).all()


@router.post("/orders/{order_id}/assign", response_model=OrderOut)
def assign_partner(
    order_id: int, payload: AssignRequest, db: Session = Depends(get_db), owner: User = Depends(require_owner)
):
    restaurant = get_owner_restaurant(db, owner)
    order = _restaurant_order(db, restaurant, order_id)
    partner = db.get(User, payload.delivery_partner_id)
    if partner is None or partner.role != Role.DELIVERY_PARTNER:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Delivery partner not found")
    if order.status != OrderStatus.READY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A delivery partner can only be assigned to a READY order")
    apply_transition(db, order, OrderStatus.ASSIGNED, Role.RESTAURANT_OWNER)
    order.delivery_partner_id = partner.id
    db.commit()
    return load_order(db, Order.id == order_id)


# ---------- returns / refunds ----------
@router.get("/returns")
def list_returns(
    return_status: ReturnStatus | None = None,
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    restaurant = get_owner_restaurant(db, owner)
    conditions = [Order.restaurant_id == restaurant.id, Order.return_status != ReturnStatus.NONE]
    if return_status and return_status != ReturnStatus.NONE:
        conditions.append(Order.return_status == return_status)
    page = paginate_orders(db, conditions, params)
    page["items"] = [OrderOut.model_validate(o) for o in page["items"]]
    return page


def _decide_return(db: Session, owner: User, order_id: int, approve: bool) -> Order:
    restaurant = get_owner_restaurant(db, owner)
    order = _restaurant_order(db, restaurant, order_id)
    if order.return_status != ReturnStatus.REQUESTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This order has no pending return request")
    if approve:
        order.return_status = ReturnStatus.APPROVED
        apply_transition(db, order, OrderStatus.REFUNDED, Role.RESTAURANT_OWNER)
        record_refund(db, order)  # payment_status -> refunded + refund ledger row
    else:
        order.return_status = ReturnStatus.REJECTED
    db.commit()
    return load_order(db, Order.id == order_id)


@router.post("/orders/{order_id}/return/approve", response_model=OrderOut)
def approve_return(order_id: int, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    return _decide_return(db, owner, order_id, approve=True)


@router.post("/orders/{order_id}/return/reject", response_model=OrderOut)
def reject_return(order_id: int, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    return _decide_return(db, owner, order_id, approve=False)


# ---------- statistics & reminders ----------
@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    rid = get_owner_restaurant(db, owner).id

    by_status = {s.value: c for s, c in db.execute(
        select(Order.status, func.count(Order.id)).where(Order.restaurant_id == rid).group_by(Order.status)
    ).all()}

    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    orders_today = db.scalar(
        select(func.count(Order.id)).where(Order.restaurant_id == rid, Order.created_at >= today_start)
    ) or 0

    delivered_revenue = db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.restaurant_id == rid, Order.status == OrderStatus.DELIVERED
        )
    )
    live = [Order.restaurant_id == rid, Order.status.notin_([OrderStatus.CANCELLED, OrderStatus.REFUNDED])]
    live_count = db.scalar(select(func.count(Order.id)).where(*live)) or 0
    live_total = db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0)).where(*live))

    avg_rating, review_count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(Review.restaurant_id == rid)
    ).one()

    top = db.execute(
        select(OrderItem.name, func.sum(OrderItem.quantity).label("qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.restaurant_id == rid, Order.status.notin_([OrderStatus.CANCELLED, OrderStatus.REFUNDED]))
        .group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.quantity).desc(), OrderItem.name)
        .limit(5)
    ).all()

    return StatsOut(
        total_orders=sum(by_status.values()),
        orders_today=orders_today,
        delivered_revenue=float(delivered_revenue or 0),
        average_order_value=float(Decimal(live_total or 0) / live_count) if live_count else 0.0,
        average_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        review_count=int(review_count or 0),
        pending_returns=db.scalar(
            select(func.count(Order.id)).where(Order.restaurant_id == rid, Order.return_status == ReturnStatus.REQUESTED)
        ) or 0,
        open_reminders=db.scalar(
            select(func.count(AdminReminderLog.id)).where(
                AdminReminderLog.restaurant_id == rid, AdminReminderLog.resolved.is_(False)
            )
        ) or 0,
        orders_by_status=by_status,
        top_items=[TopItem(name=n, quantity=int(q)) for n, q in top],
    )


@router.get("/reminders", response_model=list[ReminderOut])
def reminders(db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    rid = get_owner_restaurant(db, owner).id
    return db.scalars(
        select(AdminReminderLog)
        .where(AdminReminderLog.restaurant_id == rid, AdminReminderLog.resolved.is_(False))
        .order_by(AdminReminderLog.created_at.desc())
        .limit(50)
    ).all()
