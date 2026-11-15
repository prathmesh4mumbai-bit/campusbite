"""Delivery-partner endpoints. A partner only ever sees and changes orders assigned to them."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_delivery
from ..models import Order, OrderStatus, Role, User
from ..schemas import OrderOut, StatusUpdate
from ..services import PageParams, apply_transition, load_order, paginate_orders

router = APIRouter(prefix="/delivery", tags=["Delivery partner"])

ACTIVE = [OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY]
HISTORY = [OrderStatus.DELIVERED, OrderStatus.REFUNDED]  # REFUNDED = delivered, then returned


@router.get("/orders")
def my_deliveries(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(require_delivery),
):
    if status_filter is not None and status_filter not in ACTIVE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "status must be ASSIGNED or OUT_FOR_DELIVERY")
    wanted = [status_filter] if status_filter else ACTIVE
    page = paginate_orders(db, [Order.delivery_partner_id == user.id, Order.status.in_(wanted)], params)
    page["items"] = [OrderOut.model_validate(o) for o in page["items"]]
    return page


@router.get("/history")
def delivery_history(params: PageParams = Depends(), db: Session = Depends(get_db), user: User = Depends(require_delivery)):
    page = paginate_orders(db, [Order.delivery_partner_id == user.id, Order.status.in_(HISTORY)], params)
    page["items"] = [OrderOut.model_validate(o) for o in page["items"]]
    return page


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_delivery_status(
    order_id: int, payload: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(require_delivery)
):
    order = load_order(db, Order.id == order_id, Order.delivery_partner_id == user.id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    apply_transition(db, order, payload.status, Role.DELIVERY_PARTNER)
    db.commit()
    return load_order(db, Order.id == order_id)
