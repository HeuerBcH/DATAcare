import { useEffect, useState } from 'react';
import { format, parseISO } from 'date-fns';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { api } from '../lib/api';
import type { Paginated, RiskLevel, Visit } from '../lib/types';
import { RiskBadge } from '../components/RiskBadge';

const FILTERS: { key: RiskLevel | 'todos'; label: string }[] = [
  { key: 'todos', label: 'Todos' },
  { key: 'alto', label: 'Alto' },
  { key: 'medio', label: 'Médio' },
  { key: 'baixo', label: 'Baixo' },
];

export default function Visits() {
  const [page, setPage] = useState(1);
  const [risk, setRisk] = useState<RiskLevel | 'todos'>('todos');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [data, setData] = useState<Paginated<Visit> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string | number> = { page, ordering: '-visit_date' };
    if (risk !== 'todos') params.risk_level = risk;
    if (query) params.search = query;
    api
      .get<Paginated<Visit>>('/triage/visits/', { params })
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [page, risk, query]);

  const totalPages = data ? Math.max(1, Math.ceil(data.count / 20)) : 1;

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6">
        <p className="eyebrow">Triagens</p>
        <h1 className="mt-1 font-display text-3xl font-600 text-ink">Visitas registradas</h1>
        <p className="mt-1 text-sm text-ink-soft">Histórico de triagens com o risco previsto pelo modelo.</p>
      </header>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1.5">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => {
                setRisk(f.key);
                setPage(1);
              }}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                risk === f.key ? 'bg-brand-700 text-white' : 'bg-surface-raised text-ink-soft hover:bg-surface-sunken'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(search);
            setPage(1);
          }}
          className="relative"
        >
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            className="input py-2 pl-9 sm:w-64"
            placeholder="Buscar paciente ou CPF…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </form>
      </div>

      <div className="card overflow-hidden">
        <div className="hidden grid-cols-[1.6fr_0.6fr_1fr_0.8fr_auto] gap-3 border-b border-line bg-surface-sunken/50 px-5 py-3 text-[0.7rem] font-semibold uppercase tracking-wide text-ink-faint sm:grid">
          <span>Paciente</span>
          <span>Idade</span>
          <span>Data</span>
          <span>Sintomas</span>
          <span className="text-right">Risco</span>
        </div>
        <div className="divide-y divide-line">
          {loading && <p className="px-5 py-10 text-center text-sm text-ink-faint">Carregando…</p>}
          {!loading && data?.results.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-ink-faint">Nenhuma triagem encontrada.</p>
          )}
          {!loading &&
            data?.results.map((v) => (
              <div
                key={v.id}
                className="grid grid-cols-2 gap-2 px-5 py-3.5 text-sm sm:grid-cols-[1.6fr_0.6fr_1fr_0.8fr_auto] sm:items-center sm:gap-3"
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-ink">{v.patient_name}</p>
                  <p className="truncate text-xs text-ink-faint">{v.acs_name || 'ACS não informado'}</p>
                </div>
                <span className="text-ink-soft">{v.patient_age} anos</span>
                <span className="text-ink-soft">{format(parseISO(v.visit_date), 'dd/MM/yyyy')}</span>
                <span className="text-ink-soft">
                  {v.symptoms.length} <span className="text-ink-faint">sintoma(s)</span>
                </span>
                <div className="flex justify-start sm:justify-end">
                  <RiskBadge level={v.risk_level} score={v.risk_score} showScore />
                </div>
              </div>
            ))}
        </div>
      </div>

      {data && data.count > 20 && (
        <div className="mt-4 flex items-center justify-between text-sm text-ink-soft">
          <span>
            {data.count} triagens · página {page}/{totalPages}
          </span>
          <div className="flex gap-2">
            <button className="btn-ghost px-3 py-1.5" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft size={16} />
            </button>
            <button className="btn-ghost px-3 py-1.5" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
