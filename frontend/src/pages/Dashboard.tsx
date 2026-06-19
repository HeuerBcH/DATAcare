import { useEffect, useState } from 'react'
import { Users, AlertTriangle, Activity, TrendingUp } from 'lucide-react'
import KPICard from '../components/KPICard'
import DiseaseChart from '../components/DiseaseChart'
import TrendChart from '../components/TrendChart'
import AlertPanel from '../components/AlertPanel'
import PatientTable from '../components/PatientTable'
import api from '../api/client'
import { mockDashboardStats, mockTrendData, mockAlerts, mockRecentPatients } from '../api/mock'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

interface DashboardStats {
  total_visits_week: number
  total_visits: number
  high_risk_count: number
  active_alerts: number
  disease_distribution: Record<string, number>
}

interface Alert {
  id: number
  patient_name: string
  predicted_severity: string
  predicted_disease: string
  bairro: string
  created_at: string
}

interface TrendPoint {
  date: string
  dengue: number
  chikungunya: number
  zika: number
  influenza: number
}

interface Visit {
  id: number
  patient_name: string
  patient_age: number
  predicted_disease: string
  predicted_severity: string
  bairro: string
  acs_name: string
}

function mapVisitToTableRow(v: Visit) {
  return {
    id: v.id,
    name: v.patient_name,
    age: v.patient_age,
    disease: v.predicted_disease,
    risk: v.predicted_severity,
    bairro: v.bairro,
    acs: v.acs_name ?? '—',
  }
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [visits, setVisits] = useState<Visit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (USE_MOCK) {
      const dist = mockDashboardStats.disease_distribution
      setStats({
        ...mockDashboardStats,
        total_visits: Object.values(dist).reduce((a, b) => a + b, 0),
      })
      setAlerts(mockAlerts.map(a => ({
        id: a.id,
        patient_name: a.patient_name,
        predicted_severity: a.risk_level,
        predicted_disease: a.disease,
        bairro: a.bairro,
        created_at: a.created_at,
      })))
      setTrend(mockTrendData)
      setVisits(mockRecentPatients.map(p => ({
        id: p.id,
        patient_name: p.name,
        patient_age: p.age,
        predicted_disease: p.disease,
        predicted_severity: p.risk,
        bairro: p.bairro,
        acs_name: p.acs,
      })))
      setLoading(false)
      return
    }

    Promise.all([
      api.get<DashboardStats>('/api/v1/dashboard/stats/'),
      api.get<Alert[]>('/api/v1/dashboard/alerts/'),
      api.get<TrendPoint[]>('/api/v1/dashboard/trends/'),
      api.get<{ results?: Visit[] } | Visit[]>('/api/v1/visits/?page_size=8'),
    ])
      .then(([statsRes, alertsRes, trendRes, visitsRes]) => {
        setStats(statsRes.data)
        setAlerts(alertsRes.data)
        setTrend(trendRes.data)
        const raw = visitsRes.data
        setVisits(Array.isArray(raw) ? raw : (raw.results ?? []))
      })
      .catch(() => setError('Não foi possível conectar à API. Verifique se o backend está rodando.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
        <AlertTriangle size={32} className="text-amber-400" />
        <p className="text-sm text-slate-600">{error}</p>
        <code className="rounded bg-slate-100 px-3 py-1.5 text-xs text-slate-700">
          cd backend && python manage.py runserver
        </code>
      </div>
    )
  }

  const dist = stats?.disease_distribution ?? {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Dashboard Epidemiológico</h1>
          <p className="mt-0.5 text-sm text-slate-500">Recife, PE — dados em tempo real</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPICard
          title="Visitas na Semana"
          value={stats?.total_visits_week ?? 0}
          subtitle="Triagens ACS registradas"
          icon={<Users size={20} />}
        />
        <KPICard
          title="Total de Triagens"
          value={(stats?.total_visits ?? 0).toLocaleString('pt-BR')}
          subtitle="Registros no sistema"
          icon={<Activity size={20} />}
        />
        <KPICard
          title="Alto Risco"
          value={stats?.high_risk_count ?? 0}
          subtitle="Pacientes críticos"
          icon={<TrendingUp size={20} />}
          variant="danger"
        />
        <KPICard
          title="Alertas Ativos"
          value={stats?.active_alerts ?? 0}
          subtitle="Últimas 72 horas"
          icon={<AlertTriangle size={20} />}
          variant="warning"
        />
      </div>

      {/* Charts */}
      {(Object.keys(dist).length > 0 || trend.length > 0) ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {Object.keys(dist).length > 0 && <DiseaseChart data={dist} />}
          {trend.length > 0 && <TrendChart data={trend} />}
        </div>
      ) : null}

      {/* Alerts + Visits */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <AlertPanel alerts={alerts.map(a => ({
            id: a.id,
            patient_name: a.patient_name,
            risk_level: a.predicted_severity,
            disease: a.predicted_disease,
            bairro: a.bairro,
            created_at: a.created_at,
          }))} />
        </div>
        <div className="lg:col-span-2">
          <PatientTable patients={visits.map(mapVisitToTableRow)} />
        </div>
      </div>
    </div>
  )
}
