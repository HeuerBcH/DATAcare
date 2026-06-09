import { useState, FormEvent } from 'react'
import { CheckCircle, AlertTriangle } from 'lucide-react'
import api from '../api/client'

const SYMPTOMS = [
  { key: 'FEBRE', label: 'Febre' },
  { key: 'MIALGIA', label: 'Mialgia (dor muscular)' },
  { key: 'CEFALEIA', label: 'Cefaleia (dor de cabeça)' },
  { key: 'EXANTEMA', label: 'Exantema (erupção cutânea)' },
  { key: 'VOMITO', label: 'Vômito' },
  { key: 'NAUSEA', label: 'Náusea' },
  { key: 'DOR_COSTAS', label: 'Dor nas costas' },
  { key: 'CONJUNTVIT', label: 'Conjuntivite' },
  { key: 'ARTRITE', label: 'Artrite' },
  { key: 'ARTRALGIA', label: 'Artralgia (dor nas juntas)' },
  { key: 'PETEQUIA_N', label: 'Petéquias' },
  { key: 'LEUCOPENIA', label: 'Leucopenia' },
  { key: 'LACO', label: 'Prova do Laço positiva' },
  { key: 'DOR_RETRO', label: 'Dor retroorbitária' },
]

const COMORBIDITIES = [
  { key: 'DIABETES', label: 'Diabetes' },
  { key: 'HIPERTENSA', label: 'Hipertensão' },
  { key: 'RENAL', label: 'Doença Renal' },
  { key: 'HEPATOPAT', label: 'Hepatopatia' },
  { key: 'HEMATOLOG', label: 'Doença Hematológica' },
  { key: 'AUTO_IMUNE', label: 'Doença Autoimune' },
]

interface VisitResult {
  id: number
  patient_name: string
  predicted_disease: string
  predicted_disease_display: string
  predicted_severity: string
  predicted_severity_display: string
  disease_probabilities: Record<string, number>
  severity_probabilities: Record<string, number>
  model_available: boolean
}

const severityConfig: Record<string, { label: string; classes: string }> = {
  baixo: { label: 'Baixo Risco', classes: 'bg-emerald-50 border-emerald-300 text-emerald-800' },
  medio: { label: 'Médio Risco — acompanhar de perto', classes: 'bg-amber-50 border-amber-300 text-amber-800' },
  alto:  { label: 'Alto Risco — encaminhar imediatamente', classes: 'bg-red-50 border-red-300 text-red-800' },
}

function CheckboxGroup({
  items,
  state,
  onToggle,
  color,
}: {
  items: { key: string; label: string }[]
  state: Record<string, boolean>
  onToggle: (key: string) => void
  color: 'teal' | 'amber'
}) {
  const active = color === 'teal'
    ? 'border-teal-400 bg-teal-50 text-teal-800'
    : 'border-amber-400 bg-amber-50 text-amber-800'
  const checkActive = color === 'teal' ? 'border-teal-500 bg-teal-500' : 'border-amber-500 bg-amber-500'

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {items.map(item => (
        <label
          key={item.key}
          className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
            state[item.key] ? active : 'border-slate-200 text-slate-600 hover:border-slate-300'
          }`}
        >
          <input
            type="checkbox"
            className="sr-only"
            checked={!!state[item.key]}
            onChange={() => onToggle(item.key)}
          />
          <span className={`h-4 w-4 shrink-0 rounded border-2 flex items-center justify-center ${
            state[item.key] ? checkActive : 'border-slate-300'
          }`}>
            {state[item.key] && (
              <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 12 12"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <path d="M2 6l3 3 5-5" />
              </svg>
            )}
          </span>
          {item.label}
        </label>
      ))}
    </div>
  )
}

export default function Triagem() {
  const [patientName, setPatientName] = useState('')
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('M')
  const [bairro, setBairro] = useState('')
  const [symptoms, setSymptoms] = useState<Record<string, boolean>>({})
  const [comorbidities, setComorbidities] = useState<Record<string, boolean>>({})
  const [result, setResult] = useState<VisitResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function toggle(key: string, group: 'symptoms' | 'comorbidities') {
    if (group === 'symptoms') setSymptoms(s => ({ ...s, [key]: !s[key] }))
    else setComorbidities(c => ({ ...c, [key]: !c[key] }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')

    const symptomData: Record<string, number> = {}
    SYMPTOMS.forEach(s => { symptomData[s.key] = symptoms[s.key] ? 1 : 0 })

    const comorbidityData: Record<string, number> = {}
    COMORBIDITIES.forEach(c => { comorbidityData[c.key] = comorbidities[c.key] ? 1 : 0 })

    try {
      const { data } = await api.post<VisitResult>('/api/v1/visits/', {
        patient_name: patientName,
        patient_age: Number(age),
        patient_sex: sex,
        bairro,
        symptoms: symptomData,
        comorbidities: comorbidityData,
      })
      setResult(data)
    } catch {
      setError('Erro ao registrar visita. Verifique se o backend está rodando.')
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setPatientName(''); setAge(''); setSex('M'); setBairro('')
    setSymptoms({}); setComorbidities({}); setResult(null); setError('')
  }

  if (result) {
    const sev = severityConfig[result.predicted_severity] ?? severityConfig.baixo
    const topProb = Math.max(...Object.values(result.disease_probabilities))
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <div className="flex items-center gap-2 text-emerald-600">
          <CheckCircle size={20} />
          <h1 className="text-lg font-bold">Triagem registrada — {result.patient_name}</h1>
        </div>

        {!result.model_available && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
            <AlertTriangle size={14} />
            Modelos ML não treinados — predição indisponível. A visita foi salva.
          </div>
        )}

        {result.model_available && (
          <>
            <div className={`rounded-xl border-2 p-5 ${sev.classes}`}>
              <p className="text-xl font-bold">{sev.label}</p>
              <p className="mt-1 text-sm">
                Doença provável: <strong>{result.predicted_disease_display}</strong>
                {' '}({(topProb * 100).toFixed(0)}% confiança)
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="mb-3 text-sm font-semibold text-slate-700">Probabilidades por doença</h3>
              {Object.entries(result.disease_probabilities)
                .sort(([, a], [, b]) => b - a)
                .map(([d, p]) => (
                  <div key={d} className="mb-2">
                    <div className="flex justify-between text-xs text-slate-600 mb-0.5">
                      <span className="capitalize">{d}</span>
                      <span>{(p * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100">
                      <div className="h-1.5 rounded-full bg-teal-500" style={{ width: `${p * 100}%` }} />
                    </div>
                  </div>
                ))}
            </div>
          </>
        )}

        <button
          onClick={reset}
          className="w-full rounded-lg border border-teal-300 px-4 py-2.5 text-sm font-medium text-teal-700 hover:bg-teal-50 transition-colors"
        >
          Nova triagem
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-800">Nova Triagem</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Dados salvos no banco de dados e processados pelos modelos ML
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Dados do Paciente</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600">Nome completo</label>
              <input
                type="text" value={patientName} onChange={e => setPatientName(e.target.value)}
                required placeholder="Nome do paciente"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Idade</label>
              <input
                type="number" min={0} max={120} value={age} onChange={e => setAge(e.target.value)}
                required placeholder="ex: 45"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Sexo</label>
              <select
                value={sex} onChange={e => setSex(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
              >
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600">Bairro</label>
              <input
                type="text" value={bairro} onChange={e => setBairro(e.target.value)}
                placeholder="ex: Ibura"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
              />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Sintomas Presentes</h2>
          <CheckboxGroup items={SYMPTOMS} state={symptoms} onToggle={k => toggle(k, 'symptoms')} color="teal" />
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Comorbidades</h2>
          <CheckboxGroup items={COMORBIDITIES} state={comorbidities} onToggle={k => toggle(k, 'comorbidities')} color="amber" />
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertTriangle size={14} />
            {error}
          </div>
        )}

        <button
          type="submit" disabled={loading || !patientName || !age}
          className="w-full rounded-lg bg-teal-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-50"
        >
          {loading ? 'Registrando...' : 'Registrar Triagem'}
        </button>
      </form>
    </div>
  )
}
