"""
Auth API controller — thin HTTP handler only.
All business logic delegated to services and repository layers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.utils.security import get_current_user
from app.schemas.auth_schemas import (
    SignupRequest,
    LoginRequest,
    LoginResponse,
    UserProfileResponse,
    UpdateProfileRequest,
)
from app.repository.user_repository import UserRepository
from app.services.auth_service import hash_password, verify_password, create_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await repo.create(
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
        onboarding_complete=bool(body.name and body.role),
    )
    token = create_token(str(user.id))
    return LoginResponse(
        access_token=token, user=UserProfileResponse.model_validate(user)
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(str(user.id))
    return LoginResponse(
        access_token=token, user=UserProfileResponse.model_validate(user)
    )


@router.get("/me", response_model=UserProfileResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserProfileResponse.model_validate(current_user)


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    updated = await repo.update(current_user, **body.model_dump(exclude_none=True))
    return UserProfileResponse.model_validate(updated)


@router.post("/logout")
async def logout():
    return {"message": "Logged out"}
