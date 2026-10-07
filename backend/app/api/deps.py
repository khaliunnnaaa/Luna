"""Олон endpoint дээр давтан хэрэглэгдэх шалгалтууд."""

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import Role, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Нэвтрээгүй эсвэл токены хугацаа дууссан байна",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_role(*roles: Role) -> Callable[..., User]:
    """Жишээ: `user: User = Depends(require_role(Role.admin))`"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Эрх хүрэхгүй")
        return user

    return checker
