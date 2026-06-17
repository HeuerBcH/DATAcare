import type { RiskLevel } from '../lib/types';

const MAP: Record<string, { cls: string; label: string }> = {
  baixo: { cls: 'risk-baixo', label: 'Baixo' },
  medio: { cls: 'risk-medio', label: 'Médio' },
  alto: { cls: 'risk-alto', label: 'Alto' },
};

export function RiskBadge({
  level,
  score,
  showScore = false,
}: {
  level: RiskLevel;
  score?: number | null;
  showScore?: boolean;
}) {
  const m = MAP[level];
  if (!m) {
    return <span className="badge risk-none">sem risco</span>;
  }
  return (
    <span className={`badge ${m.cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {m.label}
      {showScore && score != null && (
        <span className="font-mono text-[0.7rem] opacity-70">{Math.round(score)}</span>
      )}
    </span>
  );
}
