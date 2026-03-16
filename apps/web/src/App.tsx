import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { BottomNav } from './components/BottomNav';
import { ErrorState, LoadingState } from './components/StateCards';
import { useAuth } from './context/AuthContext';
import { AdminPage } from './pages/AdminPage';
import { BuyPlanPage } from './pages/BuyPlanPage';
import { HomePage } from './pages/HomePage';
import { KeyDetailsPage } from './pages/KeyDetailsPage';
import { KeysPage } from './pages/KeysPage';
import { NewsPage } from './pages/NewsPage';
import { RenewKeyPage } from './pages/RenewKeyPage';

export default function App() {
  const { isLoading, isAuthenticated, isAdmin, isExternalBrowser, error } = useAuth();

  const shell = (content: ReactNode, withNav = false) => (
    <div className="app-frame zero-frame">
      <div className="bg-layer bg-layer-a" />
      <div className="bg-layer bg-layer-b" />
      <div className="bg-grid" />
      <div className="container shell-layout">
        <main className="app-shell">{content}</main>
        {withNav && <div className="nav-dock" aria-hidden="true" />}
      </div>
      {withNav && <BottomNav />}
    </div>
  );

  if (isLoading) {
    return shell(<LoadingState text="Подготавливаем ZERO..." />);
  }

  if (!isAuthenticated) {
    if (isExternalBrowser) {
      return shell(
        <section className="browser-cover">
          <div className="browser-cover-logo">ZERO</div>
          <div className="browser-cover-mark" aria-hidden="true" />
          <div className="browser-cover-copy">
            <h1>ZERO</h1>
            <p>Похоже, эта страница открыта вне Telegram. Для обычного браузера здесь доступна только нейтральная заставка.</p>
          </div>
          <div className="browser-cover-actions">
            <a className="btn btn-primary browser-cover-btn" href="https://www.google.com/" target="_blank" rel="noreferrer">
              Перейти в Google
            </a>
          </div>
        </section>,
      );
    }

    return shell(
      <section className="stack">
        <h1>Нужна авторизация</h1>
        <ErrorState text={error ?? 'Не удалось открыть мини-приложение через Telegram.'} />
      </section>,
    );
  }

  return shell(
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/buy" element={<BuyPlanPage />} />
        <Route path="/news" element={<NewsPage />} />
        <Route path="/keys" element={<KeysPage />} />
        <Route path="/keys/:keyId" element={<KeyDetailsPage />} />
        <Route path="/keys/:keyId/renew" element={<RenewKeyPage />} />
        <Route path="/payments" element={<Navigate to="/buy" replace />} />
        <Route path="/referrals" element={<Navigate to="/" replace />} />
        <Route path="/support" element={<Navigate to="/" replace />} />
        <Route path="/help" element={<Navigate to="/" replace />} />
        <Route path="/admin" element={isAdmin ? <AdminPage /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>,
    true,
  );
}
