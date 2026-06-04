import { FormEvent, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import type { UserRole } from '@/types';

export function RegisterPage() {
  const { register, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    role: 'profissional_saude' as UserRole,
    phone: '',
  });

  if (!loading && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (form.password !== form.password_confirm) {
      setError('As senhas não coincidem.');
      return;
    }
    setSubmitting(true);
    try {
      await register(form);
      navigate('/', { replace: true });
    } catch {
      setError('Não foi possível criar a conta. Verifique os dados.');
    } finally {
      setSubmitting(false);
    }
  };

  const field = (name: keyof typeof form, label: string, type = 'text') => (
    <div key={name}>
      <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      <input
        type={type}
        className="w-full rounded-md border border-slate-300 px-3 py-2"
        value={form[name]}
        onChange={(e) => setForm({ ...form, [name]: e.target.value })}
        required={name !== 'phone'}
      />
    </div>
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg space-y-4 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <h1 className="text-2xl font-semibold text-teal-800">Criar conta</h1>
        {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          {field('first_name', 'Nome')}
          {field('last_name', 'Sobrenome')}
        </div>
        {field('username', 'Usuário')}
        {field('email', 'E-mail', 'email')}
        {field('phone', 'Telefone')}
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Papel</label>
          <select
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
          >
            <option value="gestor">Gestor/Coordenador UBS</option>
            <option value="acs">Agente Comunitário de Saúde</option>
            <option value="profissional_saude">Profissional de Saúde</option>
            <option value="admin">Administrador</option>
          </select>
        </div>
        {field('password', 'Senha', 'password')}
        {field('password_confirm', 'Confirmar senha', 'password')}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-teal-700 px-4 py-2 font-medium text-white hover:bg-teal-800 disabled:opacity-60"
        >
          {submitting ? 'Criando...' : 'Registrar'}
        </button>
        <p className="text-center text-sm text-slate-600">
          Já tem conta?{' '}
          <Link to="/login" className="font-medium text-teal-700 hover:underline">
            Entrar
          </Link>
        </p>
      </form>
    </div>
  );
}
