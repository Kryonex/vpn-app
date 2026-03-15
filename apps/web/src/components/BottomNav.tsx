import { CircleDollarSign, Home, Newspaper, Shield } from 'lucide-react';
import { useEffect, useLayoutEffect, useRef, useState, type ComponentType, type CSSProperties } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

const navItems: Array<{ to: string; label: string; icon: ComponentType<{ size?: string | number }>; adminOnly?: boolean }> = [
  { to: '/', label: 'Дом', icon: Home },
  { to: '/buy', label: 'Купить', icon: CircleDollarSign },
  { to: '/news', label: 'Новости', icon: Newspaper },
  { to: '/admin', label: 'Админ', icon: Shield, adminOnly: true },
];

export function BottomNav() {
  const location = useLocation();
  const { isAdmin } = useAuth();
  const visibleItems = navItems.filter((item) => !item.adminOnly || isAdmin);
  const navRef = useRef<HTMLElement | null>(null);
  const linkRefs = useRef<Record<string, HTMLAnchorElement | null>>({});
  const [indicatorStyle, setIndicatorStyle] = useState<CSSProperties>({ opacity: 0, width: 0, transform: 'translateX(0px)' });

  const syncIndicator = () => {
    const activeItem = visibleItems.find((item) => item.to === '/'
      ? location.pathname === '/'
      : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`));
    if (!activeItem || !navRef.current) {
      setIndicatorStyle((prev) => ({ ...prev, opacity: 0 }));
      return;
    }

    const activeLink = linkRefs.current[activeItem.to];
    if (!activeLink) {
      return;
    }

    const navRect = navRef.current.getBoundingClientRect();
    const linkRect = activeLink.getBoundingClientRect();
    setIndicatorStyle({
      opacity: 1,
      width: `${linkRect.width}px`,
      transform: `translateX(${linkRect.left - navRect.left}px)`,
    });
  };

  useLayoutEffect(() => {
    const frame = window.requestAnimationFrame(syncIndicator);
    return () => window.cancelAnimationFrame(frame);
  }, [location.pathname, isAdmin]);

  useEffect(() => {
    const handleResize = () => syncIndicator();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [location.pathname, isAdmin]);

  return (
    <div className="bottom-nav-shell">
      <nav className="bottom-nav" ref={navRef}>
        <span className="nav-indicator" style={indicatorStyle} aria-hidden="true" />
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const active = item.to === '/'
            ? location.pathname === '/'
            : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
          return (
            <Link
              key={item.to}
              to={item.to}
              ref={(node) => { linkRefs.current[item.to] = node; }}
              className={active ? 'nav-link active' : 'nav-link'}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
