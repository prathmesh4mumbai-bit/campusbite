"""Authentication + role-based access control dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from .database import get_db
from .models import Restaurant, Role, User
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        user_id = int(decode_token(creds.credentials)["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_role(*roles: Role):
    """Dependency factory: the role check happens on the server for every protected endpoint."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action")
        return user

    return checker


require_customer = require_role(Role.CUSTOMER)
require_owner = require_role(Role.RESTAURANT_OWNER)
require_delivery = require_role(Role.DELIVERY_PARTNER)


def get_owner_restaurant(db: Session, owner: User) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.owner_id == owner.id).first()
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No restaurant is linked to this owner account")
    return restaurant
