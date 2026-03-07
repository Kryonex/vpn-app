import { useEffect, useState } from 'react';

import { apiRequest } from '../api/client';
import type { ReferralMe } from '../types/models';

export function ReferralsPage() {
  const [referral, setReferral] = useState<ReferralMe | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<ReferralMe>('/referrals/me').then(setReferral).catch((err) => {
      setMessage(err instanceof Error ? err.message : 'Failed to load referrals');
    });
  }, []);

  const copy = async () => {
    if (!referral?.referral_link) return;
    await navigator.clipboard.writeText(referral.referral_link);
    setMessage('Referral link copied');
  };

  return (
    <section className="stack">
      <h1>Referrals</h1>
      {referral && (
        <article className="card">
          <p className="label">Code: {referral.referral_code}</p>
          <p className="label">Invited users: {referral.invited_count}</p>
          <p className="label">Bonus days: {referral.bonus_days_balance}</p>
          <p className="mono">{referral.referral_link || 'Set BOT_USERNAME in backend env'}</p>
          <button className="btn" onClick={copy}>Copy referral link</button>
        </article>
      )}
      {message && <p className="ok">{message}</p>}
    </section>
  );
}
