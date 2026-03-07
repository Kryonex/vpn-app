export function HelpPage() {
  return (
    <section className="stack">
      <h1>Help / FAQ</h1>
      <article className="card">
        <p className="value small">How to connect?</p>
        <p className="label">1. Buy plan. 2. Open key details. 3. Copy URI or scan QR in your VPN app.</p>
      </article>
      <article className="card">
        <p className="value small">How does renewal work?</p>
        <p className="label">Renew extends the same key. No new key is created.</p>
      </article>
      <article className="card">
        <p className="value small">How does rotation work?</p>
        <p className="label">Rotation revokes old key version and creates a new key version for the same VPN key entity.</p>
      </article>
    </section>
  );
}
