"""Background job: remind restaurant owners about orders nobody has touched for a while."""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .config import settings
from .database import SessionLocal
from .models import AdminReminderLog, Order, OrderStatus, utcnow

logger = logging.getLogger("campusbite.tasks")

WATCHED_STATUSES = (OrderStatus.PLACED, OrderStatus.ACCEPTED)


def scan_for_stale_orders() -> int:
    """Create a reminder for every PLACED/ACCEPTED order not updated within the threshold.

    Idempotent: an order only gets a new reminder if it has no open reminder for its
    current status. Returns the number of reminders created.
    """
    cutoff = utcnow() - timedelta(minutes=settings.reminder_threshold_minutes)
    created = 0
    with SessionLocal() as db:
        stale_orders = db.scalars(
            select(Order)
            .where(Order.status.in_(WATCHED_STATUSES), Order.status_updated_at <= cutoff)
            .options(selectinload(Order.reminders))
        ).all()

        for order in stale_orders:
            already_open = any(not r.resolved and r.order_status == order.status.value for r in order.reminders)
            if already_open:
                continue
            db.add(
                AdminReminderLog(
                    order_id=order.id,
                    restaurant_id=order.restaurant_id,
                    order_status=order.status.value,
                    message=(
                        f"Order #{order.id} has been {order.status.value} for more than "
                        f"{settings.reminder_threshold_minutes} minutes and needs attention."
                    ),
                )
            )
            created += 1
        db.commit()
    if created:
        logger.info("Created %s reminder(s) for stale orders", created)
    return created


async def reminder_loop() -> None:
    logger.info(
        "Reminder job started (threshold=%sm, every %ss)",
        settings.reminder_threshold_minutes,
        settings.reminder_interval_seconds,
    )
    while True:
        try:
            await asyncio.to_thread(scan_for_stale_orders)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep the loop alive no matter what
            logger.exception("Reminder scan failed")
        await asyncio.sleep(settings.reminder_interval_seconds)
