from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.repositories.referral_repository import ReferralRepository
from app.schemas.referral import ReferralMeOut

router = APIRouter(prefix='/referrals', tags=['referrals'])


@router.get('/me', response_model=ReferralMeOut)
async def referrals_me(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    repo = ReferralRepository(session)
    invited_count = await repo.count_invited(current_user.id)
    link = (
        f'https://t.me/{settings.bot_username}?start=ref_{current_user.referral_code}'
        if settings.bot_username
        else ''
    )
    return ReferralMeOut(
        referral_code=current_user.referral_code,
        referral_link=link,
        invited_count=invited_count,
        bonus_days_balance=current_user.bonus_days_balance,
    )
