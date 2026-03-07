import { Link } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

export function HomePage() {
  const { me } = useAuth();

  if (!me) {
    return null;
  }

  return (
    <section className="stack">
      <h1>VPN Dashboard</h1>
      <div className="card-grid">
        <article className="card highlight">
          <p className="label">Active keys</p>
          <p className="value">{me.active_keys_count}</p>
        </article>
        <article className="card">
          <p className="label">Bonus days</p>
          <p className="value">{me.bonus_days_balance}</p>
        </article>
      </div>

      <article className="card">
        <p className="label">Nearest expiry</p>
        <p className="value small">{me.nearest_expiry ? new Date(me.nearest_expiry).toLocaleString() : 'No active keys'}</p>
      </article>

      <div className="quick-actions">
        <Link className="btn" to="/buy">Buy Plan</Link>
        <Link className="btn secondary" to="/keys">Manage Keys</Link>
      </div>
    </section>
  );
}
