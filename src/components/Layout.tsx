import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, ClipboardList, Users, Activity,
  AlertTriangle, LogOut, Menu, X
} from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['gestor', 'admin'] },
  { to: '/triagem', label: 'Nova Triagem', icon: ClipboardList, roles: ['acs', 'profissional_saude', 'admin'] },
  { to: '/pacientes', label: 'Pacientes', icon: Users, roles: ['gestor', 'profissional_saude', 'admin'] },
  { to: '/predicoes', label: 'Predições', icon: Activity, roles: ['gestor', 'profissional_saude', 'admin'] },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)

  const visibleItems = navItems.filter(
    item => !item.roles || item.roles.includes(user?.role ?? '')
  )

  const roleLabel: Record<string, string> = {
    gestor: 'Gestor/Coordenador',
    acs: 'Agente Comunitário',
    profissional_saude: 'Profissional de Saúde',
    admin: 'Administrador',
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-white shadow-lg transition-transform duration-200',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 border-b border-slate-100 px-6 py-5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-sm font-bold text-white">
            DC
          </span>
          <span className="text-lg font-semibold text-slate-800">DATAcare</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {visibleItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                clsx(
                  'mb-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-teal-50 text-teal-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User block */}
        <div className="border-t border-slate-100 px-4 py-4">
          <div className="mb-3">
            <p className="text-sm font-medium text-slate-800">
              {user?.first_name} {user?.last_name}
            </p>
            <p className="text-xs text-slate-500">{roleLabel[user?.role ?? ''] ?? user?.role}</p>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <LogOut size={16} />
            Sair
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/30 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden lg:ml-64">
        {/* Top bar */}
        <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-6 py-4">
          <button
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
            onClick={() => setOpen(v => !v)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <AlertTriangle size={14} className="text-amber-500" />
            <span>Dados epidemiológicos — Recife, PE</span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
