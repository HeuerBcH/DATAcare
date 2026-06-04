import { useAuth } from '@/contexts/AuthContext';

export function ProfilePage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">Meu perfil</h1>
      <dl className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        <div className="grid grid-cols-3 gap-4 px-4 py-3">
          <dt className="text-sm text-slate-500">Usuário</dt>
          <dd className="col-span-2 text-sm font-medium">{user.username}</dd>
        </div>
        <div className="grid grid-cols-3 gap-4 px-4 py-3">
          <dt className="text-sm text-slate-500">Nome</dt>
          <dd className="col-span-2 text-sm font-medium">
            {user.first_name} {user.last_name}
          </dd>
        </div>
        <div className="grid grid-cols-3 gap-4 px-4 py-3">
          <dt className="text-sm text-slate-500">E-mail</dt>
          <dd className="col-span-2 text-sm font-medium">{user.email}</dd>
        </div>
        <div className="grid grid-cols-3 gap-4 px-4 py-3">
          <dt className="text-sm text-slate-500">Papel</dt>
          <dd className="col-span-2 text-sm font-medium">{user.role_display ?? user.role}</dd>
        </div>
        {user.phone && (
          <div className="grid grid-cols-3 gap-4 px-4 py-3">
            <dt className="text-sm text-slate-500">Telefone</dt>
            <dd className="col-span-2 text-sm font-medium">{user.phone}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
