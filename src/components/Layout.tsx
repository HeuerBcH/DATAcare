import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  Activity,
  Bell,
  ClipboardCheck,
  LayoutDashboard,
  LogOut,
  Menu,
  Stethoscope,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import type { Role } from '../lib/types';
import { Logo, Wordmark } from './brand';

interface NavItem {
  to: string;
  label: string;
  icon: typeof Activity;
  roles: Role[];
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['gestor', 'admin'] },
  { to: '/triagem', label: 'Nova triagem', icon: ClipboardCheck, roles: ['acs', 'profissional_saude', 'admin'] },
  { to: '/visitas', label: 'Visitas', icon: Stethoscope, roles: ['gestor', 'acs', 'profissional_saude', 'admin'] },
  { to: '/alertas', label: 'Alertas', icon: Bell, roles: ['gestor', 'admin'] },
];

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const items = NAV.filter((i) => user && i.roles.includes(user.role));
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-6">
        <Logo size={34} />
        <Wordmark />
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
          >
            <item.icon size={18} strokeWidth={2} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-line p-3">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-full bg-brand-100 font-display text-sm font-600 text-brand-800">
            {(user?.first_name?.[0] ?? user?.username?.[0] ?? '?').toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-ink">
              {user?.first_name || user?.username}
            </p>
            <p className="truncate text-xs text-ink-faint">{user?.role_display}</p>
          </div>
        </div>
        <button onClick={() => logout()} className="nav-link mt-1 w-full text-ink-faint hover:text-red-600">
          <LogOut size={18} />
          Sair
        </button>
      </div>
    </div>
  );
}

export function Layout() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_1fr]">
      {/* Sidebar desktop */}
      <aside className="sticky top-0 hidden h-screen border-r border-line bg-surface-raised/70 backdrop-blur lg:block">
        <NavContent />
      </aside>

      {/* Topbar mobile */}
      <header className="flex items-center justify-between border-b border-line bg-surface-raised/80 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center gap-2">
          <Logo size={30} />
          <Wordmark className="text-lg" />
        </div>
        <button onClick={() => setOpen(true)} className="btn-ghost px-2.5 py-2">
          <Menu size={20} />
        </button>
      </header>

      {/* Drawer mobile */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72 animate-scale-in bg-surface-raised shadow-float">
            <button onClick={() => setOpen(false)} className="absolute right-3 top-5 text-ink-faint">
              <X size={20} />
            </button>
            <NavContent onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}

      <main className="min-w-0 px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
        <Outlet />
      </main>
    </div>
  );
}
