import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
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
          <Route path="criminals" element={<div>Criminals Page (Coming Soon)</div>} />
          <Route path="identify" element={<div>Identify Page (Coming Soon)</div>} />
          <Route path="alerts" element={<div>Alerts Page (Coming Soon)</div>} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
