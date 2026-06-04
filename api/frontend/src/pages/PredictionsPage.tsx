import { useEffect, useState } from 'react';
import {
  generatePrediction,
  listPredictionModels,
  listPredictions,
} from '@/services/predictions';
import type { Prediction, PredictionModel } from '@/types';
import { formatDate, riskLevelColor, riskLevelLabel } from '@/utils';

export function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [models, setModels] = useState<PredictionModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<number | ''>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([listPredictions(), listPredictionModels()])
      .then(([preds, mods]) => {
        setPredictions(preds);
        setModels(mods);
        if (mods.length > 0 && selectedModel === '') {
          setSelectedModel(mods[0].id);
        }
      })
      .catch((err: { response?: { data?: { detail?: string } } }) => {
        setError(
          err.response?.data?.detail ??
            'Não foi possível carregar predições. Verifique se você tem perfil de paciente e sinais vitais.',
        );
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = async () => {
    if (selectedModel === '') return;
    setGenerating(true);
    setError(null);
    try {
      await generatePrediction(Number(selectedModel));
      load();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? 'Erro ao gerar predição.');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <p className="text-slate-600">Carregando predições...</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Predições de risco</h1>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {models.length > 0 && (
        <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Modelo</label>
            <select
              className="rounded-md border border-slate-300 px-3 py-2"
              value={selectedModel}
              onChange={(e) =>
                setSelectedModel(e.target.value ? Number(e.target.value) : '')
              }
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} (v{m.version})
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {generating ? 'Gerando...' : 'Nova predição'}
          </button>
        </div>
      )}

      {predictions.length === 0 ? (
        <p className="text-slate-600">Nenhuma predição registrada.</p>
      ) : (
        <ul className="space-y-3">
          {predictions.map((p) => (
            <li
              key={p.id}
              className="rounded-lg border border-slate-200 bg-white px-4 py-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{p.model_name ?? `Modelo #${p.model}`}</span>
                <span
                  className={`text-sm font-semibold ${riskLevelColor[p.risk_level] ?? ''}`}
                >
                  {p.risk_level_display ?? riskLevelLabel[p.risk_level]} ({p.probability}%)
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-500">{formatDate(p.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
