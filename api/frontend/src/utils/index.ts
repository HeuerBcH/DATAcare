import { type ClassValue, clsx } from 'clsx';

/** Combina classes CSS condicionalmente (wrapper do clsx). */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/** Formata uma data ISO para pt-BR. */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

/** Mapeia nível de risco para label em português. */
export const riskLevelLabel: Record<string, string> = {
  low: 'Baixo',
  medium: 'Médio',
  high: 'Alto',
  critical: 'Crítico',
};

/** Mapeia nível de risco para cor Tailwind. */
export const riskLevelColor: Record<string, string> = {
  low: 'text-green-600',
  medium: 'text-yellow-600',
  high: 'text-orange-600',
  critical: 'text-red-600',
};
