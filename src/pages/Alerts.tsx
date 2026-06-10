import { useEffect, useState } from 'react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { AlertTriangle, BellOff, Check, ShieldAlert } from 'lucide-react';
import { api } from '../lib/api';
import type { Alert, Paginated } from '../lib/types';

const SEVERITY: Record<string, { ring: string; icon: typeof ShieldAlert; chip: string }> = {
  critical: { ring: 'border-l-red-500', icon: ShieldAlert, chip: 'risk-alto' },
  warning: { ring: 'border-l-amber-500', icon: AlertTriangle, chip: 'risk-medio' },
  info: { ring: 'border-l-brand-500', icon: ShieldAlert, chip: 'risk-none' },
};

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showResolved, setShowResolved] = useState(false);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api
      .get<Paginated<Alert>>('/triage/alerts/', {
        params: { is_resolved: showResolved, ordering: '-created_at' },
      })
      .then((r) => setAlerts(r.data.results))
      .finally(() => setLoading(false));
  }

  useEffect(load, [showResolved]);

  async function resolve(id: number) {
    await api.post(`/triage/alerts/${id}/resolve/`);
    setAlerts((a) => a.filter((x) => x.id !== id));
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6 flex items-end justify-between">
        <div>
          <p className="eyebrow">Monitoramento</p>
          <h1 className="mt-1 font-display text-3xl font-600 text-ink">Alertas inteligentes</h1>
          <p className="mt-1 text-sm text-ink-soft">Situações detectadas automaticamente nas triagens.</p>
        </div>
        <button
          onClick={() => setShowResolved((v) => !v)}
          className="btn-ghost whitespace-nowrap px-3 py-2 text-xs"
        >
          {showResolved ? 'Ver ativos' : 'Ver resolvidos'}
        </button>
      </header>

      {loading && <p className="card p-8 text-center text-sm text-ink-faint">Carregando…</p>}

      {!loading && alerts.length === 0 && (
        <div className="card flex flex-col items-center gap-2 p-12 text-center">
          <BellOff className="text-ink-faint" size={28} />
          <p className="text-sm text-ink-soft">
            {showResolved ? 'Nenhum alerta resolvido.' : 'Nenhum alerta ativo. Tudo sob controle.'}
          </p>
        </div>
      )}

      <div className="space-y-3">
        {alerts.map((a) => {
          const s = SEVERITY[a.severity] ?? SEVERITY.info;
          return (
            <div key={a.id} className={`card border-l-4 ${s.ring} p-4`}>
              <div className="flex items-start gap-3">
                <span className="mt-0.5 text-ink-soft">
                  <s.icon size={18} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`badge ${s.chip}`}>{a.severity_display}</span>
                    <span className="text-xs text-ink-faint">{a.type_display}</span>
                  </div>
                  <p className="mt-1.5 font-semibold text-ink">{a.title}</p>
                  <p className="mt-0.5 text-sm text-ink-soft">{a.message}</p>
                  <p className="mt-1.5 text-xs text-ink-faint">
                    {formatDistanceToNow(parseISO(a.created_at), { addSuffix: true, locale: ptBR })}
                  </p>
                </div>
                {!a.is_resolved && (
                  <button onClick={() => resolve(a.id)} className="btn-soft shrink-0 px-3 py-1.5 text-xs">
                    <Check size={14} />
                    Resolver
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
