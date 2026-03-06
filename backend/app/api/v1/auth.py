"""
Auth API controller — signup (email+password only), login, profile.
Org auto-created for business email domains on signup.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repository.org_repository import OrgRepository
from app.repository.user_repository import UserRepository
from app.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    UpdateProfileRequest,
    UserProfileResponse,
)
from app.services.auth_service import create_token, hash_password, verify_password
from app.utils.database import get_db
from app.utils.email_utils import domain_to_org_name, get_email_domain, is_business_email
from app.utils.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Auto-create (or join) org for business email domains
    org_id = None
    org_role = None
    if is_business_email(body.email):
        domain = get_email_domain(body.email)
        org_repo = OrgRepository(db)
        org = await org_repo.get_by_domain(domain)
        if not org:
            org = await org_repo.create(name=domain_to_org_name(domain), domain=domain)
            org_role = "owner"
        else:
            org_role = "member"
        org_id = org.id

    user = await repo.create(
        email=body.email,
        hashed_password=await asyncio.to_thread(hash_password, body.password),
        org_id=org_id,
        org_role=org_role,
    )
    token = create_token(str(user.id))
    return LoginResponse(access_token=token, user=UserProfileResponse.model_validate(user))


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)
    if not user or not await asyncio.to_thread(
        verify_password, body.password, user.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(str(user.id))
    return LoginResponse(access_token=token, user=UserProfileResponse.model_validate(user))


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
