import { createBrowserRouter, Navigate } from 'react-router-dom'
import Layout from '../components/Layout'
import ProtectedRoute from '../components/ProtectedRoute'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Triagem from '../pages/Triagem'
import Predictions from '../pages/Predictions'
import Patients from '../pages/Patients'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute allowedRoles={['gestor', 'admin']}>
            <Dashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'triagem',
        element: (
          <ProtectedRoute allowedRoles={['acs', 'profissional_saude', 'admin']}>
            <Triagem />
          </ProtectedRoute>
        ),
      },
      {
        path: 'pacientes',
        element: (
          <ProtectedRoute allowedRoles={['gestor', 'profissional_saude', 'admin']}>
            <Patients />
          </ProtectedRoute>
        ),
      },
      {
        path: 'predicoes',
        element: (
          <ProtectedRoute allowedRoles={['gestor', 'profissional_saude', 'admin']}>
            <Predictions />
          </ProtectedRoute>
        ),
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])
