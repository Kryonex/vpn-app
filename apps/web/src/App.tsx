import { Navigate, Route, Routes } from 'react-router-dom';

import { BottomNav } from './components/BottomNav';
import { ErrorState, LoadingState } from './components/StateCards';
import { useAuth } from './context/AuthContext';
import { BuyPlanPage } from './pages/BuyPlanPage';
import { HelpPage } from './pages/HelpPage';
import { HomePage } from './pages/HomePage';
import { KeyDetailsPage } from './pages/KeyDetailsPage';
import { KeysPage } from './pages/KeysPage';
import { PaymentsPage } from './pages/PaymentsPage';
import { ReferralsPage } from './pages/ReferralsPage';
import { RenewKeyPage } from './pages/RenewKeyPage';

export default function App() {
  const { isLoading, isAuthenticated, error } = useAuth();

  if (isLoading) {
    return (
      <main className="container app-shell">
        <LoadingState text="Загружаем кабинет..." />
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="container app-shell">
        <section className="stack">
          <h1>Ошибка авторизации</h1>
          <ErrorState text={error ?? 'Откройте приложение внутри Telegram Mini App.'} />
        </section>
      </main>
    );
  }

  return (
    <main className="container app-shell">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/keys" element={<KeysPage />} />
        <Route path="/keys/:keyId" element={<KeyDetailsPage />} />
        <Route path="/keys/:keyId/renew" element={<RenewKeyPage />} />
        <Route path="/buy" element={<BuyPlanPage />} />
        <Route path="/payments" element={<PaymentsPage />} />
        <Route path="/referrals" element={<ReferralsPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomNav />
    </main>
  );
}
