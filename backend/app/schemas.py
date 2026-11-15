"""Pydantic request/response models. Money is exposed as plain JSON numbers."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import LedgerEntryType, OrderStatus, PaymentStatus, ReturnStatus, Role


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Role = Role.CUSTOMER
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    restaurant_name: str | None = Field(default=None, max_length=120)  # required for owners
    restaurant_cuisine: str | None = Field(default=None, max_length=80)

    @field_validator("name", "restaurant_name", "phone", "address", "restaurant_cuisine", mode="before")
    @classmethod
    def _strip(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def _owner_needs_restaurant(self):
        if self.role == Role.RESTAURANT_OWNER and not self.restaurant_name:
            raise ValueError("restaurant_name is required for restaurant owners")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: Role
    phone: str | None = None
    address: str | None = None


class UserBrief(ORM):
    id: int
    name: str
    phone: str | None = None


class UserName(ORM):
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- restaurants & menu ----------
class RestaurantOut(ORM):
    id: int
    name: str
    description: str | None = None
    cuisine: str | None = None
    address: str | None = None
    image_url: str | None = None
    is_active: bool = True
    avg_rating: float | None = None
    review_count: int = 0


class RestaurantBrief(ORM):
    id: int
    name: str


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    cuisine: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    price: float = Field(gt=0, le=100000)
    category: str | None = Field(default=None, max_length=80)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    price: float | None = Field(default=None, gt=0, le=100000)
    category: str | None = Field(default=None, max_length=80)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool | None = None


class AvailabilityUpdate(BaseModel):
    is_available: bool


class MenuItemOut(ORM):
    id: int
    restaurant_id: int
    name: str
    description: str | None = None
    price: float
    category: str | None = None
    image_url: str | None = None
    is_available: bool


# ---------- orders ----------
class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1, max_length=50)
    delivery_address: str = Field(min_length=5, max_length=255)
    notes: str | None = Field(default=None, max_length=500)


class OrderItemOut(ORM):
    id: int
    menu_item_id: int | None = None
    name: str
    unit_price: float
    quantity: int


class ReviewOut(ORM):
    id: int
    rating: int
    comment: str | None = None
    created_at: datetime


class PublicReviewOut(ReviewOut):
    customer: UserName | None = None


class PaymentOut(ORM):
    id: int
    entry_type: LedgerEntryType
    amount: float
    status: str
    reference: str | None = None
    note: str | None = None
    created_at: datetime


class OrderOut(ORM):
    id: int
    status: OrderStatus
    total_amount: float
    delivery_address: str
    notes: str | None = None
    payment_status: PaymentStatus
    return_status: ReturnStatus
    return_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    status_updated_at: datetime
    restaurant: RestaurantBrief
    customer: UserBrief
    delivery_partner: UserBrief | None = None
    items: list[OrderItemOut]
    review: ReviewOut | None = None
    payments: list[PaymentOut] = []


class StatusUpdate(BaseModel):
    status: OrderStatus


class AssignRequest(BaseModel):
    delivery_partner_id: int


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReturnRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Please give a reason of at least 5 characters")
        return v


# ---------- owner extras ----------
class ReminderOut(ORM):
    id: int
    order_id: int
    order_status: str
    message: str
    resolved: bool
    created_at: datetime


class TopItem(BaseModel):
    name: str
    quantity: int


class StatsOut(BaseModel):
    total_orders: int
    orders_today: int
    delivered_revenue: float
    average_order_value: float
    average_rating: float | None
    review_count: int
    pending_returns: int
    open_reminders: int
    orders_by_status: dict[str, int]
    top_items: list[TopItem]


# ---------- AI ----------
class InsightRequest(BaseModel):
    question: str | None = Field(default=None, max_length=500)


class InsightResponse(BaseModel):
    answer: str
    orders_considered: int
