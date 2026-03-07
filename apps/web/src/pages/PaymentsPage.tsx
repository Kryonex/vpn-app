import { useEffect, useState } from 'react';

import { apiRequest } from '../api/client';
import type { Payment } from '../types/models';

export function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Payment[]>('/payments')
      .then(setPayments)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load payments'));
  }, []);

  return (
    <section className="stack">
      <h1>Payments History</h1>
      {error && <p className="error">{error}</p>}
      {payments.map((payment) => (
        <article key={payment.id} className="card">
          <p className="value small">{payment.amount} {payment.currency}</p>
          <p className="label">Status: {payment.status}</p>
          <p className="label">Operation: {payment.operation}</p>
          <p className="label">Date: {new Date(payment.created_at).toLocaleString()}</p>
        </article>
      ))}
    </section>
  );
}
