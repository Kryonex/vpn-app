import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { apiRequest, toJsonBody } from '../api/client';
import type { PaymentIntent, Plan } from '../types/models';

export function RenewKeyPage() {
  const { keyId } = useParams<{ keyId: string }>();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [bonusDays, setBonusDays] = useState(0);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Plan[]>('/plans').then(setPlans).catch((err) => {
      setMessage(err instanceof Error ? err.message : 'Failed to load plans');
    });
  }, []);

  const renew = async (planId: string) => {
    if (!keyId) return;
    const payment = await apiRequest<PaymentIntent>(
      `/keys/${keyId}/renew`,
      toJsonBody({ plan_id: planId, apply_bonus_days: bonusDays }),
    );
    if (payment.confirmation_url) {
      const tg = window.Telegram?.WebApp;
      if (tg?.openLink) {
        tg.openLink(payment.confirmation_url);
      } else {
        window.open(payment.confirmation_url, '_blank');
      }
    }
    setMessage('Renewal payment created');
  };

  return (
    <section className="stack">
      <h1>Renew Key</h1>
      <article className="card">
        <label className="label" htmlFor="bonus-days">Bonus days to apply</label>
        <input
          id="bonus-days"
          className="input"
          type="number"
          value={bonusDays}
          min={0}
          onChange={(e) => setBonusDays(Number(e.target.value || 0))}
        />
      </article>
      {plans.map((plan) => (
        <article key={plan.id} className="card">
          <p className="value small">{plan.name}</p>
          <p className="label">{plan.price} {plan.currency}</p>
          <button className="btn" onClick={() => renew(plan.id)}>Renew</button>
        </article>
      ))}
      {message && <p className="ok">{message}</p>}
    </section>
  );
}
