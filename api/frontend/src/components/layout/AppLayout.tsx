import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const navLinkClass =
  'rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-teal-50 hover:text-teal-800';

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold text-teal-800">
            DATAcare
          </Link>
          <nav className="flex items-center gap-1">
            <Link to="/" className={navLinkClass}>
              Início
            </Link>
            <Link to="/patients" className={navLinkClass}>
              Pacientes
            </Link>
            <Link to="/predictions" className={navLinkClass}>
              Predições
            </Link>
            <Link to="/profile" className={navLinkClass}>
              Perfil
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500">
              {user?.first_name || user?.username}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            >
              Sair
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
