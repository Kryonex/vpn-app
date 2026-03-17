import { CircleHelp, KeyRound, ShieldCheck, Wallet } from 'lucide-react';

import { PageHeader } from '../components/PageHeader';

const faq = [
  {
    icon: Wallet,
    question: 'Как купить доступ?',
    answer: 'Откройте раздел покупки, выберите тариф, оплатите и ключ появится в разделе «Мои ключи».',
  },
  {
    icon: ShieldCheck,
    question: 'Как работает продление?',
    answer: 'Продление увеличивает срок существующего ключа и не создает новый ключ.',
  },
  {
    icon: KeyRound,
    question: 'Что значит перевыпуск?',
    answer: 'Перевыпуск отключает старую версию ключа и создает новую для той же подписки.',
  },
  {
    icon: CircleHelp,
    question: 'Как открыть профиль на устройстве?',
    answer: 'Откройте детали профиля, скопируйте служебную ссылку или отсканируйте QR-код в подходящем приложении.',
  },
];

export function HelpPage() {
  return (
    <section className="stack">
      <PageHeader title="Помощь" subtitle="Частые вопросы и быстрые ответы" />
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
