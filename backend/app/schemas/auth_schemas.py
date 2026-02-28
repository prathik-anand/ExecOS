"""Auth Pydantic schemas — request/response contracts for auth endpoints."""

from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None
    role: str | None = None
    company_name: str | None = None
    company_stage: str | None = None
    industry: str | None = None
    team_size: str | None = None
    current_challenges: str | None = None
    goals: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class UserProfileResponse(BaseModel):
    id: uuid.UUID
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

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    company_name: str | None = None
    company_stage: str | None = None
    industry: str | None = None
    team_size: str | None = None
    current_challenges: str | None = None
    goals: str | None = None
    onboarding_complete: bool | None = None
