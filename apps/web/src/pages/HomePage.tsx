import {
  CircleHelp, Copy, FileText, Gift, KeyRound, Newspaper, Rocket, ShieldCheck, Sparkles, Wallet, Zap, X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState } from '../components/StateCards';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import { openTelegramPage } from '../telegram';
import type {
  BackupAccessSettings,
  FreeTrialActivateResponse,
  FreeTrialStatus,
  ReferralMe,
  SupportContact,
  SystemNewsList,
} from '../types/models';

const onboardingSteps = [
  {
    title: 'Это ваш центр управления ZERO',
    text: 'Здесь видны активный профиль, бонусные дни, приглашения, новости и быстрые действия. Если вы открыли ZERO впервые, начните отсюда.',
  },
  {
    title: 'Профили находятся внутри кабинета',
    text: 'Откройте профили, чтобы скопировать служебную ссылку, посмотреть срок действия, продлить или обновить конфигурацию.',
  },
  {
    title: 'Покупка и продление в одном месте',
    text: 'Во вкладке «Купить» собраны тарифы, заявки и история. Если прямые платежи отключены, ZERO сразу переведёт вас к администратору.',
  },
];

const faq = [
  {
    question: 'Как начать работу с профилем?',
    answer: 'Откройте нужный профиль, скопируйте служебную ссылку или нажмите кнопку быстрого открытия в подходящем приложении.',
  },
  {
    question: 'Как продлить профиль?',
    answer: 'Перейдите в раздел покупки, создайте заявку на продление и дождитесь подтверждения. Срок действия обновится без лишних шагов.',
  },
  {
    question: 'Что делать, если профиль не открывается?',
    answer: 'Откройте карточку профиля и обновите конфигурацию. Если проблема останется, напишите администратору через окно помощи.',
  },
];

export function HomePage() {
  const { me, telegramProfile, systemStatus, refreshMe } = useAuth();
  const [referral, setReferral] = useState<ReferralMe | null>(null);
  const [support, setSupport] = useState<SupportContact | null>(null);
  const [news, setNews] = useState<SystemNewsList['items']>([]);
  const [trialStatus, setTrialStatus] = useState<FreeTrialStatus | null>(null);
  const [backupAccess, setBackupAccess] = useState<BackupAccessSettings | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [metricInfo, setMetricInfo] = useState<'keys' | 'bonus' | null>(null);
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
    apiRequest<BackupAccessSettings>('/system/backup-access').then(setBackupAccess).catch(() => null);
  }, []);

  useEffect(() => {
    if (!me) return;
    const key = `onboarding_seen_${me.id}`;
    const seen = window.localStorage.getItem(key);
    setShowOnboarding(!seen && me.active_keys_count === 0);
  }, [me]);

  useEffect(() => {
    const modalOpen = helpOpen || showOnboarding || Boolean(metricInfo);
    document.body.classList.toggle('modal-open', modalOpen);
    return () => document.body.classList.remove('modal-open');
  }, [helpOpen, showOnboarding, metricInfo]);

  if (!me) {
    return <EmptyState title="Не удалось загрузить ZERO" text="Попробуйте заново открыть мини-приложение." />;
  }

  const nearestExpiry = me.nearest_expiry
    ? new Date(me.nearest_expiry).toLocaleString()
    : 'Активный профиль пока не найден';
  const displayName = telegramProfile?.first_name || me.telegram?.first_name || me.telegram?.username || 'Пользователь';
  const username = telegramProfile?.username || me.telegram?.username || null;
  const avatar = telegramProfile?.photo_url || null;
  const onboardingStorageKey = `onboarding_seen_${me.id}`;
  const latestNews = news.slice(0, 2);
  const infoUrl = `${window.location.origin}/info.html`;

  const quickIntent = useMemo(() => {
    if (me.active_keys_count > 0) {
      return {
        title: 'Профиль уже активен',
        text: 'Откройте профили, чтобы быстро скопировать служебную ссылку, проверить срок и обновить конфигурацию.',
        to: '/keys',
        label: 'Открыть профили',
        icon: KeyRound,
      };
    }

    if (trialStatus?.eligible) {
      return {
        title: 'Для вас доступен пробный период',
        text: 'Активируйте бесплатные дни и сразу получите первый профиль без оплаты.',
        to: '/keys',
        label: 'Открыть профили',
        icon: KeyRound,
      };
    }

    return {
      title: 'Начните работу с ZERO',
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
        title="Личный кабинет"
        subtitle="Управление профилем, бонусами и новостями без лишнего шума"
        action={
          <div className="page-header-actions">
            <button
              className="page-header-chip page-header-button"
              onClick={() => openTelegramPage(infoUrl)}
              aria-label="Открыть информацию"
              title="Информация"
            >
              <FileText size={16} />
            </button>
            <button
              className="page-header-chip page-header-button"
              onClick={() => setHelpOpen(true)}
              aria-label="Открыть помощь"
              title="Помощь"
            >
              <CircleHelp size={16} />
            </button>
          </div>
        }
      />
      <SystemStatusBanner status={systemStatus} />
      {localError && <ErrorState text={localError} />}

      <article className="hero-card zero-hero welcome-enter compact-hero">
        <div className="profile-row compact-profile-row">
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
        <div className="metric-pills">
          <button className="metric-pill" onClick={() => setMetricInfo('keys')}>
            <span className="metric-pill-icon"><Zap size={14} /></span>
            <span className="metric-pill-value">{me.active_keys_count}</span>
            <span className="metric-pill-label">профили</span>
          </button>
          <button className="metric-pill" onClick={() => setMetricInfo('bonus')}>
            <span className="metric-pill-icon"><Sparkles size={14} /></span>
            <span className="metric-pill-value">{me.bonus_days_balance}</span>
            <span className="metric-pill-label">бонусы</span>
          </button>
        </div>
        <p className="hero-label greeting-chip">Добро пожаловать</p>
        <p className="hero-title welcome-line-1">{quickIntent.title}</p>
        <p className="hero-subtitle welcome-line-2">{quickIntent.text}</p>
        <div className="action-row compact-actions">
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

      <article className="glass-card quick-summary liquid-panel compact-summary-card">
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
            <p className="muted">Делитесь ZERO и получайте дополнительные дни действия.</p>
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
            <span>{me.active_keys_count > 0 ? 'Откройте профили, если хотите быстро скопировать служебную ссылку или продлить текущий профиль.' : 'Перейдите в раздел покупки, чтобы выбрать тариф и создать первую заявку.'}</span>
          </div>
          <div className="hint-row">
            <Newspaper size={16} />
            <span>{latestNews.length ? 'Во вкладке «Новости» уже есть свежие обновления по сервису.' : 'Во вкладке «Новости» будут появляться свежие обновления и анонсы.'}</span>
          </div>
        </div>
      </article>

      {systemStatus?.maintenance_mode && (
        <article className="glass-card liquid-panel">
          <p className="title-line">Сервис временно ограничен</p>
          <p className="muted">Во время технических работ активация и управление доступом могут быть временно недоступны.</p>
        </article>
      )}

      {systemStatus?.status === 'server_unavailable' && backupAccess?.enabled && backupAccess.url && (
        <article className="glass-card liquid-panel">
          <p className="title-line">Резервное подключение</p>
          <p className="muted">
            {backupAccess.message || 'Основной сервер сейчас недоступен. Используйте резервную ссылку, чтобы продолжить работу без ожидания.'}
          </p>
          <div className="action-row">
            <a className="btn btn-primary" href={backupAccess.url} target="_blank" rel="noreferrer">
              <KeyRound size={16} /> {backupAccess.button_text}
            </a>
          </div>
        </article>
      )}

      {metricInfo && (
        <div className="modal-backdrop" onClick={() => setMetricInfo(null)}>
          <div className="modal-card liquid-modal metric-modal" onClick={(event) => event.stopPropagation()}>
            <div className="row-between">
              <div>
                <p className="title-line">{metricInfo === 'keys' ? 'Активные профили' : 'Бонусные дни'}</p>
                <p className="muted">{metricInfo === 'keys' ? 'Короткое объяснение текущего статуса профиля.' : 'Короткое объяснение бонусного баланса.'}</p>
              </div>
              <button className="icon-button" onClick={() => setMetricInfo(null)}><X size={16} /></button>
            </div>
            <p className="muted">
              {metricInfo === 'keys'
                ? 'Это количество активных профилей ZERO, которыми можно пользоваться прямо сейчас. Нажмите на кнопку открытия профиля, чтобы посмотреть детали и служебную ссылку.'
                : 'Это запас бесплатных дней, который можно использовать при следующем продлении. Бонусы начисляются за приглашения и специальные акции.'}
            </p>
          </div>
        </div>
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
              <div className="action-row compact-actions">
                <button className="btn btn-ghost" onClick={() => openTelegramPage(infoUrl)}>
                  <FileText size={16} /> Читать информацию
                </button>
                {support?.telegram_link ? (
                  <a className="btn btn-primary" href={support.telegram_link} target="_blank" rel="noreferrer">Написать в Telegram</a>
                ) : (
                  <p className="muted">Если контакт пока не показан, попробуйте открыть окно позже.</p>
                )}
              </div>
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
