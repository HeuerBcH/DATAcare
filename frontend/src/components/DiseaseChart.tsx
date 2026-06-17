import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'

interface Props {
  data: Record<string, number>
}

const COLORS: Record<string, string> = {
  dengue: '#0d9488',
  chikungunya: '#f59e0b',
  zika: '#6366f1',
  influenza: '#64748b',
}

const LABELS: Record<string, string> = {
  dengue: 'Dengue',
  chikungunya: 'Chikungunya',
  zika: 'Zika',
  influenza: 'Influenza',
}

export default function DiseaseChart({ data }: Props) {
  const chartData = Object.entries(data).map(([key, value]) => ({
    name: LABELS[key] ?? key,
    casos: value,
    color: COLORS[key] ?? '#94a3b8',
  }))

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-slate-700">
        Distribuição por Doença — Semana Epidemiológica
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
            formatter={(v: number) => [`${v} casos`, 'Notificações']}
          />
          <Bar dataKey="casos" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
