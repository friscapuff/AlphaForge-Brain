import { Routes, Route, Navigate } from 'react-router-dom';
import { ChartAnalysisPage } from './pages/ChartAnalysisPage.js';
import { BacktestValidationPage } from './pages/BacktestValidationPage.js';
import { DashboardPage } from './pages/DashboardPage.js';
import SlowNotice from './components/common/SlowNotice.js';
import TrustGateAlertToast from './components/common/TrustGateAlertToast.js';

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/charts" replace />} />
  <Route path="/charts" element={<ChartAnalysisPage />} />
  <Route path="/backtest" element={<BacktestValidationPage />} />
  <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
  <SlowNotice />
  <TrustGateAlertToast />
    </>
  );
}
