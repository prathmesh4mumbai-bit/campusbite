"""Demo data. Inserted on startup into an EMPTY database when SEED_DEMO_DATA=true (or run: python -m app.seed).

Never enable this for a real deployment: it creates well-known demo accounts.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from .config import settings
from .database import SessionLocal
from .models import (
    LedgerEntryType,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentLedger,
    PaymentStatus,
    Restaurant,
    ReturnStatus,
    Review,
    Role,
    User,
    utcnow,
)
from .security import hash_password

logger = logging.getLogger("campusbite.seed")

# (owner name, email, restaurant name, cuisine, description, address, [(dish, description, price, category)])
RESTAURANTS = [
    (
        "Priya Sharma", "owner1@campusbite.dev", "Canteen Classics", "North Indian",
        "Home-style thalis, curries and snacks - the campus favourite.", "Main Canteen, Block A",
        [
            ("Veg Thali", "Dal, sabzi, rice, 2 rotis, salad and sweet", 120, "Meals"),
            ("Paneer Butter Masala", "Creamy tomato gravy with soft paneer", 140, "Mains"),
            ("Dal Tadka", "Yellow lentils tempered with garlic and cumin", 110, "Mains"),
            ("Jeera Rice", "Basmati rice with roasted cumin", 90, "Mains"),
            ("Butter Naan", "Tandoor-baked, brushed with butter", 35, "Breads"),
            ("Samosa (2 pcs)", "Crispy pastry with spiced potato filling", 30, "Snacks"),
            ("Masala Chai", "Ginger and cardamom tea", 20, "Drinks"),
            ("Gulab Jamun (2 pcs)", "Warm syrupy milk dumplings", 50, "Dessert"),
        ],
    ),
    (
        "Rahul Verma", "owner2@campusbite.dev", "Wrap & Roll", "Rolls & Wraps",
        "Freshly rolled kathi rolls, wraps and noodles.", "Student Centre, Block C",
        [
            ("Chicken Kathi Roll", "Spiced chicken tikka in a flaky paratha", 130, "Rolls"),
            ("Paneer Tikka Wrap", "Grilled paneer, onions and mint chutney", 120, "Rolls"),
            ("Egg Roll", "Double egg with onions and sauce", 80, "Rolls"),
            ("Veg Hakka Noodles", "Wok-tossed noodles with crunchy veggies", 110, "Noodles"),
            ("Masala Fries", "Crisp fries with peri-peri seasoning", 70, "Sides"),
            ("Cold Coffee", "Thick and chilled", 90, "Drinks"),
        ],
    ),
    (
        "Lakshmi Iyer", "owner3@campusbite.dev", "Southern Spice", "South Indian",
        "Dosas, idlis and filter coffee, made fresh all day.", "Hostel Road, Near Gate 2",
        [
            ("Masala Dosa", "Crispy dosa with potato masala", 80, "Tiffin"),
            ("Idli Sambar (3 pcs)", "Soft idlis with sambar and chutneys", 60, "Tiffin"),
            ("Medu Vada (2 pcs)", "Crisp lentil doughnuts", 50, "Tiffin"),
            ("Onion Uttapam", "Thick pancake topped with onions", 90, "Tiffin"),
            ("Filter Coffee", "Strong South Indian decoction coffee", 30, "Drinks"),
            ("Rava Kesari", "Semolina sweet with saffron", 45, "Dessert"),
        ],
    ),
]


def seed_demo_data() -> bool:
    """Returns True if data was inserted, False if the database already had users."""
    with SessionLocal() as db:
        if db.query(User.id).first():
            return False

        pw = hash_password(settings.seed_demo_password)
        customer = User(name="Demo Customer", email="customer@campusbite.dev", password_hash=pw,
                        role=Role.CUSTOMER, phone="9876500001", address="Hostel 3, Room 214")
        db.add(customer)
        db.flush()  # the customer gets id 1

        restaurants: list[Restaurant] = []
        dishes: dict[str, dict[str, MenuItem]] = {}
        for owner_name, email, r_name, cuisine, desc, address, menu in RESTAURANTS:
            owner = User(name=owner_name, email=email, password_hash=pw, role=Role.RESTAURANT_OWNER, phone="9876500100")
            db.add(owner)
            db.flush()
            rest = Restaurant(owner_id=owner.id, name=r_name, cuisine=cuisine, description=desc, address=address)
            db.add(rest)
            db.flush()
            dishes[r_name] = {}
            for name, d_desc, price, category in menu:
                item = MenuItem(restaurant_id=rest.id, name=name, description=d_desc,
                                price=Decimal(price), category=category)
                db.add(item)
                dishes[r_name][name] = item
            restaurants.append(rest)

        driver1 = User(name="Dev Driver", email="driver1@campusbite.dev", password_hash=pw,
                       role=Role.DELIVERY_PARTNER, phone="9876500201")
        driver2 = User(name="Asha Rider", email="driver2@campusbite.dev", password_hash=pw,
                       role=Role.DELIVERY_PARTNER, phone="9876500202")
        db.add_all([driver1, driver2])
        db.flush()

        by_name = {r.name: r for r in restaurants}
        seq = 0

        def order(rest_name, status, lines, hours_ago, driver=None, rating=None, comment=None, ret=None, minutes_in_status=None):
            nonlocal seq
            seq += 1
            rest = by_name[rest_name]
            created = utcnow() - timedelta(hours=hours_ago)
            total = sum(dishes[rest_name][n].price * q for n, q in lines)
            since = created if minutes_in_status is None else utcnow() - timedelta(minutes=minutes_in_status)
            o = Order(
                customer_id=customer.id, restaurant_id=rest.id, delivery_partner_id=driver.id if driver else None,
                status=status, total_amount=total, delivery_address=customer.address,
                payment_status=PaymentStatus.REFUNDED if status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED) else PaymentStatus.MOCK_PAID,
                created_at=created, updated_at=since, status_updated_at=since,
            )
            for n, q in lines:
                d = dishes[rest_name][n]
                o.items.append(OrderItem(menu_item_id=d.id, name=d.name, unit_price=d.price, quantity=q))
            o.payments.append(PaymentLedger(entry_type=LedgerEntryType.MOCK_PAYMENT, amount=total, status="success",
                                            reference=f"MOCK-SEED{seq:06d}", note="Dummy payment - no real money moved",
                                            created_at=created))
            if status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
                o.payments.append(PaymentLedger(entry_type=LedgerEntryType.REFUND, amount=total, status="success",
                                                reference=f"REFUND-SEED{seq:06d}", note="Order cancelled", created_at=since))
            if ret:
                o.return_status, o.return_reason = ret
            db.add(o)
            db.flush()
            if rating:
                db.add(Review(order_id=o.id, customer_id=customer.id, restaurant_id=o.restaurant_id,
                              rating=rating, comment=comment, created_at=since))
            return o

        S = OrderStatus
        # Canteen Classics (every review is 5 stars; the API tests rely on this)
        order("Canteen Classics", S.DELIVERED, [("Veg Thali", 2), ("Masala Chai", 2)], 240, driver1, 5, "Lovely thali, still hot!")
        order("Canteen Classics", S.DELIVERED, [("Paneer Butter Masala", 1), ("Butter Naan", 3)], 72, driver1, 5, "Great paneer.")
        order("Canteen Classics", S.DELIVERED, [("Dal Tadka", 1), ("Jeera Rice", 1), ("Gulab Jamun (2 pcs)", 1)], 20, driver1,
              ret=(ReturnStatus.REQUESTED, "The dal was cold when it arrived."))
        order("Canteen Classics", S.CANCELLED, [("Samosa (2 pcs)", 4)], 50)
        order("Canteen Classics", S.PLACED, [("Veg Thali", 1), ("Butter Naan", 2)], 0.4, minutes_in_status=20)
        # Wrap & Roll
        order("Wrap & Roll", S.DELIVERED, [("Chicken Kathi Roll", 2), ("Cold Coffee", 1)], 120, driver1, 4, "Tasty, a bit late.")
        order("Wrap & Roll", S.OUT_FOR_DELIVERY, [("Veg Hakka Noodles", 1), ("Masala Fries", 1)], 1, driver1, minutes_in_status=10)
        order("Wrap & Roll", S.READY, [("Paneer Tikka Wrap", 2)], 0.5, minutes_in_status=5)
        # Southern Spice
        order("Southern Spice", S.DELIVERED, [("Masala Dosa", 2), ("Filter Coffee", 2)], 144, driver2, 5, "Crispy dosa!")

        db.commit()
        logger.info("Seeded demo data (all demo accounts use the SEED_DEMO_PASSWORD)")
        return True


if __name__ == "__main__":
    from .database import Base, engine

    Base.metadata.create_all(bind=engine)
    print("Demo data inserted." if seed_demo_data() else "Database already has users - nothing seeded.")
