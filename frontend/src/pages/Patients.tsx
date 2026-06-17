import { useState, useEffect } from 'react'
import { Search, Filter, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import api from '../api/client'

interface Visit {
  id: number
  patient_name: string
  patient_age: number
  patient_sex: string
  bairro: string
  predicted_disease: string
  predicted_disease_display: string
  predicted_severity: string
  predicted_severity_display: string
  model_available: boolean
  acs_name: string | null
  created_at: string
}

const riskBadge: Record<string, string> = {
  alto:  'bg-red-100 text-red-700',
  medio: 'bg-amber-100 text-amber-700',
  baixo: 'bg-emerald-100 text-emerald-700',
}

const RISK_OPTIONS = ['todos', 'alto', 'medio', 'baixo']
const DISEASE_OPTIONS = ['todos', 'dengue', 'chikungunya', 'zika', 'influenza']

export default function Patients() {
  const [visits, setVisits] = useState<Visit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('todos')
  const [diseaseFilter, setDiseaseFilter] = useState('todos')

  useEffect(() => {
    api.get<Visit[]>('/api/v1/visits/')
      .then(res => setVisits(Array.isArray(res.data) ? res.data : (res.data as any).results ?? []))
      .catch(() => setError('Não foi possível carregar as visitas. Verifique se o backend está rodando.'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = visits.filter(v => {
    const matchSearch =
      v.patient_name.toLowerCase().includes(search.toLowerCase()) ||
      v.bairro.toLowerCase().includes(search.toLowerCase()) ||
      (v.acs_name ?? '').toLowerCase().includes(search.toLowerCase())
    const matchRisk = riskFilter === 'todos' || v.predicted_severity === riskFilter
    const matchDisease = diseaseFilter === 'todos' || v.predicted_disease === diseaseFilter
    return matchSearch && matchRisk && matchDisease
  })

  const counts = {
    alto:  visits.filter(v => v.predicted_severity === 'alto').length,
    medio: visits.filter(v => v.predicted_severity === 'medio').length,
    baixo: visits.filter(v => v.predicted_severity === 'baixo').length,
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
        <AlertTriangle size={28} className="text-amber-400" />
        <p className="text-sm text-slate-600">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Visitas / Triagens</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          {visits.length} registros de visitas ACS
        </p>
      </div>

      {/* Risk summary chips */}
      <div className="flex gap-3 flex-wrap">
        {(Object.entries(counts) as [string, number][]).map(([risk, count]) => (
          <button
            key={risk}
            onClick={() => setRiskFilter(riskFilter === risk ? 'todos' : risk)}
            className={clsx(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-all border',
              riskFilter === risk
                ? riskBadge[risk] + ' border-current'
                : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
            )}
          >
            {count} {risk === 'alto' ? 'alto risco' : risk === 'medio' ? 'médio risco' : 'baixo risco'}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text" placeholder="Buscar por paciente, bairro ou ACS..."
            value={search} onChange={e => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-200 pl-9 pr-4 py-2.5 text-sm outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-400" />
          <select
            value={diseaseFilter} onChange={e => setDiseaseFilter(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-teal-400"
          >
            {DISEASE_OPTIONS.map(d => (
              <option key={d} value={d}>{d === 'todos' ? 'Todas as doenças' : d.charAt(0).toUpperCase() + d.slice(1)}</option>
            ))}
          </select>
          <select
            value={riskFilter} onChange={e => setRiskFilter(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-teal-400"
          >
            {RISK_OPTIONS.map(r => (
              <option key={r} value={r}>{r === 'todos' ? 'Todos os riscos' : r.charAt(0).toUpperCase() + r.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-7 w-7 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60">
                <tr>
                  {['Paciente', 'Idade', 'Doença Predita', 'Risco', 'Bairro', 'ACS', 'Data'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map(v => (
                  <tr key={v.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-800">{v.patient_name}</td>
                    <td className="px-4 py-3 text-slate-600">{v.patient_age} anos</td>
                    <td className="px-4 py-3 text-slate-600">
                      {v.model_available ? v.predicted_disease_display : <span className="text-slate-400 italic">sem modelo</span>}
                    </td>
                    <td className="px-4 py-3">
                      {v.model_available ? (
                        <span className={clsx('rounded-full px-2.5 py-1 text-xs font-medium capitalize', riskBadge[v.predicted_severity] ?? 'bg-slate-100 text-slate-600')}>
                          {v.predicted_severity}
                        </span>
                      ) : <span className="text-slate-400 italic text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{v.bairro || '—'}</td>
                    <td className="px-4 py-3 text-slate-500">{v.acs_name ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(v.created_at).toLocaleDateString('pt-BR')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && !loading && (
              <div className="py-12 text-center">
                <p className="text-sm text-slate-400">
                  {visits.length === 0
                    ? 'Nenhuma visita registrada ainda. Use a triagem para criar registros.'
                    : 'Nenhum resultado para os filtros aplicados.'}
                </p>
              </div>
            )}
          </div>
          {filtered.length > 0 && (
            <div className="border-t border-slate-100 px-4 py-3 text-xs text-slate-400">
              Mostrando {filtered.length} de {visits.length} visitas
            </div>
          )}
        </div>
      )}
    </div>
  )
}
