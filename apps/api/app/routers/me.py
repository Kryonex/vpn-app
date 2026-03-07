from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.enums import VPNKeyStatus
from app.models.referral import Referral
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.schemas.user import MeResponse

router = APIRouter(tags=['me'])


@router.get('/me', response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> MeResponse:
    invited_count_stmt = select(func.count(Referral.id)).where(Referral.referrer_user_id == current_user.id)
    invited_count = int((await session.scalar(invited_count_stmt)) or 0)

    active_keys_stmt = select(func.count(VPNKey.id)).where(
        VPNKey.owner_id == current_user.id,
        VPNKey.status == VPNKeyStatus.ACTIVE,
    )
    active_keys_count = int((await session.scalar(active_keys_stmt)) or 0)

    nearest_expiry_stmt = (
        select(func.min(Subscription.expires_at))
        .join(VPNKey, VPNKey.id == Subscription.vpn_key_id)
        .where(
            VPNKey.owner_id == current_user.id,
            Subscription.expires_at > datetime.now(timezone.utc),
        )
    )
    nearest_expiry = await session.scalar(nearest_expiry_stmt)

    return MeResponse(
        id=current_user.id,
        referral_code=current_user.referral_code,
        bonus_days_balance=current_user.bonus_days_balance,
        invited_count=invited_count,
        active_keys_count=active_keys_count,
        nearest_expiry=nearest_expiry,
        telegram=current_user.telegram_account,
    )
