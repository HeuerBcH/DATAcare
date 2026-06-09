import { useState, FormEvent } from 'react'
import { CheckCircle } from 'lucide-react'
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

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

interface PredictionResult {
  disease: { predicted_class: string; probabilities: Record<string, number> }
  severity: { predicted_class: string; probabilities: Record<string, number> }
}

const diseaseLabel: Record<string, string> = {
  dengue: 'Dengue', chikungunya: 'Chikungunya', zika: 'Zika', influenza: 'Influenza'
}

const severityConfig: Record<string, { label: string; classes: string }> = {
  baixo: { label: 'Baixo Risco', classes: 'bg-emerald-50 border-emerald-300 text-emerald-800' },
  medio: { label: 'Médio Risco', classes: 'bg-amber-50 border-amber-300 text-amber-800' },
  alto:  { label: 'Alto Risco — Encaminhar imediatamente', classes: 'bg-red-50 border-red-300 text-red-800' },
}

export default function Triagem() {
  const [symptoms, setSymptoms] = useState<Record<string, boolean>>({})
  const [comorbidities, setComorbidities] = useState<Record<string, boolean>>({})
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('M')
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  function toggle(key: string, group: 'symptoms' | 'comorbidities') {
    if (group === 'symptoms') setSymptoms(s => ({ ...s, [key]: !s[key] }))
    else setComorbidities(s => ({ ...s, [key]: !s[key] }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setResult(null)

    const features: Record<string, number> = {
      age_years: Number(age) || 0,
      sex_M: sex === 'M' ? 1 : 0,
      notification_month: new Date().getMonth() + 1,
      notification_week: Math.ceil(new Date().getDate() / 7),
    }
    SYMPTOMS.forEach(s => { features[s.key] = symptoms[s.key] ? 1 : 0 })
    COMORBIDITIES.forEach(c => { features[c.key] = comorbidities[c.key] ? 1 : 0 })

    try {
      if (USE_MOCK) {
        // Simulate prediction based on symptom signals
        await new Promise(r => setTimeout(r, 600))
        const hasArtrite = features['ARTRITE']
        const hasExantema = features['EXANTEMA']
        const hasComorbidity = Object.values(comorbidities).some(Boolean)
        const isElderly = Number(age) >= 60

        const disease = hasArtrite ? 'chikungunya' : hasExantema ? 'zika' : 'dengue'
        const severity = (hasComorbidity && isElderly) ? 'alto' : hasComorbidity ? 'medio' : 'baixo'

        setResult({
          disease: {
            predicted_class: disease,
            probabilities: { [disease]: 0.72, dengue: 0.15, chikungunya: 0.08, zika: 0.05 }
          },
          severity: {
            predicted_class: severity,
            probabilities: { baixo: severity === 'baixo' ? 0.75 : 0.10, medio: severity === 'medio' ? 0.65 : 0.15, alto: severity === 'alto' ? 0.70 : 0.15 }
          }
        })
      } else {
        const { data } = await api.post('/api/v1/predict/', { features })
        setResult(data)
      }
      setSubmitted(true)
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setSymptoms({})
    setComorbidities({})
    setAge('')
    setSex('M')
    setResult(null)
    setSubmitted(false)
  }

  if (submitted && result) {
    const sev = severityConfig[result.severity.predicted_class] ?? severityConfig.baixo
    const diseaseTopProb = Math.max(...Object.values(result.disease.probabilities))
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <div className="flex items-center gap-2 text-emerald-600">
          <CheckCircle size={20} />
          <h1 className="text-lg font-bold">Triagem registrada</h1>
        </div>

        <div className={`rounded-xl border-2 p-5 ${sev.classes}`}>
          <p className="text-xl font-bold">{sev.label}</p>
          <p className="mt-1 text-sm">
            Doença provável: <strong>{diseaseLabel[result.disease.predicted_class]}</strong>
            {' '}({(diseaseTopProb * 100).toFixed(0)}% confiança)
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Probabilidades por doença</h3>
          {Object.entries(result.disease.probabilities).map(([d, p]) => (
            <div key={d} className="mb-2">
              <div className="flex justify-between text-xs text-slate-600 mb-0.5">
                <span>{diseaseLabel[d] ?? d}</span>
                <span>{(p * 100).toFixed(1)}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100">
                <div
                  className="h-1.5 rounded-full bg-teal-500"
                  style={{ width: `${p * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>

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
          Preencha os sintomas e dados do paciente para obter a predição
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Demographics */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Dados do Paciente</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Idade</label>
              <input
                type="number"
                min={0} max={120}
                value={age}
                onChange={e => setAge(e.target.value)}
                required
                placeholder="ex: 45"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Sexo</label>
              <select
                value={sex}
                onChange={e => setSex(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
              >
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
              </select>
            </div>
          </div>
        </div>

        {/* Symptoms */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Sintomas Presentes</h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {SYMPTOMS.map(s => (
              <label
                key={s.key}
                className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                  symptoms[s.key]
                    ? 'border-teal-400 bg-teal-50 text-teal-800'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={!!symptoms[s.key]}
                  onChange={() => toggle(s.key, 'symptoms')}
                />
                <span className={`h-4 w-4 shrink-0 rounded border-2 flex items-center justify-center ${symptoms[s.key] ? 'border-teal-500 bg-teal-500' : 'border-slate-300'}`}>
                  {symptoms[s.key] && <svg className="h-2.5 w-2.5 text-white" fill="currentColor" viewBox="0 0 12 12"><path d="M10 3L5 8.5 2 5.5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round"/></svg>}
                </span>
                {s.label}
              </label>
            ))}
          </div>
        </div>

        {/* Comorbidities */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Comorbidades</h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {COMORBIDITIES.map(c => (
              <label
                key={c.key}
                className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                  comorbidities[c.key]
                    ? 'border-amber-400 bg-amber-50 text-amber-800'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={!!comorbidities[c.key]}
                  onChange={() => toggle(c.key, 'comorbidities')}
                />
                <span className={`h-4 w-4 shrink-0 rounded border-2 flex items-center justify-center ${comorbidities[c.key] ? 'border-amber-500 bg-amber-500' : 'border-slate-300'}`}>
                  {comorbidities[c.key] && <svg className="h-2.5 w-2.5 text-white" fill="currentColor" viewBox="0 0 12 12"><path d="M10 3L5 8.5 2 5.5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round"/></svg>}
                </span>
                {c.label}
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !age}
          className="w-full rounded-lg bg-teal-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-50"
        >
          {loading ? 'Processando predição...' : 'Realizar Triagem'}
        </button>
      </form>
    </div>
  )
}
