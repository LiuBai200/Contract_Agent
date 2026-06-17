from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.db.models import User
from backend.schemas import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from backend.security.password import hash_password, verify_password
from backend.security.token import create_access_token


def register_user(request: RegisterRequest, db: Session) -> AuthResponse:
    exists = db.query(User).filter(User.username == request.username).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(username=request.username, password_hash=hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


def login_user(request: LoginRequest, db: Session) -> AuthResponse:
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return _auth_response(user)


def _auth_response(user: User) -> AuthResponse:
    token = create_access_token(user.id, user.username)
    return AuthResponse(access_token=token, user=UserPublic(id=user.id, username=user.username))
