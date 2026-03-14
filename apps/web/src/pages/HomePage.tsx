import { CircleHelp, Copy, Gift, KeyRound, Rocket, ShieldCheck, Sparkles, Wallet, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState } from '../components/StateCards';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type { ReferralMe, SupportContact } from '../types/models';

const onboardingSteps = [
  {
    title: 'Это ваш личный кабинет',
    text: 'Здесь видно состояние подписки, бонусные дни, реферальную ссылку и быстрые действия. Отсюда удобно начать, если вы открыли сервис впервые.',
  },
  {
    title: 'Ключи всегда под рукой',
    text: 'Во вкладке «Ключи» находятся все ваши подключения: активные, истёкшие и архивные. Там же можно открыть детали, продлить подписку или перевыпустить ключ.',
  },
  {
    title: 'Покупка без лишних шагов',
    text: 'Во вкладке «Купить» собраны тарифы, активные заявки и история оплат. После создания заявки мы сразу покажем, куда перевести оплату и что написать в комментарии.',
  },
];

const faq = [
  {
    question: 'Как подключить VPN?',
    answer: 'Откройте свой ключ, скопируйте ссылку подключения или нажмите кнопку быстрого добавления в приложение. Если появится QR-код, его тоже можно использовать.',
  },
  {
    question: 'Как продлить текущий ключ?',
    answer: 'Откройте нужный ключ и нажмите «Продлить». После оплаты срок действия обновится у текущего подключения.',
  },
  {
    question: 'Что делать, если соединение не работает?',
    answer: 'Попробуйте перевыпустить ключ в разделе «Ключи». Если проблема останется, откройте помощь и напишите в поддержку.',
  },
];

export function HomePage() {
  const { me, telegramProfile, systemStatus } = useAuth();
  const [referral, setReferral] = useState<ReferralMe | null>(null);
  const [support, setSupport] = useState<SupportContact | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [onboardingStep, setOnboardingStep] = useState(0);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    apiRequest<ReferralMe>('/referrals/me').then(setReferral).catch(() => null);
    apiRequest<SupportContact>('/support').then(setSupport).catch(() => null);
  }, []);

  useEffect(() => {
    if (!me) return;
    const key = `onboarding_seen_${me.id}`;
    const seen = window.localStorage.getItem(key);
    const shouldShow = !seen && me.active_keys_count === 0;
    setShowOnboarding(shouldShow);
  }, [me]);

  if (!me) {
    return <EmptyState title="Не удалось загрузить кабинет" text="Попробуйте переоткрыть Mini App." />;
  }

  const nearestExpiry = me.nearest_expiry
    ? new Date(me.nearest_expiry).toLocaleString()
    : 'Пока нет активной подписки';
  const displayName =
    telegramProfile?.first_name ||
    me.telegram?.first_name ||
    me.telegram?.username ||
    'Пользователь';
  const username = telegramProfile?.username || me.telegram?.username || null;
  const avatar = telegramProfile?.photo_url || null;
  const onboardingStorageKey = `onboarding_seen_${me.id}`;

  const quickIntent = useMemo(() => {
    if (me.active_keys_count > 0) {
      return {
        title: 'У вас уже есть активный доступ',
        text: 'Откройте ключи, чтобы быстро скопировать ссылку, посмотреть срок действия или продлить подписку.',
        to: '/keys',
        label: 'Открыть ключи',
        icon: KeyRound,
      };
    }

    return {
      title: 'Начните с выбора тарифа',
      text: 'Во вкладке покупки доступны тарифы и создание новой заявки. После оплаты мы активируем ваш первый ключ.',
      to: '/buy',
      label: 'Выбрать тариф',
      icon: Wallet,
    };
  }, [me.active_keys_count]);

  const dismissOnboarding = () => {
    window.localStorage.setItem(onboardingStorageKey, '1');
    setShowOnboarding(false);
  };

  const copyReferral = async () => {
    if (!referral?.referral_link) return;
    await navigator.clipboard.writeText(referral.referral_link);
    setMessage('Реферальная ссылка скопирована.');
  };

  const QuickIcon = quickIntent.icon;

  return (
    <section className="stack">
      <PageHeader
        title="Личный кабинет"
        subtitle="Статус аккаунта, бонусы, приглашения и быстрая помощь"
        action={
          <button className="page-header-chip page-header-button" onClick={() => setHelpOpen(true)} aria-label="Открыть помощь">
            <CircleHelp size={16} />
          </button>
        }
      />
      <SystemStatusBanner status={systemStatus} />
      {localError && <ErrorState text={localError} />}

      <article className="hero-card welcome-enter">
        <div className="profile-row">
          {avatar ? (
            <img className="profile-avatar" src={avatar} alt="Аватар" />
          ) : (
            <div className="profile-avatar profile-avatar-fallback">{displayName.slice(0, 1).toUpperCase()}</div>
          )}
          <div>
            <p className="profile-name">{displayName}</p>
            <p className="profile-username">{username ? `@${username}` : 'Telegram профиль'}</p>
          </div>
        </div>
        <p className="hero-label greeting-chip">Добро пожаловать</p>
        <p className="hero-title welcome-line-1">{quickIntent.title}</p>
        <p className="hero-subtitle welcome-line-2">{quickIntent.text}</p>
        <div className="action-row">
          <Link className="btn btn-primary" to={quickIntent.to}>
            <QuickIcon size={16} /> {quickIntent.label}
          </Link>
          <Link className="btn btn-ghost" to="/buy">
            <Wallet size={16} /> Купить или продлить
          </Link>
        </div>
      </article>

      <div className="stat-grid">
        <article className="glass-card stat-card">
          <span className="stat-icon"><KeyRound size={16} /></span>
          <p className="stat-label">Активные ключи</p>
          <p className="stat-value">{me.active_keys_count}</p>
        </article>
        <article className="glass-card stat-card">
          <span className="stat-icon"><Sparkles size={16} /></span>
          <p className="stat-label">Бонусные дни</p>
          <p className="stat-value">{me.bonus_days_balance}</p>
        </article>
      </div>

      <article className="glass-card quick-summary">
        <div>
          <p className="muted">Ближайшее окончание</p>
          <p className="title-line">{nearestExpiry}</p>
        </div>
        <div>
          <p className="muted">Приглашено друзей</p>
          <p className="title-line">{referral?.invited_count ?? me.invited_count}</p>
        </div>
      </article>

      <article className="glass-card account-section">
        <div className="section-head">
          <div>
            <p className="title-line row-inline"><Gift size={16} /> Реферальная программа</p>
            <p className="muted">Делитесь ссылкой и получайте бонусные дни за приглашённых друзей.</p>
          </div>
          <span className="chip">{referral?.bonus_days_balance ?? me.bonus_days_balance} дн.</span>
        </div>
        <div className="referral-panel">
          <div>
            <p className="muted">Ваш код</p>
            <p className="title-line">{referral?.referral_code ?? me.referral_code}</p>
          </div>
          <div>
            <p className="muted">Ссылка</p>
            <p className="mono-block">{referral?.referral_link || 'Ссылка появится немного позже.'}</p>
          </div>
          <button className="btn btn-ghost" onClick={() => void copyReferral()} disabled={!referral?.referral_link}>
            <Copy size={16} /> Скопировать ссылку
          </button>
        </div>
      </article>

      <article className="glass-card account-section">
        <div className="section-head">
          <div>
            <p className="title-line row-inline"><ShieldCheck size={16} /> Что можно сделать сейчас</p>
            <p className="muted">Мы подсказываем следующий логичный шаг, чтобы было проще сориентироваться.</p>
          </div>
        </div>
        <div className="stack compact-stack">
          <div className="hint-row">
            <Rocket size={16} />
            <span>{me.active_keys_count > 0 ? 'Откройте ключи, если хотите быстро скопировать ссылку подключения или продлить подписку.' : 'Перейдите в раздел покупки, чтобы выбрать тариф и создать первую заявку.'}</span>
          </div>
          <div className="hint-row">
            <Sparkles size={16} />
            <span>{me.bonus_days_balance > 0 ? `У вас уже есть ${me.bonus_days_balance} бонусных дней. Их можно использовать при продлении.` : 'Бонусные дни начисляются за приглашённых друзей и специальные акции.'}</span>
          </div>
        </div>
      </article>

      {systemStatus?.maintenance_mode && (
        <article className="glass-card">
          <p className="title-line">Сервис временно ограничен</p>
          <p className="muted">Во время технических работ покупка и управление ключами могут быть недоступны. Как только работы завершатся, всё снова заработает в обычном режиме.</p>
        </article>
      )}

      {helpOpen && (
        <div className="modal-backdrop" onClick={() => setHelpOpen(false)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="row-between">
              <div>
                <p className="title-line">Помощь</p>
                <p className="muted">Частые вопросы и контакт поддержки</p>
              </div>
              <button className="icon-button" onClick={() => setHelpOpen(false)}><X size={16} /></button>
            </div>

            <article className="support-card">
              <p className="title-line">Поддержка</p>
              <p className="muted">{support?.display_tag ?? 'Контакт скоро появится'}</p>
              {support?.telegram_link ? (
                <a className="btn btn-primary" href={support.telegram_link} target="_blank" rel="noreferrer">Написать в Telegram</a>
              ) : (
                <p className="muted">Если контакт пока не показан, попробуйте открыть окно позже.</p>
              )}
            </article>

            <div className="stack compact-stack">
              {faq.map((item) => (
                <article key={item.question} className="help-faq-item">
                  <p className="title-line">{item.question}</p>
                  <p className="muted">{item.answer}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      )}

      {showOnboarding && (
        <div className="modal-backdrop">
          <div className="modal-card onboarding-card">
            <div className="row-between">
              <span className="chip">Шаг {onboardingStep + 1} из {onboardingSteps.length}</span>
              <button className="btn btn-ghost" onClick={dismissOnboarding}>Пропустить</button>
            </div>
            <p className="title-line">{onboardingSteps[onboardingStep].title}</p>
            <p className="muted">{onboardingSteps[onboardingStep].text}</p>
            <div className="action-row">
              {onboardingStep < onboardingSteps.length - 1 ? (
                <button className="btn btn-primary" onClick={() => setOnboardingStep((prev) => prev + 1)}>Дальше</button>
              ) : (
                <button className="btn btn-primary" onClick={dismissOnboarding}>Понятно</button>
              )}
            </div>
          </div>
        </div>
      )}

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
