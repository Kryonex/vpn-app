import { QRCodeCanvas } from 'qrcode.react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { apiRequest, toJsonBody } from '../api/client';
import type { VPNKey } from '../types/models';

export function KeyDetailsPage() {
  const { keyId } = useParams<{ keyId: string }>();
  const [keyData, setKeyData] = useState<VPNKey | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!keyId) return;
    apiRequest<VPNKey>(`/keys/${keyId}`).then(setKeyData).catch((err) => {
      setMessage(err instanceof Error ? err.message : 'Failed to load key');
    });
  }, [keyId]);

  const copyUri = async () => {
    const uri = keyData?.active_version?.connection_uri;
    if (!uri) return;
    await navigator.clipboard.writeText(uri);
    setMessage('Key copied');
  };

  const rotate = async () => {
    if (!keyId) return;
    await apiRequest(`/keys/${keyId}/rotate`, toJsonBody({}));
    setMessage('Key rotated');
    const fresh = await apiRequest<VPNKey>(`/keys/${keyId}`);
    setKeyData(fresh);
  };

  if (!keyData) {
    return <section className="stack"><h1>Key Details</h1><p>Loading...</p></section>;
  }

  const uri = keyData.active_version?.connection_uri;

  return (
    <section className="stack">
      <h1>{keyData.display_name}</h1>
      <article className="card">
        <p className="label">Status: {keyData.status}</p>
        <p className="label">
          Expires:{' '}
          {keyData.current_subscription
            ? new Date(keyData.current_subscription.expires_at).toLocaleString()
            : 'n/a'}
        </p>
        <p className="label">Version: {keyData.active_version?.version ?? '-'}</p>
      </article>

      {uri && (
        <article className="card">
          <p className="label">Connection URI</p>
          <p className="mono">{uri}</p>
          <div className="quick-actions">
            <button className="btn" onClick={copyUri}>Copy key</button>
            <button className="btn secondary" onClick={rotate}>Rotate key</button>
            <Link className="btn secondary" to={`/keys/${keyData.id}/renew`}>Renew</Link>
          </div>
          <div className="qr-wrap">
            <QRCodeCanvas value={uri} size={180} />
          </div>
        </article>
      )}

      {message && <p className="ok">{message}</p>}
    </section>
  );
}
