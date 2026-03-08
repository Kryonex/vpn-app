import { CircleHelp, ExternalLink, KeyRound, LifeBuoy, ShieldCheck, Wallet } from 'lucide-react';
import { useEffect, useState } from 'react';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import type { SupportContact } from '../types/models';

const faq = [
  {
    icon: Wallet,
    question: 'Как оплатить подписку?',
    answer: 'Создайте заявку в разделе покупки и выполните перевод по указанному номеру. После этого отправьте подтверждение администратору.',
  },
  {
    icon: ShieldCheck,
    question: 'Как работает продление?',
    answer: 'Продление увеличивает срок действия текущего ключа, новый ключ при этом не создается.',
  },
  {
    icon: KeyRound,
    question: 'Что делает перевыпуск?',
    answer: 'Старый клиент в панели 3x-ui отключается, после чего создается новый активный ключ и новый URI.',
  },
  {
    icon: CircleHelp,
    question: 'Не удается подключиться',
    answer: 'Напишите в поддержку и приложите ID ключа, а также скрин ошибки подключения из VPN-клиента.',
  },
];

export function SupportPage() {
  const [support, setSupport] = useState<SupportContact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<SupportContact>('/support')
      .then(setSupport)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить контакт поддержки'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="stack">
      <PageHeader title="Поддержка" subtitle="Контакты администратора и быстрые ответы на частые вопросы" />

      {loading && <LoadingState text="Загружаем данные поддержки..." />}
      {error && <ErrorState text={error} />}

      {!loading && !error && support && (
        <article className="glass-card">
          <p className="title-line row-inline"><LifeBuoy size={16} /> Контакт администратора</p>
          <p className="muted">Telegram: {support.display_tag}</p>
          {support.telegram_link ? (
            <a className="btn btn-primary" href={support.telegram_link} target="_blank" rel="noreferrer">
              Написать в Telegram <ExternalLink size={14} />
            </a>
          ) : (
            <EmptyState title="Контакт пока недоступен" text="Администратор не настроен в конфигурации сервера." />
          )}
        </article>
      )}

      {!loading && !error && !support && (
        <EmptyState title="Поддержка недоступна" text="Попробуйте обновить страницу позже." />
      )}

      {faq.map((item) => {
        const Icon = item.icon;
        return (
          <article key={item.question} className="glass-card help-item">
            <p className="title-line row-inline"><Icon size={16} /> {item.question}</p>
            <p className="muted">{item.answer}</p>
          </article>
        );
      })}
    </section>
  );
}
