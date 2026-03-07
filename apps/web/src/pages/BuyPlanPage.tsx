import { useEffect, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import type { PaymentIntent, Plan } from '../types/models';

export function BuyPlanPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Plan[]>('/plans').then(setPlans).catch((err) => {
      setMessage(err instanceof Error ? err.message : 'Failed to load plans');
    });
  }, []);

  const buy = async (planId: string) => {
    const payment = await apiRequest<PaymentIntent>('/keys/purchase', toJsonBody({ plan_id: planId, apply_bonus_days: 0 }));
    if (payment.confirmation_url) {
      const tg = window.Telegram?.WebApp;
      if (tg?.openLink) {
        tg.openLink(payment.confirmation_url);
      } else {
        window.open(payment.confirmation_url, '_blank');
      }
    }
    setMessage('Payment session created');
  };

  return (
    <section className="stack">
      <h1>Buy Plan</h1>
      {plans.map((plan) => (
        <article key={plan.id} className="card">
          <p className="value small">{plan.name}</p>
          <p className="label">{plan.duration_days} days</p>
          <p className="label">{plan.price} {plan.currency}</p>
          <button className="btn" onClick={() => buy(plan.id)}>Pay</button>
        </article>
      ))}
      {message && <p className="ok">{message}</p>}
    </section>
  );
}
