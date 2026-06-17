from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.models import User
from backend.db.session import get_db
from backend.schemas import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from backend.security.dependencies import get_current_user
from backend.services.auth_service import login_user, register_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(request, db)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    return login_user(request, db)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)):
    return UserPublic(id=current_user.id, username=current_user.username)
