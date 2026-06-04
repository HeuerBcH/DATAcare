import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

export function HomePage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-teal-700">DATAcare</p>
        <h1 className="mt-2 text-3xl font-semibold">
          Olá, {user?.first_name || user?.username}
        </h1>
        <p className="mt-2 text-slate-600">
          Painel principal — saúde digital e predição de risco para APS.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          to="/patients"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-200"
        >
          <h2 className="font-semibold text-teal-800">Pacientes</h2>
          <p className="mt-1 text-sm text-slate-600">Listar e acompanhar pacientes.</p>
        </Link>
        <Link
          to="/predictions"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-200"
        >
          <h2 className="font-semibold text-teal-800">Predições</h2>
          <p className="mt-1 text-sm text-slate-600">Histórico e novas predições de risco.</p>
        </Link>
        <Link
          to="/profile"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-200"
        >
          <h2 className="font-semibold text-teal-800">Perfil</h2>
          <p className="mt-1 text-sm text-slate-600">Dados da sua conta.</p>
        </Link>
      </div>
    </div>
  );
}
