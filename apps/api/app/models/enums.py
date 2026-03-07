from enum import Enum
from typing import TypeVar

import sqlalchemy as sa

EnumT = TypeVar('EnumT', bound=Enum)


class VPNKeyStatus(str, Enum):
    ACTIVE = 'active'
    EXPIRED = 'expired'
    REVOKED = 'revoked'
    PENDING_PAYMENT = 'pending_payment'


class SubscriptionStatus(str, Enum):
    ACTIVE = 'active'
    EXPIRED = 'expired'
    REVOKED = 'revoked'
    PENDING_PAYMENT = 'pending_payment'


class PaymentStatus(str, Enum):
    PENDING = 'pending'
    WAITING_FOR_CAPTURE = 'waiting_for_capture'
    SUCCEEDED = 'succeeded'
    CANCELED = 'canceled'
    FAILED = 'failed'


class PaymentProvider(str, Enum):
    YOOKASSA = 'yookassa'


class PaymentOperation(str, Enum):
    PURCHASE = 'purchase'
    RENEW = 'renew'


class ReferralStatus(str, Enum):
    PENDING = 'pending'
    QUALIFIED = 'qualified'
    REWARDED = 'rewarded'
    REJECTED = 'rejected'


def db_enum(enum_cls: type[EnumT], *, name: str) -> sa.Enum:
    return sa.Enum(
        enum_cls,
        name=name,
        values_callable=lambda members: [item.value for item in members],
        native_enum=True,
        validate_strings=True,
    )

