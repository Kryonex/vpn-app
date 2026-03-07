import { Copy, Gift, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import type { ReferralMe } from '../types/models';

export function ReferralsPage() {
  const [referral, setReferral] = useState<ReferralMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<ReferralMe>('/referrals/me')
      .then(setReferral)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить реферальные данные'))
      .finally(() => setLoading(false));
  }, []);

  const copy = async () => {
    if (!referral?.referral_link) return;
    await navigator.clipboard.writeText(referral.referral_link);
    setMessage('Реферальная ссылка скопирована');
  };

  return (
    <section className="stack">
      <PageHeader title="Рефералы" subtitle="Приглашайте друзей и получайте бонусные дни" />

      {loading && <LoadingState text="Загружаем статистику..." />}
      {error && <ErrorState text={error} />}
      {!loading && !error && !referral && <EmptyState title="Нет данных" text="Попробуйте позже." />}

      {referral && (
        <>
          <div className="stat-grid">
            <article className="glass-card stat-card">
              <span className="stat-icon"><Users size={16} /></span>
              <p className="stat-label">Приглашено</p>
              <p className="stat-value">{referral.invited_count}</p>
            </article>
            <article className="glass-card stat-card">
              <span className="stat-icon"><Gift size={16} /></span>
              <p className="stat-label">Бонусные дни</p>
              <p className="stat-value">{referral.bonus_days_balance}</p>
            </article>
          </div>

          <article className="glass-card">
            <p className="muted">Реферальный код</p>
            <p className="title-line">{referral.referral_code}</p>
            <p className="muted">Реферальная ссылка</p>
            <p className="mono-block">{referral.referral_link || 'Укажите BOT_USERNAME на backend, чтобы сформировать ссылку'}</p>
            <button className="btn btn-primary" onClick={copy} disabled={!referral.referral_link}>
              <Copy size={16} /> Скопировать ссылку
            </button>
          </article>
        </>
      )}

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
