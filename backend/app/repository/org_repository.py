"""
Org Repository — CRUD for organizations and invitations.
"""

import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation
from app.models.organization import Organization


class OrgRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Organization | None:
        result = await self.db.execute(select(Organization).where(Organization.domain == domain))
        return result.scalar_one_or_none()

    async def create(self, name: str, domain: str | None = None) -> Organization:
        org = Organization(name=name, domain=domain)
        self.db.add(org)
        await self.db.flush()
        return org

    # --- Invitations ---

    async def get_invite_by_token(self, token: str) -> Invitation | None:
        result = await self.db.execute(select(Invitation).where(Invitation.token == token))
        return result.scalar_one_or_none()

    async def get_pending_invites_for_org(self, org_id: uuid.UUID) -> list[Invitation]:
        result = await self.db.execute(
            select(Invitation).where(
                Invitation.org_id == org_id,
                Invitation.accepted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def create_invite(
        self,
        org_id: uuid.UUID,
        invited_by: uuid.UUID,
        email: str,
        role: str = "member",
        expires_days: int = 7,
    ) -> Invitation:
        invite = Invitation(
            org_id=org_id,
            invited_by=invited_by,
            email=email,
            token=secrets.token_urlsafe(32),
            role=role,
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        return invite

    async def accept_invite(self, invite: Invitation) -> Invitation:
        invite.accepted_at = datetime.utcnow()
        await self.db.commit()
        return invite
