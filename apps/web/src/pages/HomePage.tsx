import { KeyRound, Sparkles, Wallet } from 'lucide-react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { EmptyState } from '../components/StateCards';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';

export function HomePage() {
  const { me, telegramProfile, systemStatus } = useAuth();

  if (!me) {
    return <EmptyState title="Нет данных профиля" text="Переоткройте Mini App." />;
  }

  const nearestExpiry = me.nearest_expiry
    ? new Date(me.nearest_expiry).toLocaleString()
    : 'Нет активных подписок';
  const displayName =
    telegramProfile?.first_name ||
    me.telegram?.first_name ||
    me.telegram?.username ||
    'Пользователь';
  const username = telegramProfile?.username || me.telegram?.username || null;
  const avatar = telegramProfile?.photo_url || null;

  return (
    <section className="stack">
      <PageHeader title="Кабинет" subtitle="Управляйте VPN-подписками в одном месте" />
      <SystemStatusBanner status={systemStatus} />

      <article className="hero-card welcome-enter">
        <div className="profile-row">
          {avatar ? (
            <img className="profile-avatar" src={avatar} alt="Аватар" />
          ) : (
            <div className="profile-avatar profile-avatar-fallback">{displayName.slice(0, 1).toUpperCase()}</div>
          )}
          <div>
            <p className="profile-name">{displayName}</p>
            <p className="profile-username">{username ? `@${username}` : 'Telegram клиент'}</p>
          </div>
        </div>
        <p className="hero-label greeting-chip">Добро пожаловать</p>
        <p className="hero-title welcome-line-1">Ваш VPN-центр управления</p>
        <p className="hero-subtitle welcome-line-2">Ключи, платежи и рефералы в одном интерфейсе.</p>
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

      <article className="glass-card">
        <p className="muted">Ближайшее истечение</p>
        <p className="title-line">{nearestExpiry}</p>
      </article>

      <article className="glass-card">
        <p className="muted">Реферальная активность</p>
        <p className="title-line">Приглашено пользователей: {me.invited_count}</p>
      </article>

      <div className="action-row">
        <Link className="btn btn-primary" to="/buy">
          <Wallet size={16} /> Купить тариф
        </Link>
        <Link className="btn btn-ghost" to="/keys">
          <KeyRound size={16} /> Мои ключи
        </Link>
      </div>

      {systemStatus?.maintenance_mode && (
        <article className="glass-card">
          <p className="title-line">Режим обслуживания</p>
          <p className="muted">Операции с подписками могут быть временно ограничены. Статус системы отображается выше.</p>
        </article>
      )}
    </section>
  );
}
