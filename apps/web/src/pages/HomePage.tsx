import { KeyRound, Sparkles, Wallet } from 'lucide-react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/PageHeader';
import { EmptyState } from '../components/StateCards';
import { useAuth } from '../context/AuthContext';

export function HomePage() {
  const { me } = useAuth();

  if (!me) {
    return <EmptyState title="Нет данных профиля" text="Переоткройте Mini App." />;
  }

  const nearestExpiry = me.nearest_expiry
    ? new Date(me.nearest_expiry).toLocaleString()
    : 'Нет активных подписок';

  return (
    <section className="stack">
      <PageHeader title="Кабинет" subtitle="Управляйте VPN-подписками в одном месте" />

      <article className="hero-card">
        <p className="hero-label">Добро пожаловать</p>
        <p className="hero-title">Ваш VPN-центр управления</p>
        <p className="hero-subtitle">Ключи, платежи и рефералы в одном интерфейсе.</p>
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
    </section>
  );
}
