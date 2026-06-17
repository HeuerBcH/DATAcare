import { AlertTriangle, Clock } from 'lucide-react'
import clsx from 'clsx'

interface Alert {
  id: number
  patient_name: string
  risk_level: string
  disease: string
  bairro: string
  created_at: string
}

interface Props {
  alerts: Alert[]
}

const riskConfig: Record<string, { label: string; classes: string }> = {
  alto:  { label: 'Alto',  classes: 'bg-red-100 text-red-700' },
  medio: { label: 'Médio', classes: 'bg-amber-100 text-amber-700' },
  baixo: { label: 'Baixo', classes: 'bg-emerald-100 text-emerald-700' },
}

const diseaseLabel: Record<string, string> = {
  dengue: 'Dengue',
  chikungunya: 'Chikungunya',
  zika: 'Zika',
  influenza: 'Influenza',
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  if (h > 0) return `há ${h}h${m > 0 ? ` ${m}min` : ''}`
  return `há ${m}min`
}

export default function AlertPanel({ alerts }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Alertas Recentes</h3>
        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
          {alerts.filter(a => a.risk_level === 'alto').length} críticos
        </span>
      </div>
      <div className="space-y-2">
        {alerts.map(alert => {
          const risk = riskConfig[alert.risk_level] ?? riskConfig.baixo
          return (
            <div
              key={alert.id}
              className="flex items-start gap-3 rounded-lg border border-slate-100 p-3 hover:bg-slate-50 transition-colors"
            >
              <AlertTriangle
                size={16}
                className={clsx('mt-0.5 shrink-0', alert.risk_level === 'alto' ? 'text-red-500' : 'text-amber-500')}
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-slate-800">{alert.patient_name}</span>
                  <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium', risk.classes)}>
                    {risk.label}
                  </span>
                  <span className="text-xs text-slate-500">{diseaseLabel[alert.disease] ?? alert.disease}</span>
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
                  <span>{alert.bairro}</span>
                  <span>·</span>
                  <Clock size={11} />
                  <span>{formatRelative(alert.created_at)}</span>
                </div>
              </div>
            </div>
          )
        })}
        {alerts.length === 0 && (
          <p className="py-6 text-center text-sm text-slate-400">Nenhum alerta ativo</p>
        )}
      </div>
    </div>
  )
}
