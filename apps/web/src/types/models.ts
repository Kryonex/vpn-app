export type Plan = {
  id: string;
  name: string;
  duration_days: number;
  price: string;
  currency: string;
  is_active: boolean;
  sort_order: number;
};

export type Subscription = {
  id: string;
  starts_at: string;
  expires_at: string;
  status: string;
  plan: Plan;
};

export type VPNKeyVersion = {
  id: string;
  version: number;
  inbound_id: number | null;
  email_remark: string | null;
  connection_uri: string | null;
  is_active: boolean;
  created_at: string;
};

export type VPNKey = {
  id: string;
  display_name: string;
  status: 'active' | 'expired' | 'revoked' | 'pending_payment';
  created_at: string;
  updated_at: string;
  current_subscription: Subscription | null;
  active_version: VPNKeyVersion | null;
};

export type Payment = {
  id: string;
  user_id: string;
  vpn_key_id: string | null;
  plan_id: string;
  provider: string;
  operation: string;
  amount: string;
  currency: string;
  status: string;
  confirmation_url: string | null;
  external_payment_id: string | null;
  bonus_days_applied: number;
  created_at: string;
  updated_at: string;
};

export type MeResponse = {
  id: string;
  referral_code: string;
  bonus_days_balance: number;
  invited_count: number;
  active_keys_count: number;
  nearest_expiry: string | null;
  telegram: {
    telegram_user_id: number;
    username: string | null;
    first_name: string | null;
    last_name: string | null;
    language_code: string | null;
  } | null;
};

export type ReferralMe = {
  referral_code: string;
  referral_link: string;
  invited_count: number;
  bonus_days_balance: number;
};

export type PaymentIntent = {
  payment_id: string;
  provider: string;
  status: string;
  confirmation_url: string | null;
  transfer_phone: string | null;
  transfer_note: string | null;
};
