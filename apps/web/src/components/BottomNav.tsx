import { CircleDollarSign, HelpCircle, Home, KeyRound, ReceiptText, Users } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Главная', icon: Home },
  { to: '/keys', label: 'Ключи', icon: KeyRound },
  { to: '/buy', label: 'Купить', icon: CircleDollarSign },
  { to: '/payments', label: 'Платежи', icon: ReceiptText },
  { to: '/referrals', label: 'Рефералы', icon: Users },
  { to: '/help', label: 'Помощь', icon: HelpCircle },
];

export function BottomNav() {
  const location = useLocation();

  return (
    <nav className="bottom-nav">
      {navItems.map((item) => {
        const Icon = item.icon;
        const active = location.pathname === item.to;
        return (
          <Link
            key={item.to}
            to={item.to}
            className={active ? 'nav-link active' : 'nav-link'}
          >
            <Icon size={16} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
