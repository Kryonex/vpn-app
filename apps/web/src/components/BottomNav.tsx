import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Home' },
  { to: '/keys', label: 'My Keys' },
  { to: '/buy', label: 'Buy' },
  { to: '/payments', label: 'Payments' },
  { to: '/referrals', label: 'Referrals' },
  { to: '/help', label: 'Help' },
];

export function BottomNav() {
  const location = useLocation();

  return (
    <nav className="bottom-nav">
      {navItems.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className={location.pathname === item.to ? 'nav-link active' : 'nav-link'}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
