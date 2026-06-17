import clsx from 'clsx'

interface Patient {
  id: number
  name: string
  age: number
  disease: string
  risk: string
  bairro: string
  acs: string
}

interface Props {
  patients: Patient[]
}

const riskBadge: Record<string, string> = {
  alto:  'bg-red-100 text-red-700',
  medio: 'bg-amber-100 text-amber-700',
  baixo: 'bg-emerald-100 text-emerald-700',
}

const diseaseLabel: Record<string, string> = {
  dengue: 'Dengue',
  chikungunya: 'Chikungunya',
  zika: 'Zika',
  influenza: 'Influenza',
}

export default function PatientTable({ patients }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <h3 className="text-sm font-semibold text-slate-700">Pacientes Recentes</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-100 bg-slate-50/60">
            <tr>
              {['Paciente', 'Idade', 'Doença', 'Risco', 'Bairro', 'ACS'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {patients.map(p => (
              <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 font-medium text-slate-800">{p.name}</td>
                <td className="px-4 py-3 text-slate-600">{p.age} anos</td>
                <td className="px-4 py-3 text-slate-600">{diseaseLabel[p.disease] ?? p.disease}</td>
                <td className="px-4 py-3">
                  <span className={clsx('rounded-full px-2.5 py-1 text-xs font-medium capitalize', riskBadge[p.risk] ?? 'bg-slate-100 text-slate-600')}>
                    {p.risk}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{p.bairro}</td>
                <td className="px-4 py-3 text-slate-500">{p.acs}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {patients.length === 0 && (
          <p className="py-8 text-center text-sm text-slate-400">Nenhum paciente encontrado</p>
        )}
      </div>
    </div>
  )
}
