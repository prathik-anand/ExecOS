"""
Invitations API — org members can invite others via email token.

POST /api/v1/invitations           — create invite (org owner/admin only)
GET  /api/v1/invitations           — list pending invites for current user's org
POST /api/v1/invitations/accept    — accept an invite by token
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repository.org_repository import OrgRepository
from app.repository.user_repository import UserRepository
from app.utils.database import get_db
from app.utils.security import get_current_user

router = APIRouter(prefix="/invitations", tags=["invitations"])


class CreateInviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class AcceptInviteRequest(BaseModel):
    token: str


@router.post("")
async def create_invitation(
    body: CreateInviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.org_id:
        raise HTTPException(status_code=400, detail="You are not part of an organization")
    if current_user.org_role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only org owners or admins can invite members")

    org_repo = OrgRepository(db)
    invite = await org_repo.create_invite(
        org_id=current_user.org_id,
        invited_by=current_user.id,
        email=body.email,
        role=body.role,
    )
    return {
        "id": str(invite.id),
        "email": invite.email,
        "token": invite.token,
        "role": invite.role,
        "expires_at": invite.expires_at.isoformat(),
    }


@router.get("")
async def list_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.org_id:
        return {"invitations": []}

    org_repo = OrgRepository(db)
    invites = await org_repo.get_pending_invites_for_org(current_user.org_id)
    return {
        "invitations": [
            {
                "id": str(i.id),
                "email": i.email,
                "role": i.role,
                "expires_at": i.expires_at.isoformat(),
                "created_at": i.created_at.isoformat(),
            }
            for i in invites
        ]
    }


@router.post("/accept")
async def accept_invitation(
    body: AcceptInviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_repo = OrgRepository(db)
    invite = await org_repo.get_invite_by_token(body.token)

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invitation already accepted")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation has expired")
    if invite.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=403, detail="This invitation is for a different email address"
        )

    # Accept invite and assign user to org
    await org_repo.accept_invite(invite)
    user_repo = UserRepository(db)
    await user_repo.update(current_user, org_id=invite.org_id, org_role=invite.role)

    return {"success": True, "org_id": str(invite.org_id), "role": invite.role}
