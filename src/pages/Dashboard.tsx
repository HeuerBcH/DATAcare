import { useEffect, useState } from 'react';
import { format, parseISO } from 'date-fns';
import { AlertTriangle, Bell, ClipboardList, ShieldAlert, Users } from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../lib/api';
import type { DashboardData } from '../lib/types';
import { StatCard } from '../components/StatCard';

const RISK_COLORS: Record<string, string> = {
  baixo: '#15803d',
  medio: '#d97706',
  alto: '#dc2626',
};
const RISK_LABELS: Record<string, string> = { baixo: 'Baixo', medio: 'Médio', alto: 'Alto' };

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .get('/triage/visits/dashboard/')
      .then((r) => setData(r.data))
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <p className="card p-6 text-sm text-red-700">Não foi possível carregar os indicadores.</p>
    );
  }
  if (!data) return <DashboardSkeleton />;

  const totalRisk = data.risk_distribution.baixo + data.risk_distribution.medio + data.risk_distribution.alto;
  const pctAlto = totalRisk ? Math.round((data.risk_distribution.alto / totalRisk) * 100) : 0;
  const riskPie = (['alto', 'medio', 'baixo'] as const).map((k) => ({
    name: RISK_LABELS[k],
    key: k,
    value: data.risk_distribution[k],
  }));
  const timeSeries = data.visits_over_time.map((d) => ({
    label: format(parseISO(d.date), 'dd/MM'),
    count: d.count,
  }));

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-7">
        <p className="eyebrow">Painel do gestor</p>
        <h1 className="mt-1 font-display text-3xl font-600 text-ink">Visão da unidade</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Leitura rápida do risco e da operação a partir das triagens dos ACS.
        </p>
      </header>

      {/* Insight de storytelling */}
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 sm:items-center">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-amber-100 text-amber-700">
          <ShieldAlert size={20} />
        </span>
        <p className="text-sm text-amber-900">
          <strong className="font-semibold">{data.risk_distribution.alto} triagens em alto risco</strong>{' '}
          ({pctAlto}% do total) e <strong className="font-semibold">{data.active_alerts} alertas ativos</strong>{' '}
          aguardando ação. Priorize os pacientes críticos abaixo.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 stagger lg:grid-cols-4">
        <StatCard label="Pacientes" value={data.total_patients} icon={<Users size={18} />} hint="cadastrados na UBS" />
        <StatCard label="Triagens" value={data.total_visits} icon={<ClipboardList size={18} />} hint="visitas registradas" />
        <StatCard label="Alto risco" value={data.risk_distribution.alto} accent="alto" icon={<AlertTriangle size={18} />} hint={`${pctAlto}% das triagens`} />
        <StatCard label="Alertas ativos" value={data.active_alerts} accent="medio" icon={<Bell size={18} />} hint="não resolvidos" />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-5">
        {/* Distribuição de risco */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="font-display text-lg font-600 text-ink">Distribuição de risco</h3>
          <div className="mt-2 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskPie} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={2} strokeWidth={0}>
                  {riskPie.map((d) => (
                    <Cell key={d.key} fill={RISK_COLORS[d.key]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={TOOLTIP} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex justify-center gap-4">
            {riskPie.map((d) => (
              <div key={d.key} className="flex items-center gap-1.5 text-xs text-ink-soft">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLORS[d.key] }} />
                {d.name} · <span className="font-mono">{d.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Triagens ao longo do tempo */}
        <div className="card p-5 lg:col-span-3">
          <h3 className="font-display text-lg font-600 text-ink">Triagens ao longo do tempo</h3>
          <div className="mt-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeries} margin={{ left: -22, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0f766e" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#0f766e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#eceee8" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#7a9092' }} tickLine={false} axisLine={false} minTickGap={20} />
                <YAxis tick={{ fontSize: 11, fill: '#7a9092' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={TOOLTIP} />
                <Area type="monotone" dataKey="count" stroke="#0f766e" strokeWidth={2.5} fill="url(#grad)" name="Triagens" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-5">
        {/* Top sintomas */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="font-display text-lg font-600 text-ink">Sintomas mais comuns</h3>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.top_symptoms} layout="vertical" margin={{ left: 30, right: 16 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: '#3f5b5e' }} tickLine={false} axisLine={false} width={90} />
                <Tooltip contentStyle={TOOLTIP} cursor={{ fill: '#f3f6f2' }} />
                <Bar dataKey="count" fill="#14a682" radius={[0, 6, 6, 0]} name="Ocorrências" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pacientes críticos */}
        <div className="card overflow-hidden lg:col-span-3">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h3 className="font-display text-lg font-600 text-ink">Pacientes críticos</h3>
            <span className="badge risk-alto">alto risco</span>
          </div>
          <div className="divide-y divide-line">
            {data.critical_patients.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-ink-faint">Nenhum paciente em alto risco. 🎉</p>
            )}
            {data.critical_patients.map((p) => (
              <div key={p.visit_id} className="flex items-center justify-between px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">{p.patient_name}</p>
                  <p className="text-xs text-ink-faint">
                    {p.age} anos · triagem em {format(parseISO(p.visit_date), 'dd/MM/yyyy')}
                  </p>
                </div>
                <div className="flex items-center gap-2 font-mono text-sm font-semibold text-red-700">
                  {p.risk_score != null ? Math.round(p.risk_score) : '—'}
                  <span className="text-[0.65rem] font-normal text-ink-faint">score</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const TOOLTIP = {
  borderRadius: 12,
  border: '1px solid #dde3db',
  boxShadow: '0 10px 30px -16px rgba(20,41,43,0.25)',
  fontSize: 12,
};

function DashboardSkeleton() {
  return (
    <div className="mx-auto max-w-6xl">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-surface-sunken" />
      <div className="mt-7 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-2xl bg-surface-sunken" />
        ))}
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-5">
        <div className="h-72 animate-pulse rounded-2xl bg-surface-sunken lg:col-span-2" />
        <div className="h-72 animate-pulse rounded-2xl bg-surface-sunken lg:col-span-3" />
      </div>
    </div>
  );
}
