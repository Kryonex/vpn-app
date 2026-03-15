import {
  ChevronDown, CircleHelp, Copy, Gift, KeyRound, Newspaper, Rocket, ShieldCheck, Sparkles, Wallet, Zap, X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState } from '../components/StateCards';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type {
  FreeTrialActivateResponse,
  FreeTrialStatus,
  ReferralMe,
  SupportContact,
  SystemNewsList,
} from '../types/models';

const onboardingSteps = [
  {
    title: 'Это ваш центр управления ZERO',
    text: 'Здесь видно активный доступ, бонусные дни, приглашения, новости и быстрые действия. Если вы открыли ZERO впервые, начните отсюда.',
  },
  {
    title: 'Доступы находятся внутри кабинета',
    text: 'Откройте доступы, чтобы скопировать ссылку подключения, посмотреть срок действия, продлить или перевыпустить конфигурацию.',
  },
  {
    title: 'Покупка и продление в одном месте',
    text: 'Во вкладке «Купить» собраны тарифы, заявки и история. Если прямые платежи отключены, ZERO сразу переведёт вас к администратору.',
  },
];

const faq = [
  {
    question: 'Как подключить ускоритель?',
    answer: 'Откройте нужный доступ, скопируйте ссылку подключения или нажмите кнопку быстрого добавления в приложение Happ.',
  },
  {
    question: 'Как продлить доступ?',
    answer: 'Перейдите в раздел покупки, создайте заявку на продление и дождитесь подтверждения. Срок действия обновится без лишних шагов.',
  },
  {
    question: 'Что делать, если ускорение не работает?',
    answer: 'Откройте карточку доступа и перевыпустите конфигурацию. Если проблема останется, напишите администратору через окно помощи.',
  },
];

export function HomePage() {
  const { me, telegramProfile, systemStatus, refreshMe } = useAuth();
  const [referral, setReferral] = useState<ReferralMe | null>(null);
  const [support, setSupport] = useState<SupportContact | null>(null);
  const [news, setNews] = useState<SystemNewsList['items']>([]);
  const [trialStatus, setTrialStatus] = useState<FreeTrialStatus | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [activatingTrial, setActivatingTrial] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState(0);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    apiRequest<ReferralMe>('/referrals/me').then(setReferral).catch(() => null);
    apiRequest<SupportContact>('/support').then(setSupport).catch(() => null);
    apiRequest<SystemNewsList>('/system/news').then((data) => setNews(data.items)).catch(() => null);
    apiRequest<FreeTrialStatus>('/system/free-trial').then(setTrialStatus).catch(() => null);
  }, []);

  useEffect(() => {
    if (!me) return;
    const key = `onboarding_seen_${me.id}`;
    const seen = window.localStorage.getItem(key);
    setShowOnboarding(!seen && me.active_keys_count === 0);
  }, [me]);

  useEffect(() => {
    const modalOpen = helpOpen || showOnboarding;
    document.body.classList.toggle('modal-open', modalOpen);
    return () => document.body.classList.remove('modal-open');
  }, [helpOpen, showOnboarding]);

  if (!me) {
    return <EmptyState title="Не удалось загрузить ZERO" text="Попробуйте заново открыть мини-приложение." />;
  }

  const nearestExpiry = me.nearest_expiry
    ? new Date(me.nearest_expiry).toLocaleString()
    : 'Активный доступ пока не найден';
  const displayName = telegramProfile?.first_name || me.telegram?.first_name || me.telegram?.username || 'Пользователь';
  const username = telegramProfile?.username || me.telegram?.username || null;
  const avatar = telegramProfile?.photo_url || null;
  const onboardingStorageKey = `onboarding_seen_${me.id}`;
  const latestNews = news.slice(0, 2);

  const quickIntent = useMemo(() => {
    if (me.active_keys_count > 0) {
      return {
        title: 'Ускорение уже активно',
        text: 'Откройте доступы, чтобы быстро скопировать ссылку подключения, посмотреть срок или обновить конфигурацию.',
        to: '/keys',
        label: 'Открыть доступы',
        icon: KeyRound,
      };
    }

    if (trialStatus?.eligible) {
      return {
        title: 'Для вас доступен пробный период',
        text: 'Активируйте бесплатные дни и сразу получите первый доступ без оплаты.',
        to: '/keys',
        label: 'Открыть доступы',
        icon: KeyRound,
      };
    }

    return {
      title: 'Подключите ZERO за пару шагов',
      text: 'Выберите тариф, создайте заявку и продолжайте оформление в удобном для вас режиме.',
      to: '/buy',
      label: 'Выбрать тариф',
      icon: Wallet,
    };
  }, [me.active_keys_count, trialStatus?.eligible]);

  const dismissOnboarding = () => {
    window.localStorage.setItem(onboardingStorageKey, '1');
    setShowOnboarding(false);
  };

  const copyReferral = async () => {
    if (!referral?.referral_link) return;
    await navigator.clipboard.writeText(referral.referral_link);
    setMessage('Ссылка приглашения скопирована.');
  };

  const activateTrial = async () => {
    try {
      setActivatingTrial(true);
      setLocalError(null);
      const response = await apiRequest<FreeTrialActivateResponse>('/system/free-trial/activate', {
        method: 'POST',
      });
      await refreshMe();
      const nextStatus = await apiRequest<FreeTrialStatus>('/system/free-trial');
      setTrialStatus(nextStatus);
      setMessage(response.message);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Не удалось активировать пробный период.');
    } finally {
      setActivatingTrial(false);
    }
  };

  const QuickIcon = quickIntent.icon;
  const trialReasonText =
    trialStatus?.reason === 'already_used'
      ? 'Пробный период уже использовался.'
      : trialStatus?.reason === 'already_has_subscription'
        ? 'Пробный период доступен только до первой платной активации.'
        : null;

  return (
    <section className="stack">
      <PageHeader
        title="ZERO"
        subtitle="Ускоритель интернета с быстрым доступом, новостями и понятным управлением"
        action={
          <button className="page-header-chip page-header-button" onClick={() => setHelpOpen(true)} aria-label="Открыть помощь">
            <CircleHelp size={16} />
          </button>
        }
      />
      <SystemStatusBanner status={systemStatus} />
      {localError && <ErrorState text={localError} />}

      <article className="hero-card zero-hero welcome-enter">
        <div className="zero-brand">ZERO</div>
        <div className="profile-row">
          {avatar ? (
            <img className="profile-avatar" src={avatar} alt="Аватар" />
          ) : (
            <div className="profile-avatar profile-avatar-fallback">{displayName.slice(0, 1).toUpperCase()}</div>
          )}
          <div>
            <p className="profile-name">{displayName}</p>
            <p className="profile-username">{username ? `@${username}` : 'Аккаунт Telegram'}</p>
          </div>
        </div>
        <p className="hero-label greeting-chip">Добро пожаловать</p>
        <p className="hero-title welcome-line-1">{quickIntent.title}</p>
        <p className="hero-subtitle welcome-line-2">{quickIntent.text}</p>
        <div className="action-row">
          {trialStatus?.eligible && (
            <button className="btn btn-primary" onClick={() => void activateTrial()} disabled={activatingTrial}>
              <Rocket size={16} /> {activatingTrial ? 'Активируем...' : `Пробный период на ${trialStatus.days} дн.`}
            </button>
          )}
          <Link className="btn btn-primary" to={quickIntent.to}>
            <QuickIcon size={16} /> {quickIntent.label}
          </Link>
          <Link className="btn btn-ghost" to="/buy">
            <Wallet size={16} /> Купить или продлить
          </Link>
        </div>
        {trialReasonText && <p className="muted">{trialReasonText}</p>}
      </article>

      <div className="stat-grid">
        <article className="glass-card stat-card liquid-panel">
          <span className="stat-icon"><Zap size={16} /></span>
          <p className="stat-label">Активные доступы</p>
          <p className="stat-value">{me.active_keys_count}</p>
        </article>
        <article className="glass-card stat-card liquid-panel">
          <span className="stat-icon"><Sparkles size={16} /></span>
          <p className="stat-label">Бонусные дни</p>
          <p className="stat-value">{me.bonus_days_balance}</p>
        </article>
      </div>

      <article className="glass-card quick-summary liquid-panel">
        <div>
          <p className="muted">Ближайшее окончание</p>
          <p className="title-line">{nearestExpiry}</p>
        </div>
        <div>
          <p className="muted">Приглашено друзей</p>
          <p className="title-line">{referral?.invited_count ?? me.invited_count}</p>
        </div>
      </article>

      <article className="glass-card account-section liquid-panel">
        <div className="section-head">
          <div>
            <p className="title-line row-inline"><Gift size={16} /> Приглашения</p>
            <p className="muted">Делитесь ZERO и получайте дополнительные дни доступа.</p>
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

      <article className="glass-card account-section liquid-panel">
        <div className="section-head">
          <div>
            <p className="title-line row-inline"><ShieldCheck size={16} /> Быстрые шаги</p>
            <p className="muted">ZERO подсказывает, что логичнее сделать дальше.</p>
          </div>
        </div>
        <div className="stack compact-stack">
          <div className="hint-row">
            <Zap size={16} />
            <span>{me.active_keys_count > 0 ? 'Откройте доступы, если хотите быстро скопировать ссылку подключения или продлить доступ.' : 'Перейдите в раздел покупки, чтобы выбрать тариф и создать первую заявку.'}</span>
          </div>
          <div className="hint-row">
            <Newspaper size={16} />
            <span>{latestNews.length ? 'Во вкладке «Новости» уже есть свежие обновления по сервису.' : 'Во вкладке «Новости» будут появляться свежие обновления и анонсы.'}</span>
          </div>
        </div>
      </article>

      <article className="glass-card account-section liquid-panel">
        <div className="section-head">
          <div>
            <p className="title-line row-inline"><Newspaper size={16} /> Последние новости</p>
            <p className="muted">Короткий обзор самого важного. Полная лента находится в отдельной вкладке.</p>
          </div>
          <Link className="btn btn-ghost btn-inline" to="/news">Открыть все</Link>
        </div>
        {latestNews.length ? (
          <div className="stack compact-stack">
            {latestNews.map((item) => (
              <article key={item.id} className="admin-item zero-news-preview">
                <div className="row-between">
                  <p className="title-line">{item.title}</p>
                  <span className="chip">{new Date(item.created_at).toLocaleDateString()}</span>
                </div>
                <p className="muted">{item.body}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">Пока новостей нет. Здесь будут появляться анонсы и полезные обновления.</p>
        )}
      </article>

      {systemStatus?.maintenance_mode && (
        <article className="glass-card liquid-panel">
          <p className="title-line">Сервис временно ограничен</p>
          <p className="muted">Во время технических работ активация и управление доступом могут быть временно недоступны.</p>
        </article>
      )}

      {helpOpen && (
        <div className="modal-backdrop" onClick={() => setHelpOpen(false)}>
          <div className="modal-card liquid-modal" onClick={(event) => event.stopPropagation()}>
            <div className="row-between">
              <div>
                <p className="title-line">Помощь ZERO</p>
                <p className="muted">Частые вопросы и контакт администратора</p>
              </div>
              <button className="icon-button" onClick={() => setHelpOpen(false)}><X size={16} /></button>
            </div>

            <article className="support-card liquid-panel">
              <p className="title-line">Связь с администратором</p>
              <p className="muted">{support?.display_tag ?? 'Контакт скоро появится'}</p>
              {support?.telegram_link ? (
                <a className="btn btn-primary" href={support.telegram_link} target="_blank" rel="noreferrer">Написать в Telegram</a>
              ) : (
                <p className="muted">Если контакт пока не показан, попробуйте открыть окно позже.</p>
              )}
            </article>

            <div className="stack compact-stack">
              {faq.map((item) => (
                <article key={item.question} className="help-faq-item liquid-panel">
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
          <div className="modal-card onboarding-card liquid-modal">
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
