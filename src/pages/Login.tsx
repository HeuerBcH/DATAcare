import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, BellRing, ClipboardCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { homeForRole } from '../components/ProtectedRoute';
import { Logo, Wordmark } from '../components/brand';

const DEMO = [
  { label: 'Gestor', username: 'gestor' },
  { label: 'ACS', username: 'acs1' },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(username.trim(), password);
      navigate(homeForRole(user.role), { replace: true });
    } catch {
      setError('Usuário ou senha inválidos.');
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(u: string) {
    setUsername(u);
    setPassword('datacare123');
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-2">
      {/* Painel de marca */}
      <aside className="relative hidden overflow-hidden bg-brand-900 lg:block">
        <div
          className="absolute inset-0 opacity-90"
          style={{
            backgroundImage:
              'radial-gradient(40rem 40rem at 20% 10%, rgba(56,195,154,0.35), transparent 60%), radial-gradient(35rem 35rem at 90% 90%, rgba(15,118,110,0.6), transparent 55%)',
          }}
        />
        <div className="relative flex h-full flex-col justify-between p-12 text-brand-50">
          <div className="flex items-center gap-3">
            <Logo size={40} />
            <span className="font-display text-2xl font-600 text-white">
              DATA<span className="text-brand-200">care</span>
            </span>
          </div>

          <div className="max-w-md">
            <p className="eyebrow text-brand-200">Atenção Primária à Saúde · SUS</p>
            <h1 className="mt-4 font-display text-4xl font-600 leading-tight text-white">
              Dados que já existem, transformados em decisão de cuidado.
            </h1>
            <p className="mt-5 text-brand-100/90">
              Triagem guiada para o Agente Comunitário, classificação de risco por aprendizado de
              máquina e um painel que conta a história dos dados para o gestor da UBS.
            </p>

            <ul className="mt-8 space-y-3 text-sm text-brand-50">
              <Feature icon={ClipboardCheck} text="Triagem domiciliar padronizada e validada" />
              <Feature icon={Activity} text="Risco BAIXO · MÉDIO · ALTO previsto por ML" />
              <Feature icon={BellRing} text="Alertas inteligentes para casos prioritários" />
            </ul>
          </div>

          <p className="text-xs text-brand-200/70">
            Camada de apoio à decisão — não substitui o julgamento clínico.
          </p>
        </div>
      </aside>

      {/* Formulário */}
      <main className="flex min-h-screen items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <Logo size={36} />
            <Wordmark className="text-2xl" />
          </div>

          <p className="eyebrow">Bem-vindo de volta</p>
          <h2 className="mt-2 font-display text-3xl font-600 text-ink">Entrar na plataforma</h2>
          <p className="mt-2 text-sm text-ink-soft">Acesse com suas credenciais da UBS.</p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <div>
              <label className="label mb-1.5" htmlFor="username">
                Usuário
              </label>
              <input
                id="username"
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="seu.usuario"
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className="label mb-1.5" htmlFor="password">
                Senha
              </label>
              <input
                id="password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
            </div>

            {error && (
              <p className="rounded-xl bg-red-50 px-3.5 py-2.5 text-sm text-red-700 ring-1 ring-inset ring-red-600/15">
                {error}
              </p>
            )}

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Entrando…' : 'Entrar'}
              {!loading && <ArrowRight size={16} />}
            </button>
          </form>

          <div className="mt-8 rounded-2xl border border-dashed border-line bg-surface-raised/60 p-4">
            <p className="label mb-2">Acessos de demonstração</p>
            <div className="flex flex-wrap gap-2">
              {DEMO.map((d) => (
                <button
                  key={d.username}
                  onClick={() => fillDemo(d.username)}
                  className="badge risk-none hover:bg-brand-100 hover:text-brand-800"
                >
                  {d.label}
                  <span className="font-mono opacity-70">{d.username}</span>
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-ink-faint">
              Senha: <span className="font-mono">datacare123</span>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

function Feature({ icon: Icon, text }: { icon: typeof Activity; text: string }) {
  return (
    <li className="flex items-center gap-3">
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-white/10 ring-1 ring-inset ring-white/15">
        <Icon size={16} className="text-brand-200" />
      </span>
      {text}
    </li>
  );
}
