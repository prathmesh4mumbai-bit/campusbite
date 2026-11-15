"""Shared business logic: order state machine, pagination, query helpers."""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from .models import (
    AdminReminderLog,
    LedgerEntryType,
    Order,
    OrderStatus,
    PaymentLedger,
    PaymentStatus,
    Role,
    utcnow,
)

# ---------------------------------------------------------------------------
# Order lifecycle: current status -> {next status: role allowed to perform it}
# Anything not in this table is rejected with 400, whoever asks.
# ---------------------------------------------------------------------------
S = OrderStatus
TRANSITIONS: dict[OrderStatus, dict[OrderStatus, Role]] = {
    S.PLACED: {S.ACCEPTED: Role.RESTAURANT_OWNER, S.CANCELLED: Role.CUSTOMER},
    S.ACCEPTED: {S.PREPARING: Role.RESTAURANT_OWNER},
    S.PREPARING: {S.READY: Role.RESTAURANT_OWNER},
    S.READY: {S.ASSIGNED: Role.RESTAURANT_OWNER},
    S.ASSIGNED: {S.OUT_FOR_DELIVERY: Role.DELIVERY_PARTNER},
    S.OUT_FOR_DELIVERY: {S.DELIVERED: Role.DELIVERY_PARTNER},
    S.DELIVERED: {S.REFUNDED: Role.RESTAURANT_OWNER},  # only reachable via an approved return
}


def apply_transition(db: Session, order: Order, new_status: OrderStatus, actor_role: Role) -> None:
    allowed = TRANSITIONS.get(order.status, {})
    if new_status not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid status transition: {order.status.value} -> {new_status.value}",
        )
    if allowed[new_status] != actor_role:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"A {actor_role.value.replace('_', ' ')} cannot move an order from {order.status.value} to {new_status.value}",
        )
    now = utcnow()
    order.status = new_status
    order.status_updated_at = now
    order.updated_at = now
    # Any open "this order is stale" reminder is no longer relevant once the order moves.
    db.execute(
        update(AdminReminderLog)
        .where(AdminReminderLog.order_id == order.id, AdminReminderLog.resolved.is_(False))
        .values(resolved=True)
    )


def record_mock_payment(db: Session, order: Order) -> None:
    """Dummy payment: always succeeds. No real gateway is involved."""
    order.payment_status = PaymentStatus.MOCK_PAID
    db.add(
        PaymentLedger(
            order=order,
            entry_type=LedgerEntryType.MOCK_PAYMENT,
            amount=order.total_amount,
            status="success",
            reference=f"MOCK-{uuid.uuid4().hex[:12].upper()}",
            note="Dummy payment - no real money moved",
        )
    )


def record_refund(db: Session, order: Order) -> None:
    order.payment_status = PaymentStatus.REFUNDED
    db.add(
        PaymentLedger(
            order=order,
            entry_type=LedgerEntryType.REFUND,
            amount=order.total_amount,
            status="success",
            reference=f"REFUND-{uuid.uuid4().hex[:12].upper()}",
            note="Return approved by restaurant",
        )
    )


# ---------------------------------------------------------------------------
# Pagination + listing helpers
# ---------------------------------------------------------------------------
class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=50),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


ORDER_LOAD_OPTIONS = (
    joinedload(Order.restaurant),
    joinedload(Order.customer),
    joinedload(Order.delivery_partner),
    joinedload(Order.review),
    selectinload(Order.items),
    selectinload(Order.payments),
)


def date_conditions(column, date_from: date | None, date_to: date | None) -> list:
    conditions = []
    if date_from:
        conditions.append(column >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        conditions.append(column < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc))
    return conditions


def paginate_orders(db: Session, conditions: list, params: PageParams) -> dict:
    total = db.scalar(select(func.count(Order.id)).where(*conditions)) or 0
    stmt = (
        select(Order)
        .where(*conditions)
        .options(*ORDER_LOAD_OPTIONS)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    items = db.scalars(stmt).unique().all()
    return {"items": items, "total": total, "page": params.page, "page_size": params.page_size}


def load_order(db: Session, *conditions) -> Order | None:
    return db.scalars(select(Order).where(*conditions).options(*ORDER_LOAD_OPTIONS)).unique().first()


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def paginate_query(db: Session, stmt, params: "PageParams") -> dict:
    """Paginate any SELECT (non-order lists: restaurants, menu items, reviews...)."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.offset(params.offset).limit(params.page_size)).unique().all()
    return {"items": items, "total": total, "page": params.page, "page_size": params.page_size}
