import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Criminals from '@/pages/Criminals';
import Identify from '@/pages/Identify';
import Alerts from '@/pages/Alerts';
import { AuthGuard } from '@/components/layout/AuthGuard';
import DashboardLayout from '@/components/layout/DashboardLayout';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Dashboard Routes */}
        <Route
          path="/dashboard"
          element={
            <AuthGuard>
              <DashboardLayout />
            </AuthGuard>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="criminals" element={<Criminals />} />
          <Route path="identify" element={<Identify />} />
          <Route path="alerts" element={<Alerts />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
