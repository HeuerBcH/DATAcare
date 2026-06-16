import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { CheckCircle2, Loader2, RotateCcw, Wind } from 'lucide-react';
import { api } from '../lib/api';
import type { Comorbidity, Symptom, Visit } from '../lib/types';
import { RiskBadge } from '../components/RiskBadge';

const DRAFT_KEY = 'datacare_triage_draft';
const SEVERITY_LABELS = ['Muito leve', 'Leve', 'Moderado', 'Grave', 'Muito grave'];
const EMPTY = {
  full_name: '',
  birth_date: '',
  gender: '',
  phone: '',
  address: '',
  cpf: '',
  medications: '',
  notes: '',
};

interface SymptomState {
  severity: number;
  duration_days: number;
}

export default function TriageForm() {
  const [symptomsCatalog, setSymptomsCatalog] = useState<Symptom[]>([]);
  const [comorbiditiesCatalog, setComorbiditiesCatalog] = useState<Comorbidity[]>([]);
  const [form, setForm] = useState({ ...EMPTY });
  const [symptoms, setSymptoms] = useState<Record<string, SymptomState>>({});
  const [comorbidities, setComorbidities] = useState<string[]>([]);
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Visit | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Symptom[]>('/triage/symptoms/').then((r) => setSymptomsCatalog(r.data));
    api.get<Comorbidity[]>('/triage/comorbidities/').then((r) => setComorbiditiesCatalog(r.data));
    const raw = localStorage.getItem(DRAFT_KEY);
    if (raw) {
      try {
        const d = JSON.parse(raw);
        setForm({ ...EMPTY, ...d.form });
        setSymptoms(d.symptoms || {});
        setComorbidities(d.comorbidities || []);
      } catch {
        /* ignore */
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ form, symptoms, comorbidities }));
  }, [form, symptoms, comorbidities]);

  const errors = useMemo(() => {
    const e: Record<string, string> = {};
    if (form.full_name.trim().length < 3) e.full_name = 'Informe o nome completo (mín. 3 letras).';
    if (!form.birth_date) e.birth_date = 'Informe a data de nascimento.';
    else if (form.birth_date > new Date().toISOString().slice(0, 10))
      e.birth_date = 'A data não pode ser futura.';
    if (!form.gender) e.gender = 'Selecione o gênero.';
    return e;
  }, [form]);
  const valid = Object.keys(errors).length === 0;

  function set(key: keyof typeof EMPTY, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }
  function toggleSymptom(name: string) {
    setSymptoms((s) => {
      const next = { ...s };
      if (next[name]) delete next[name];
      else next[name] = { severity: 3, duration_days: 2 };
      return next;
    });
  }
  function updateSymptom(name: string, patch: Partial<SymptomState>) {
    setSymptoms((s) => ({ ...s, [name]: { ...s[name], ...patch } }));
  }
  function toggleComorbidity(name: string) {
    setComorbidities((c) => (c.includes(name) ? c.filter((x) => x !== name) : [...c, name]));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!valid) return;
    setSubmitting(true);
    setError('');

    const patient: Record<string, string> = {
      full_name: form.full_name.trim(),
      birth_date: form.birth_date,
      gender: form.gender,
    };
    if (form.phone) patient.phone = form.phone;
    if (form.address) patient.address = form.address;
    if (form.cpf.replace(/\D/g, '')) patient.cpf = form.cpf.replace(/\D/g, '');

    try {
      const r = await api.post<Visit>('/triage/visits/', {
        patient,
        medications: form.medications,
        notes: form.notes,
        symptoms: Object.entries(symptoms).map(([name, s]) => ({
          name,
          severity: s.severity,
          duration_days: s.duration_days,
        })),
        comorbidities,
      });
      setResult(r.data);
      localStorage.removeItem(DRAFT_KEY);
    } catch {
      setError('Erro ao registrar. Confira os dados e tente novamente.');
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    setForm({ ...EMPTY });
    setSymptoms({});
    setComorbidities([]);
    setResult(null);
    setError('');
    setTouched(false);
    localStorage.removeItem(DRAFT_KEY);
  }

  if (result) return <ResultPanel visit={result} onNew={reset} />;

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-5 stagger">
      <header>
        <p className="eyebrow">Visita domiciliar</p>
        <h1 className="mt-1 font-display text-3xl font-600 text-ink">Nova triagem</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Coleta padronizada dos dados do paciente. O risco é calculado automaticamente ao salvar.
        </p>
      </header>

      <Section n={1} title="Dados pessoais">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Nome completo" error={touched ? errors.full_name : ''} className="sm:col-span-2">
            <input
              className="input"
              value={form.full_name}
              onChange={(e) => set('full_name', e.target.value)}
              placeholder="Maria da Silva"
            />
          </Field>
          <Field label="Data de nascimento" error={touched ? errors.birth_date : ''}>
            <input
              type="date"
              className="input"
              value={form.birth_date}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => set('birth_date', e.target.value)}
            />
          </Field>
          <Field label="Gênero" error={touched ? errors.gender : ''}>
            <select className="input" value={form.gender} onChange={(e) => set('gender', e.target.value)}>
              <option value="">Selecione…</option>
              <option value="F">Feminino</option>
              <option value="M">Masculino</option>
              <option value="O">Outro</option>
            </select>
          </Field>
          <Field label="Telefone">
            <input
              className="input"
              value={form.phone}
              onChange={(e) => set('phone', e.target.value)}
              placeholder="(81) 99999-0000"
            />
          </Field>
          <Field label="CPF (opcional)">
            <input
              className="input"
              value={form.cpf}
              onChange={(e) => set('cpf', e.target.value)}
              placeholder="000.000.000-00"
            />
          </Field>
          <Field label="Endereço" className="sm:col-span-2">
            <input
              className="input"
              value={form.address}
              onChange={(e) => set('address', e.target.value)}
              placeholder="Rua, número, bairro"
            />
          </Field>
        </div>
      </Section>

      <Section n={2} title="Sintomas" desc="Selecione os sintomas e ajuste severidade e duração.">
        <div className="flex flex-wrap gap-2">
          {symptomsCatalog.map((s) => {
            const active = !!symptoms[s.name];
            return (
              <button
                type="button"
                key={s.id}
                onClick={() => toggleSymptom(s.name)}
                className={`badge transition ${active ? 'risk-medio ring-amber-500/40' : 'risk-none hover:bg-surface-sunken'}`}
              >
                {s.is_respiratory && <Wind size={12} className="opacity-70" />}
                {s.name}
              </button>
            );
          })}
        </div>

        {Object.keys(symptoms).length > 0 && (
          <div className="mt-4 space-y-3">
            {Object.entries(symptoms).map(([name, st]) => (
              <div key={name} className="rounded-xl border border-line bg-surface-sunken/40 p-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-ink">{name}</span>
                  <button
                    type="button"
                    onClick={() => toggleSymptom(name)}
                    className="text-xs text-ink-faint hover:text-red-600"
                  >
                    remover
                  </button>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_8rem]">
                  <div>
                    <span className="label mb-1.5">Severidade · {SEVERITY_LABELS[st.severity - 1]}</span>
                    <div className="flex gap-1.5">
                      {[1, 2, 3, 4, 5].map((v) => (
                        <button
                          type="button"
                          key={v}
                          onClick={() => updateSymptom(name, { severity: v })}
                          className={`h-9 flex-1 rounded-lg text-sm font-semibold transition ${
                            v <= st.severity
                              ? 'bg-amber-500 text-white'
                              : 'bg-white text-ink-faint ring-1 ring-inset ring-line hover:bg-surface-sunken'
                          }`}
                        >
                          {v}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="label mb-1.5">Duração (dias)</span>
                    <input
                      type="number"
                      min={0}
                      className="input"
                      value={st.duration_days}
                      onChange={(e) =>
                        updateSymptom(name, { duration_days: Math.max(0, Number(e.target.value)) })
                      }
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section n={3} title="Comorbidades" desc="Condições crônicas conhecidas.">
        <div className="flex flex-wrap gap-2">
          {comorbiditiesCatalog.map((c) => {
            const active = comorbidities.includes(c.name);
            return (
              <button
                type="button"
                key={c.id}
                onClick={() => toggleComorbidity(c.name)}
                className={`badge transition ${
                  active
                    ? c.is_critical
                      ? 'risk-alto ring-red-500/40'
                      : 'risk-baixo ring-emerald-500/40'
                    : 'risk-none hover:bg-surface-sunken'
                }`}
              >
                {c.name}
              </button>
            );
          })}
        </div>
      </Section>

      <Section n={4} title="Medicações e observações">
        <div className="space-y-4">
          <Field label="Medicações em uso">
            <textarea
              className="input min-h-[72px] resize-y"
              value={form.medications}
              onChange={(e) => set('medications', e.target.value)}
              placeholder="Ex.: Losartana 50mg, Metformina 850mg…"
            />
          </Field>
          <Field label="Observações gerais">
            <textarea
              className="input min-h-[72px] resize-y"
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              placeholder="Contexto relevante da visita…"
            />
          </Field>
        </div>
      </Section>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-inset ring-red-600/15">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between gap-3 pb-4">
        <p className="text-xs text-ink-faint">Rascunho salvo automaticamente.</p>
        <button type="submit" className="btn-primary px-6" disabled={submitting || (touched && !valid)}>
          {submitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
          {submitting ? 'Avaliando risco…' : 'Registrar e avaliar'}
        </button>
      </div>
    </form>
  );
}

function Section({
  n,
  title,
  desc,
  children,
}: {
  n: number;
  title: string;
  desc?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card p-5 sm:p-6">
      <div className="mb-4 flex items-baseline gap-3">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand-100 font-mono text-sm font-600 text-brand-800">
          {n}
        </span>
        <div>
          <h3 className="font-display text-lg font-600 text-ink">{title}</h3>
          {desc && <p className="text-xs text-ink-faint">{desc}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function Field({
  label,
  error,
  className = '',
  children,
}: {
  label: string;
  error?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={className}>
      <label className="label mb-1.5">{label}</label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

function ResultPanel({ visit, onNew }: { visit: Visit; onNew: () => void }) {
  const recommendation =
    {
      alto: 'Risco ALTO — priorize o atendimento e avalie encaminhamento.',
      medio: 'Risco MÉDIO — acompanhe de perto e reavalie em curto prazo.',
      baixo: 'Risco BAIXO — mantenha o acompanhamento de rotina.',
    }[visit.risk_level as 'alto' | 'medio' | 'baixo'] || 'Triagem registrada.';

  return (
    <div className="mx-auto max-w-xl animate-scale-in">
      <div className="card p-8 text-center">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-100 text-brand-700">
          <CheckCircle2 size={28} />
        </span>
        <h2 className="mt-4 font-display text-2xl font-600 text-ink">Triagem registrada</h2>
        <p className="mt-1 text-sm text-ink-soft">
          {visit.patient_name} · {visit.patient_age} anos
        </p>

        <div className="mt-6 flex flex-col items-center gap-2.5">
          <p className="label">Risco previsto pelo modelo</p>
          <div className="scale-125">
            <RiskBadge level={visit.risk_level} score={visit.risk_score} showScore />
          </div>
        </div>

        <p className="mt-6 rounded-xl bg-surface-sunken px-4 py-3 text-sm text-ink-soft">{recommendation}</p>

        <button onClick={onNew} className="btn-primary mt-6 w-full">
          <RotateCcw size={16} />
          Registrar nova triagem
        </button>
      </div>
    </div>
  );
}
