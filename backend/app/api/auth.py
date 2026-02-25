"""
Auth API routes: signup, login, me, profile update.
Onboarding questions are collected at signup time.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ─────────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    # Profile / onboarding fields (collected at signup)
    name: str
    role: str
    company_name: str | None = None
    company_stage: str | None = None
    industry: str | None = None
    team_size: str | None = None
    current_challenges: str | None = None
    goals: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    company_name: str | None = None
    company_stage: str | None = None
    industry: str | None = None
    team_size: str | None = None
    current_challenges: str | None = None
    goals: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str | None
    company_name: str | None
    company_stage: str | None
    industry: str | None
    team_size: str | None
    current_challenges: str | None
    goals: str | None
    onboarding_complete: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# ── Routes ──────────────────────────────────────────────────────────────────


@router.post(
    "/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        role=body.role,
        company_name=body.company_name,
        company_stage=body.company_stage,
        industry=body.industry,
        team_size=body.team_size,
        current_challenges=body.current_challenges,
        goals=body.goals,
        onboarding_complete=True,  # All questions answered at signup
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last active
    user.last_active_at = datetime.utcnow()
    await db.commit()

    token = create_access_token(str(user.id))
    return AuthResponse(token=token, user=_user_response(user))


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return _user_response(current_user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return _user_response(current_user)


@router.post("/logout")
async def logout():
    # JWT is stateless — client drops the token
    return {"message": "Logged out successfully"}


# ── Helper ──────────────────────────────────────────────────────────────────


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        company_name=user.company_name,
        company_stage=user.company_stage,
        industry=user.industry,
        team_size=user.team_size,
        current_challenges=user.current_challenges,
        goals=user.goals,
        onboarding_complete=user.onboarding_complete,
        created_at=user.created_at,
    )
