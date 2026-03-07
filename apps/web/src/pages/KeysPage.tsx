import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { apiRequest } from '../api/client';
import type { VPNKey } from '../types/models';

export function KeysPage() {
  const [keys, setKeys] = useState<VPNKey[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<VPNKey[]>('/keys')
      .then(setKeys)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load keys'));
  }, []);

  return (
    <section className="stack">
      <h1>My Keys</h1>
      {error && <p className="error">{error}</p>}
      {keys.map((key) => (
        <article key={key.id} className="card">
          <p className="value small">{key.display_name}</p>
          <p className="label">Status: {key.status}</p>
          <p className="label">
            Expires:{' '}
            {key.current_subscription
              ? new Date(key.current_subscription.expires_at).toLocaleDateString()
              : 'n/a'}
          </p>
          <div className="quick-actions">
            <Link className="btn" to={`/keys/${key.id}`}>Details</Link>
            <Link className="btn secondary" to={`/keys/${key.id}/renew`}>Renew</Link>
          </div>
        </article>
      ))}
    </section>
  );
}
