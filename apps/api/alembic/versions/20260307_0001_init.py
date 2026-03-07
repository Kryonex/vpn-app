"""initial schema

Revision ID: 20260307_0001
Revises:
Create Date: 2026-03-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260307_0001'
down_revision = None
branch_labels = None
depends_on = None

vpn_key_status = sa.Enum('active', 'expired', 'revoked', 'pending_payment', name='vpnkeystatus')
subscription_status = sa.Enum('active', 'expired', 'revoked', 'pending_payment', name='subscriptionstatus')
payment_status = sa.Enum('pending', 'waiting_for_capture', 'succeeded', 'canceled', 'failed', name='paymentstatus')
payment_provider = sa.Enum('yookassa', name='paymentprovider')
payment_operation = sa.Enum('purchase', 'renew', name='paymentoperation')
referral_status = sa.Enum('pending', 'qualified', 'rewarded', 'rejected', name='referralstatus')


def upgrade() -> None:
    bind = op.get_bind()
    vpn_key_status.create(bind, checkfirst=True)
    subscription_status.create(bind, checkfirst=True)
    payment_status.create(bind, checkfirst=True)
    payment_provider.create(bind, checkfirst=True)
    payment_operation.create(bind, checkfirst=True)
    referral_status.create(bind, checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('referral_code', sa.String(length=32), nullable=False),
        sa.Column('bonus_days_balance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referral_code'),
    )

    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'telegram_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('first_name', sa.String(length=128), nullable=True),
        sa.Column('last_name', sa.String(length=128), nullable=True),
        sa.Column('language_code', sa.String(length=16), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_user_id'),
        sa.UniqueConstraint('user_id'),
    )

    op.create_table(
        'vpn_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', vpn_key_status, nullable=False, server_default='pending_payment'),
        sa.Column('display_name', sa.String(length=128), nullable=False),
        sa.Column('current_subscription_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vpn_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', subscription_status, nullable=False, server_default='active'),
        sa.Column('notified_expiring_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notified_expired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['vpn_key_id'], ['vpn_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_foreign_key(
        'fk_vpn_keys_current_subscription_id',
        'vpn_keys',
        'subscriptions',
        ['current_subscription_id'],
        ['id'],
    )

    op.create_table(
        'vpn_key_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vpn_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('threexui_client_uuid', sa.String(length=64), nullable=False),
        sa.Column('inbound_id', sa.Integer(), nullable=True),
        sa.Column('email_remark', sa.String(length=255), nullable=True),
        sa.Column('connection_uri', sa.Text(), nullable=True),
        sa.Column('raw_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['vpn_key_id'], ['vpn_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vpn_key_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', payment_provider, nullable=False, server_default='yookassa'),
        sa.Column('operation', payment_operation, nullable=False),
        sa.Column('external_payment_id', sa.String(length=128), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('status', payment_status, nullable=False, server_default='pending'),
        sa.Column('confirmation_url', sa.String(length=1024), nullable=True),
        sa.Column('idempotence_key', sa.String(length=64), nullable=False),
        sa.Column('bonus_days_applied', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('succeeded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vpn_key_id'], ['vpn_keys.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_payment_id'),
        sa.UniqueConstraint('idempotence_key'),
    )

    op.create_table(
        'payment_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('provider', payment_provider, nullable=False),
        sa.Column('provider_event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_event_id'),
    )

    op.create_table(
        'referrals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('referrer_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('referred_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', referral_status, nullable=False, server_default='pending'),
        sa.Column('qualified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rewarded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['referrer_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['referred_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referred_user_id', name='uq_referrals_referred_user_id'),
    )

    op.create_table(
        'referral_rewards',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('referral_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('bonus_days', sa.Integer(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['referral_id'], ['referrals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referral_id', name='uq_referral_rewards_referral_id'),
    )

    op.create_table(
        'bonus_day_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('related_referral_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('related_payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('days_delta', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['related_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_referral_id'], ['referrals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_type', sa.String(length=32), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('bonus_day_ledger')
    op.drop_table('referral_rewards')
    op.drop_table('referrals')
    op.drop_table('payment_events')
    op.drop_table('payments')
    op.drop_table('vpn_key_versions')
    op.drop_constraint('fk_vpn_keys_current_subscription_id', 'vpn_keys', type_='foreignkey')
    op.drop_table('subscriptions')
    op.drop_table('vpn_keys')
    op.drop_table('telegram_accounts')
    op.drop_table('plans')
    op.drop_table('users')

    bind = op.get_bind()
    referral_status.drop(bind, checkfirst=True)
    payment_operation.drop(bind, checkfirst=True)
    payment_provider.drop(bind, checkfirst=True)
    payment_status.drop(bind, checkfirst=True)
    subscription_status.drop(bind, checkfirst=True)
    vpn_key_status.drop(bind, checkfirst=True)
