from pydantic import BaseModel


class ReferralMeOut(BaseModel):
    referral_code: str
    referral_link: str
    invited_count: int
    bonus_days_balance: int

