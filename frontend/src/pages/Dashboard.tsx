import { useEffect, useState } from 'react'
import { Users, AlertTriangle, Activity, TrendingUp, Database } from 'lucide-react'
import KPICard from '../components/KPICard'
import DiseaseChart from '../components/DiseaseChart'
import TrendChart from '../components/TrendChart'
import AlertPanel from '../components/AlertPanel'
import PatientTable from '../components/PatientTable'
import api from '../api/client'

interface DashboardStats {
  total_visits_week: number
  total_cases: number
  high_risk_count: number
  active_alerts: number
  disease_distribution: Record<string, number>
  data_source: 'sinan_parquets' | 'db_visits' | 'no_data'
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

const SOURCE_LABEL: Record<string, string> = {
  sinan_parquets: 'Fonte: SINAN/DataSUS (dados epidemiológicos reais)',
  db_visits:      'Fonte: registros de visitas ACS',
  no_data:        'Sem dados — execute o pipeline ETL ou registre visitas',
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [visits, setVisits] = useState<Visit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
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
  const totalCases = stats?.total_cases ?? Object.values(dist).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Dashboard Epidemiológico</h1>
          <p className="mt-0.5 text-sm text-slate-500">Recife, PE — dados em tempo real</p>
        </div>
        {stats?.data_source && (
          <div className="flex items-center gap-1.5 rounded-lg bg-teal-50 px-3 py-1.5 text-xs text-teal-700">
            <Database size={12} />
            {SOURCE_LABEL[stats.data_source]}
          </div>
        )}
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
          title="Total de Casos"
          value={totalCases.toLocaleString('pt-BR')}
          subtitle="Notificações SINAN"
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
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
          <p className="text-sm text-slate-400">
            Sem dados epidemiológicos — execute o pipeline ETL para gerar os parquets SINAN.
          </p>
          <code className="mt-2 block text-xs text-slate-500">
            PYTHONPATH=data_pipeline python -m src.etl.run_pipeline
          </code>
        </div>
      )}

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
