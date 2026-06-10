import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ProtectedRoute, homeForRole } from './components/ProtectedRoute';
import { useAuth } from './context/AuthContext';
import Alerts from './pages/Alerts';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import TriageForm from './pages/TriageForm';
import Visits from './pages/Visits';

export default function App() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute roles={['gestor', 'admin']}>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="/triagem" element={<TriageForm />} />
        <Route path="/visitas" element={<Visits />} />
        <Route
          path="/alertas"
          element={
            <ProtectedRoute roles={['gestor', 'admin']}>
              <Alerts />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to={user ? homeForRole(user.role) : '/login'} replace />} />
    </Routes>
  );
}
