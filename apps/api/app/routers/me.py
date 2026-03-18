from __future__ import annotations

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.enums import VPNKeyStatus
from app.models.referral import Referral
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.schemas.auth import WebAccessSetupRequest, WebAccessStatusResponse
from app.schemas.user import MeResponse
from app.services.web_access_service import WebAccessService

router = APIRouter(tags=['me'])
logger = logging.getLogger(__name__)


@router.get('/me', response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> MeResponse:
    logger.info('GET /me reached for authenticated user')
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


@router.get('/me/web-access', response_model=WebAccessStatusResponse)
async def me_web_access(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebAccessStatusResponse:
    service = WebAccessService(session)
    return WebAccessStatusResponse(**(await service.get_status(current_user)))


@router.put('/me/web-access', response_model=WebAccessStatusResponse)
async def update_web_access(
    payload: WebAccessSetupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebAccessStatusResponse:
    service = WebAccessService(session)
    try:
        return WebAccessStatusResponse(
            **(
                await service.set_password(
                    current_user,
                    password=payload.password,
                    regenerate_login_id=payload.regenerate_login_id,
                )
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
