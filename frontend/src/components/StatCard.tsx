import type { ReactNode } from 'react';

type Accent = 'brand' | 'alto' | 'medio' | 'baixo';

const ACCENTS: Record<Accent, string> = {
  brand: 'text-brand-700 bg-brand-100',
  alto: 'text-red-700 bg-red-50',
  medio: 'text-amber-700 bg-amber-50',
  baixo: 'text-emerald-700 bg-emerald-50',
};

export function StatCard({
  label,
  value,
  hint,
  icon,
  accent = 'brand',
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  accent?: Accent;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <p className="label">{label}</p>
        {icon && (
          <span className={`grid h-9 w-9 place-items-center rounded-xl ${ACCENTS[accent]}`}>
            {icon}
          </span>
        )}
      </div>
      <p className="mt-3 font-display text-3xl font-600 leading-none text-ink">{value}</p>
      {hint && <p className="mt-2 text-xs text-ink-faint">{hint}</p>}
    </div>
  );
}
