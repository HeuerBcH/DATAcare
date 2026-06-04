import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { listPatients } from '@/services/patients';
import type { Patient } from '@/types';

export function PatientsPage() {
  const { user } = useAuth();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const canList =
    user?.role === 'profissional_saude' || user?.role === 'admin';

  useEffect(() => {
    if (!canList) {
      setLoading(false);
      return;
    }
    listPatients()
      .then(setPatients)
      .catch(() => setError('Sem permissão ou erro ao carregar pacientes.'))
      .finally(() => setLoading(false));
  }, [canList]);

  if (loading) {
    return <p className="text-slate-600">Carregando pacientes...</p>;
  }

  if (!canList) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
        <p className="font-medium">Acesso restrito</p>
        <p className="mt-1 text-sm">
          Apenas profissionais de saúde e administradores podem listar pacientes. Use a API ou
          o perfil de paciente vinculado à sua conta para predições.
        </p>
      </div>
    );
  }

  if (error) {
    return <p className="text-red-600">{error}</p>;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Pacientes</h1>
      {patients.length === 0 ? (
        <p className="text-slate-600">Nenhum paciente cadastrado.</p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {patients.map((p) => (
            <li key={p.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="font-medium">
                  {p.user.first_name} {p.user.last_name}
                </p>
                <p className="text-sm text-slate-500">CPF: {p.cpf ?? '—'}</p>
              </div>
              {p.age != null && (
                <span className="text-sm text-slate-500">{p.age} anos</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
