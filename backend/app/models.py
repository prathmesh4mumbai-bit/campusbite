"""SQLAlchemy models: users, restaurants, menu_items, orders, order_items, reviews, payment_ledger, admin_reminder_logs."""

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UtcDateTime(TypeDecorator):
    """Always stores UTC and always returns timezone-aware UTC datetimes (SQLite and PostgreSQL alike)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Role(str, enum.Enum):
    CUSTOMER = "customer"
    RESTAURANT_OWNER = "restaurant_owner"
    DELIVERY_PARTNER = "delivery_partner"


class OrderStatus(str, enum.Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, enum.Enum):
    MOCK_PAID = "mock_paid"
    REFUNDED = "refunded"


class ReturnStatus(str, enum.Enum):
    NONE = "none"
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class LedgerEntryType(str, enum.Enum):
    MOCK_PAYMENT = "mock_payment"
    REFUND = "refund"


def _enum(e):
    return SAEnum(e, native_enum=False, length=30, values_callable=lambda cls: [m.value for m in cls])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role), index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    restaurant: Mapped["Restaurant | None"] = relationship(back_populates="owner", uselist=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="customer", foreign_keys="Order.customer_id")
    deliveries: Mapped[list["Order"]] = relationship(
        back_populates="delivery_partner", foreign_keys="Order.delivery_partner_id"
    )


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    cuisine: Mapped[str | None] = mapped_column(String(80))
    address: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    owner: Mapped[User] = relationship(back_populates="restaurant")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="restaurant")
    reviews: Mapped[list["Review"]] = relationship(back_populates="restaurant")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    category: Mapped[str | None] = mapped_column(String(80))
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    # Soft delete keeps historical order items valid.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    restaurant: Mapped[Restaurant] = relationship(back_populates="menu_items")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    delivery_partner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus), default=OrderStatus.PLACED, index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    delivery_address: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(String(500))
    payment_status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus), default=PaymentStatus.MOCK_PAID)
    return_status: Mapped[ReturnStatus] = mapped_column(_enum(ReturnStatus), default=ReturnStatus.NONE)
    return_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)
    status_updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    customer: Mapped[User] = relationship(back_populates="orders", foreign_keys=[customer_id])
    delivery_partner: Mapped[User | None] = relationship(
        back_populates="deliveries", foreign_keys=[delivery_partner_id]
    )
    restaurant: Mapped[Restaurant] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    review: Mapped["Review | None"] = relationship(back_populates="order", uselist=False)
    payments: Mapped[list["PaymentLedger"]] = relationship(back_populates="order", order_by="PaymentLedger.id")
    reminders: Mapped[list["AdminReminderLog"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    menu_item_id: Mapped[int | None] = mapped_column(ForeignKey("menu_items.id"))
    name: Mapped[str] = mapped_column(String(120))  # snapshot at order time
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # snapshot at order time
    quantity: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("order_id", name="uq_reviews_order"),)  # one review per order

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    order: Mapped[Order] = relationship(back_populates="review")
    customer: Mapped[User] = relationship()
    restaurant: Mapped[Restaurant] = relationship(back_populates="reviews")


class PaymentLedger(Base):
    __tablename__ = "payment_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    entry_type: Mapped[LedgerEntryType] = mapped_column(_enum(LedgerEntryType))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="success")
    reference: Mapped[str | None] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    order: Mapped[Order] = relationship(back_populates="payments")


class AdminReminderLog(Base):
    __tablename__ = "admin_reminder_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    order_status: Mapped[str] = mapped_column(String(20))  # status the order was stuck in
    message: Mapped[str] = mapped_column(String(255))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    order: Mapped[Order] = relationship(back_populates="reminders")
