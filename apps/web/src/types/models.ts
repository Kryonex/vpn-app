export type Plan = {
  id: string;
  name: string;
  duration_days: number;
  price: string;
  currency: string;
  is_active: boolean;
  sort_order: number;
  inbound_ids: number[];
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

export type SystemStatus = {
  status: 'online' | 'degraded' | 'maintenance' | 'panel_unavailable' | 'server_unavailable';
  message: string | null;
  maintenance_mode: boolean;
  show_to_all: boolean;
  scheduled_for: string | null;
  updated_at: string | null;
};

export type PaymentSettings = {
  enabled: boolean;
  mode: 'direct' | 'admin_contact' | string;
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

export type SupportContact = {
  telegram_admin_id: number | null;
  username: string | null;
  display_tag: string;
  telegram_link: string | null;
};

export type TelegramProxyItem = {
  id: string;
  country: string;
  proxy_url: string | null;
  button_text: string;
  enabled: boolean;
};

export type TelegramProxyAccess = {
  enabled: boolean;
  proxy_url: string | null;
  button_text: string;
  proxies: TelegramProxyItem[];
};

export type FreeTrialStatus = {
  enabled: boolean;
  eligible: boolean;
  days: number;
  inbound_ids: number[];
  reason: string | null;
};

export type FreeTrialActivateResponse = {
  ok: boolean;
  message: string;
  key_id: string;
  display_name: string;
  expires_at: string;
  connection_uri: string | null;
};

export type NewsItem = {
  id: string;
  title: string;
  body: string;
  image_data_url: string | null;
  created_at: string;
};

export type SystemNewsList = {
  items: NewsItem[];
};
