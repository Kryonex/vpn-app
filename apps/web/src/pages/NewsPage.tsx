import { Newspaper } from 'lucide-react';
import { useEffect, useState } from 'react';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, SkeletonCards } from '../components/StateCards';
import type { SystemNewsList } from '../types/models';

export function NewsPage() {
  const [items, setItems] = useState<SystemNewsList['items']>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<SystemNewsList>('/system/news')
      .then((data) => setItems(data.items))
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить новости'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="stack">
      <PageHeader title="Новости ZERO" subtitle="Обновления сервиса, новые режимы и важные объявления" />
      {loading && <SkeletonCards count={3} />}
      {error && <ErrorState text={error} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState title="Пока без новостей" text="Здесь будут появляться анонсы, обновления и важные сообщения от команды ZERO." />
      )}
      {!loading && !error && items.map((item) => (
        <article key={item.id} className="glass-card news-card">
          <div className="row-inline news-headline">
            <span className="stat-icon"><Newspaper size={16} /></span>
            <div>
              <p className="title-line">{item.title}</p>
              <p className="muted">{new Date(item.created_at).toLocaleDateString()}</p>
            </div>
          </div>
          {item.image_data_url && <img className="news-image" src={item.image_data_url} alt={item.title} />}
          <p className="muted">{item.body}</p>
        </article>
      ))}
    </section>
  );
}
