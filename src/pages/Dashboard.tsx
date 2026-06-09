import { useEffect, useState } from 'react'
import { Users, AlertTriangle, Activity, TrendingUp } from 'lucide-react'
import KPICard from '../components/KPICard'
import DiseaseChart from '../components/DiseaseChart'
import TrendChart from '../components/TrendChart'
import AlertPanel from '../components/AlertPanel'
import PatientTable from '../components/PatientTable'
import api from '../api/client'
import {
  mockDashboardStats, mockTrendData, mockAlerts, mockRecentPatients
} from '../api/mock'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

interface DashboardStats {
  total_visits_week: number
  high_risk_count: number
  active_alerts: number
  disease_distribution: Record<string, number>
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [alerts, setAlerts] = useState(mockAlerts)
  const [patients, setPatients] = useState(mockRecentPatients)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (USE_MOCK) {
      setStats(mockDashboardStats)
      setLoading(false)
      return
    }

    Promise.all([
      api.get('/api/v1/dashboard/stats/').catch(() => ({ data: mockDashboardStats })),
      api.get('/api/v1/dashboard/alerts/').catch(() => ({ data: mockAlerts })),
      api.get('/api/v1/patients/?ordering=-created_at&page_size=6').catch(() => ({ data: { results: mockRecentPatients } })),
    ]).then(([statsRes, alertsRes, patientsRes]) => {
      setStats(statsRes.data)
      setAlerts(alertsRes.data)
      setPatients(patientsRes.data.results ?? patientsRes.data)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
      </div>
    )
  }

  const dist = stats?.disease_distribution ?? {}
  const totalCases = Object.values(dist).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-800">Dashboard</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Visão geral da semana epidemiológica atual — Recife, PE
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPICard
          title="Visitas na Semana"
          value={stats?.total_visits_week ?? 0}
          subtitle="ACS registradas"
          icon={<Users size={20} />}
          trend={{ value: 12, label: 'vs. semana passada' }}
        />
        <KPICard
          title="Total de Casos"
          value={totalCases}
          subtitle="Notificações confirmadas"
          icon={<Activity size={20} />}
          variant="default"
        />
        <KPICard
          title="Alto Risco"
          value={stats?.high_risk_count ?? 0}
          subtitle="Pacientes críticos"
          icon={<TrendingUp size={20} />}
          variant="danger"
          trend={{ value: 8, label: 'vs. semana passada' }}
        />
        <KPICard
          title="Alertas Ativos"
          value={stats?.active_alerts ?? 0}
          subtitle="Requerem atenção"
          icon={<AlertTriangle size={20} />}
          variant="warning"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <DiseaseChart data={dist} />
        <TrendChart data={mockTrendData} />
      </div>

      {/* Alerts + Table */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <AlertPanel alerts={alerts} />
        </div>
        <div className="lg:col-span-2">
          <PatientTable patients={patients} />
        </div>
      </div>
    </div>
  )
}
