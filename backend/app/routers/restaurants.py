"""Public browsing: restaurants, menus and reviews (no login needed to look around)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MenuItem, Restaurant, Review
from ..schemas import MenuItemOut, PublicReviewOut, RestaurantOut
from ..services import PageParams, paginate_query

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


def _with_ratings(db: Session, restaurants: list[Restaurant]) -> list[RestaurantOut]:
    ids = [r.id for r in restaurants]
    stats = {}
    if ids:
        rows = db.execute(
            select(Review.restaurant_id, func.avg(Review.rating), func.count(Review.id))
            .where(Review.restaurant_id.in_(ids))
            .group_by(Review.restaurant_id)
        ).all()
        stats = {rid: (float(avg), int(cnt)) for rid, avg, cnt in rows}
    out = []
    for r in restaurants:
        data = RestaurantOut.model_validate(r)
        if r.id in stats:
            data.avg_rating, data.review_count = round(stats[r.id][0], 2), stats[r.id][1]
        out.append(data)
    return out


def _active_restaurant(db: Session, restaurant_id: int) -> Restaurant:
    r = db.get(Restaurant, restaurant_id)
    if r is None or not r.is_active:
        raise HTTPException(404, "Restaurant not found")
    return r


@router.get("")
def list_restaurants(
    search: str | None = None, params: PageParams = Depends(), db: Session = Depends(get_db)
):
    stmt = select(Restaurant).where(Restaurant.is_active.is_(True))
    if search and search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(Restaurant.name.ilike(like) | Restaurant.cuisine.ilike(like))
    page = paginate_query(db, stmt.order_by(Restaurant.name), params)
    page["items"] = _with_ratings(db, page["items"])
    return page


@router.get("/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    return _with_ratings(db, [_active_restaurant(db, restaurant_id)])[0]


@router.get("/{restaurant_id}/menu")
def get_menu(
    restaurant_id: int,
    q: str | None = Query(None, description="Search dish names"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
):
    _active_restaurant(db, restaurant_id)
    stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id, MenuItem.is_deleted.is_(False))
    if q and q.strip():
        stmt = stmt.where(MenuItem.name.ilike(f"%{q.strip()}%"))
    if min_price is not None:
        stmt = stmt.where(MenuItem.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(MenuItem.price <= max_price)
    page = paginate_query(db, stmt.order_by(MenuItem.id), params)
    page["items"] = [MenuItemOut.model_validate(i) for i in page["items"]]
    return page


@router.get("/{restaurant_id}/reviews")
def get_reviews(restaurant_id: int, params: PageParams = Depends(), db: Session = Depends(get_db)):
    _active_restaurant(db, restaurant_id)
    stmt = select(Review).where(Review.restaurant_id == restaurant_id).order_by(Review.created_at.desc())
    page = paginate_query(db, stmt, params)
    page["items"] = [PublicReviewOut.model_validate(r) for r in page["items"]]
    return page
