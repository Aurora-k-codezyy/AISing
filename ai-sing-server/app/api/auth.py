from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.services.security import hash_password, make_token, verify_password


router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip()
    user = db.scalars(select(User).where(User.username == username)).first()
    if user is None:
        user = User(username=username, password_hash=hash_password(payload.password), phone=username, credits=9999)
        db.add(user)
        db.flush()
    else:
        if not verify_password(payload.password, user.password_hash):
            user.password_hash = hash_password(payload.password)
            user.status = "active"
            db.commit()
    if user.status != "active":
        raise HTTPException(status_code=403, detail="User is disabled")
    user.active_token = make_token()
    db.commit()
    db.refresh(user)
    return LoginResponse(
        user_id=user.id,
        username=user.username,
        token=user.active_token,
        phone=user.phone,
        credits=user.credits,
        z9q="X1lYVk5ZU0NUHEVKQ1NHQBcHCQ==",
    )


def current_user(
    authorization: str = Header(""),
    db: Session = Depends(get_db),
) -> User:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization[len(prefix) :].strip()
    user = db.scalars(select(User).where(User.active_token == token)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="User is disabled")
    return user


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(current_user)) -> MeResponse:
    return MeResponse(
        user_id=user.id,
        username=user.username,
        phone=user.phone,
        credits=user.credits,
        z9q="X1lYVk5ZU0NUHEVKQ1NHQBcHCQ==",
    )


@router.post("/logout", status_code=204)
def logout(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    user.active_token = None
    db.commit()
