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
import { PaymentsPage } from './pages/PaymentsPage';
import { ReferralsPage } from './pages/ReferralsPage';
import { RenewKeyPage } from './pages/RenewKeyPage';
import { SupportPage } from './pages/SupportPage';

export default function App() {
  const { isLoading, isAuthenticated, isAdmin, error } = useAuth();

  const shell = (content: ReactNode) => (
    <div className="app-frame">
      <div className="bg-layer bg-layer-a" />
      <div className="bg-layer bg-layer-b" />
      <div className="bg-grid" />
      <main className="container app-shell">{content}</main>
    </div>
  );

  if (isLoading) {
    return shell(<LoadingState text="Загружаем кабинет..." />);
  }

  if (!isAuthenticated) {
    return shell(
      <section className="stack">
        <h1>Ошибка авторизации</h1>
        <ErrorState text={error ?? 'Откройте приложение внутри Telegram Mini App.'} />
      </section>,
    );
  }

  return shell(
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/keys" element={<KeysPage />} />
        <Route path="/keys/:keyId" element={<KeyDetailsPage />} />
        <Route path="/keys/:keyId/renew" element={<RenewKeyPage />} />
        <Route path="/buy" element={<BuyPlanPage />} />
        <Route path="/payments" element={<PaymentsPage />} />
        <Route path="/referrals" element={<ReferralsPage />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/help" element={<SupportPage />} />
        <Route path="/admin" element={isAdmin ? <AdminPage /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomNav />
    </>,
  );
}
