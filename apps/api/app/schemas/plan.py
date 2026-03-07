from decimal import Decimal
from uuid import UUID

from app.schemas.base import BaseSchema


class PlanOut(BaseSchema):
    id: UUID
    name: str
    duration_days: int
    price: Decimal
    currency: str
    is_active: bool
    sort_order: int

