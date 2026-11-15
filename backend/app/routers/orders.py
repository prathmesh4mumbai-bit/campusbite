"""Customer order endpoints: place, list, view, cancel, review, request a return."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_customer
from ..models import (
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    ReturnStatus,
    Review,
    Role,
    User,
)
from ..schemas import OrderCreate, OrderOut, ReturnRequest, ReviewCreate
from ..services import (
    PageParams,
    apply_transition,
    date_conditions,
    load_order,
    money,
    paginate_orders,
    record_mock_payment,
    record_refund,
)

router = APIRouter(prefix="/orders", tags=["Orders (customer)"])


def get_own_order(db: Session, order_id: int, user: User) -> Order:
    """A customer can only ever load their own orders; anyone else's id looks like it doesn't exist."""
    order = load_order(db, Order.id == order_id, Order.customer_id == user.id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, db: Session = Depends(get_db), user: User = Depends(require_customer)):
    # merge duplicate lines
    quantities: dict[int, int] = {}
    for line in payload.items:
        quantities[line.menu_item_id] = quantities.get(line.menu_item_id, 0) + line.quantity

    dishes = db.scalars(
        select(MenuItem).where(MenuItem.id.in_(quantities.keys()), MenuItem.is_deleted.is_(False))
    ).all()
    found = {d.id: d for d in dishes}
    missing = sorted(set(quantities) - set(found))
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Dish not found: {missing}")
    if len({d.restaurant_id for d in dishes}) != 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An order can only contain dishes from one restaurant")
    unavailable = [d.name for d in dishes if not d.is_available]
    if unavailable:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Currently unavailable: {', '.join(unavailable)}")
    restaurant = dishes[0].restaurant
    if not restaurant.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This restaurant is not accepting orders right now")

    # Prices always come from the database, never from the client.
    total = sum((found[i].price * q for i, q in quantities.items()), Decimal("0"))
    order = Order(
        customer_id=user.id,
        restaurant_id=restaurant.id,
        total_amount=money(total),
        delivery_address=payload.delivery_address.strip(),
        notes=(payload.notes or "").strip() or None,
        status=OrderStatus.PLACED,
    )
    for dish_id, qty in quantities.items():
        d = found[dish_id]
        order.items.append(OrderItem(menu_item_id=d.id, name=d.name, unit_price=d.price, quantity=qty))
    db.add(order)
    db.flush()
    record_mock_payment(db, order)  # dummy payment: payment_status -> mock_paid + ledger row
    db.commit()
    return load_order(db, Order.id == order.id)


@router.get("")
def list_my_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(require_customer),
):
    conditions = [Order.customer_id == user.id, *date_conditions(Order.created_at, date_from, date_to)]
    if status_filter:
        conditions.append(Order.status == status_filter)
    page = paginate_orders(db, conditions, params)
    page["items"] = [OrderOut.model_validate(o) for o in page["items"]]
    return page


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The customer who placed it, the owner of its restaurant, or its assigned delivery partner."""
    order = load_order(db, Order.id == order_id)
    allowed = order is not None and (
        (user.role == Role.CUSTOMER and order.customer_id == user.id)
        or (user.role == Role.RESTAURANT_OWNER and order.restaurant.owner_id == user.id)
        or (user.role == Role.DELIVERY_PARTNER and order.delivery_partner_id == user.id)
    )
    if not allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_customer)):
    order = get_own_order(db, order_id, user)
    if order.status != OrderStatus.PLACED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only orders in PLACED status can be cancelled")
    apply_transition(db, order, OrderStatus.CANCELLED, Role.CUSTOMER)
    record_refund(db, order)  # the dummy payment is returned
    db.commit()
    return load_order(db, Order.id == order_id)


@router.post("/{order_id}/review", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def submit_review(
    order_id: int, payload: ReviewCreate, db: Session = Depends(get_db), user: User = Depends(require_customer)
):
    order = get_own_order(db, order_id, user)
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can only review an order after it has been delivered")
    if order.review is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already reviewed this order")
    db.add(
        Review(
            order_id=order.id,
            customer_id=user.id,
            restaurant_id=order.restaurant_id,
            rating=payload.rating,
            comment=(payload.comment or "").strip() or None,
        )
    )
    db.commit()
    return load_order(db, Order.id == order_id)


@router.post("/{order_id}/return", response_model=OrderOut)
def request_return(
    order_id: int, payload: ReturnRequest, db: Session = Depends(get_db), user: User = Depends(require_customer)
):
    order = get_own_order(db, order_id, user)
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A return/refund can only be requested after delivery")
    if order.return_status != ReturnStatus.NONE:
        raise HTTPException(status.HTTP_409_CONFLICT, "A return has already been requested for this order")
    order.return_status = ReturnStatus.REQUESTED
    order.return_reason = payload.reason
    db.commit()
    return load_order(db, Order.id == order_id)
