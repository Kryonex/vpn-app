import { CircleDollarSign, Home, KeyRound, Shield } from 'lucide-react';
import type { ComponentType } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

const navItems: Array<{ to: string; label: string; icon: ComponentType<{ size?: string | number }>; adminOnly?: boolean }> = [
  { to: '/', label: 'Кабинет', icon: Home },
  { to: '/keys', label: 'Ключи', icon: KeyRound },
  { to: '/buy', label: 'Купить', icon: CircleDollarSign },
  { to: '/admin', label: 'Админ', icon: Shield, adminOnly: true },
];

export function BottomNav() {
  const location = useLocation();
  const { isAdmin } = useAuth();
  const visibleItems = navItems.filter((item) => !item.adminOnly || isAdmin);

  return (
    <nav className="bottom-nav">
      {visibleItems.map((item) => {
        const Icon = item.icon;
        const active = item.to === '/'
          ? location.pathname === '/'
          : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
        return (
          <Link key={item.to} to={item.to} className={active ? 'nav-link active' : 'nav-link'}>
            <Icon size={16} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
