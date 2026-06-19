import { useState, useEffect } from 'react'
import { Activity, TrendingUp } from 'lucide-react'
import clsx from 'clsx'
import api from '../api/client'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

interface ModelInfo {
  name: string
  description: string
  accuracy: number
  model_type: string
  version: string
}

const mockModels: ModelInfo[] = [
  {
    name: 'disease_classifier',
    description: 'Classifica o tipo de arbovirose (dengue, chikungunya, zika) ou influenza com base nos sintomas e dados demográficos.',
    accuracy: 0.83,
    model_type: 'XGBoost',
    version: '1.0.0',
  },
  {
    name: 'severity_classifier',
    description: 'Estratifica o risco do paciente em baixo, médio ou alto com base em sintomas, comorbidades e dados clínicos.',
    accuracy: 0.79,
    model_type: 'XGBoost',
    version: '1.0.0',
  },
]

const accuracyColor = (acc: number) => {
  if (acc >= 0.80) return 'text-emerald-600'
  if (acc >= 0.70) return 'text-amber-600'
  return 'text-red-600'
}

export default function Predictions() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (USE_MOCK) {
      setModels(mockModels)
      setLoading(false)
      return
    }
    api.get('/api/v1/prediction-models/')
      .then(res => setModels(res.data.results ?? res.data))
      .catch(() => setModels(mockModels))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Modelos de Predição</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Modelos de machine learning treinados com dados do SINAN e SRAG — Recife, PE
        </p>
      </div>

      {loading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-7 w-7 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {models.map(model => (
            <div
              key={model.name}
              className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="mb-4 flex items-start justify-between">
                <div className="flex items-center gap-2">
                  {model.name.includes('disease') ? (
                    <Activity size={20} className="text-teal-600" />
                  ) : (
                    <TrendingUp size={20} className="text-amber-600" />
                  )}
                  <h3 className="font-semibold text-slate-800">
                    {model.name === 'disease_classifier'
                      ? 'Classificador de Doença'
                      : 'Classificador de Gravidade'}
                  </h3>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
                  v{model.version}
                </span>
              </div>

              <p className="mb-5 text-sm text-slate-500 leading-relaxed">{model.description}</p>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Acurácia</p>
                  <p className={clsx('text-xl font-bold', accuracyColor(model.accuracy))}>
                    {(model.accuracy * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Algoritmo</p>
                  <p className="text-sm font-semibold text-slate-700">{model.model_type}</p>
                </div>
              </div>

              {model.name === 'disease_classifier' && (
                <div className="mt-4 rounded-lg border border-teal-100 bg-teal-50 p-3 text-xs text-teal-700">
                  <strong>Classes:</strong> Dengue · Chikungunya · Zika · Influenza
                </div>
              )}
              {model.name === 'severity_classifier' && (
                <div className="mt-4 rounded-lg border border-amber-100 bg-amber-50 p-3 text-xs text-amber-700">
                  <strong>Classes:</strong> Baixo Risco · Médio Risco · Alto Risco
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Dados de Treinamento</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
          {[
            { label: 'SINAN Dengue', value: 'DataSUS 2025' },
            { label: 'SINAN Chikungunya', value: 'DataSUS 2025' },
            { label: 'SINAN Zika', value: 'DataSUS 2025' },
            { label: 'SRAG Influenza', value: 'DataSUS 2025' },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs font-medium text-slate-700">{label}</p>
              <p className="text-xs text-slate-500">{value}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-400">
          Treinados com dados epidemiológicos do Ministério da Saúde (DataSUS).
          Resultados para triagem de apoio clínico — não substituem avaliação médica.
        </p>
      </div>
    </div>
  )
}
