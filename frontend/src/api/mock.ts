/**
 * Mock API responses for development/demo when the backend is offline.
 * Toggle with: VITE_USE_MOCK=true in .env
 */

export const mockDashboardStats = {
  total_visits_week: 124,
  high_risk_count: 18,
  active_alerts: 7,
  disease_distribution: {
    dengue: 61,
    chikungunya: 31,
    zika: 14,
    influenza: 18,
  },
}

export const mockTrendData = Array.from({ length: 30 }, (_, i) => {
  const date = new Date()
  date.setDate(date.getDate() - (29 - i))
  return {
    date: date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
    dengue: Math.round(10 + Math.random() * 15 + (i > 20 ? 8 : 0)),
    chikungunya: Math.round(4 + Math.random() * 8),
    zika: Math.round(1 + Math.random() * 5),
    influenza: Math.round(3 + Math.random() * 6),
  }
})

export const mockAlerts = [
  {
    id: 1,
    patient_name: 'Maria S.',
    risk_level: 'alto',
    disease: 'dengue',
    bairro: 'Ibura',
    created_at: '2026-06-09T10:23:00',
  },
  {
    id: 2,
    patient_name: 'João P.',
    risk_level: 'alto',
    disease: 'dengue',
    bairro: 'Afogados',
    created_at: '2026-06-09T09:11:00',
  },
  {
    id: 3,
    patient_name: 'Ana L.',
    risk_level: 'medio',
    disease: 'chikungunya',
    bairro: 'Casa Amarela',
    created_at: '2026-06-09T08:45:00',
  },
  {
    id: 4,
    patient_name: 'Carlos M.',
    risk_level: 'alto',
    disease: 'influenza',
    bairro: 'Boa Viagem',
    created_at: '2026-06-08T18:30:00',
  },
]

export const mockRecentPatients = [
  { id: 1, name: 'Maria S.', age: 67, disease: 'dengue', risk: 'alto', bairro: 'Ibura', acs: 'Rosa A.' },
  { id: 2, name: 'João P.', age: 54, disease: 'dengue', risk: 'alto', bairro: 'Afogados', acs: 'Marcos T.' },
  { id: 3, name: 'Ana L.', age: 38, disease: 'chikungunya', risk: 'medio', bairro: 'Casa Amarela', acs: 'Rosa A.' },
  { id: 4, name: 'Carlos M.', age: 71, disease: 'influenza', risk: 'alto', bairro: 'Boa Viagem', acs: 'Lúcia F.' },
  { id: 5, name: 'Fernanda C.', age: 25, disease: 'zika', risk: 'baixo', bairro: 'Várzea', acs: 'Pedro S.' },
  { id: 6, name: 'Pedro H.', age: 45, disease: 'dengue', risk: 'medio', bairro: 'Mustardinha', acs: 'Marcos T.' },
]

export const mockUser = {
  id: 1,
  username: 'gestor.ubs',
  email: 'gestor@ubs-ibura.recife.pe.gov.br',
  role: 'gestor' as const,
  first_name: 'Gestor',
  last_name: 'UBS Ibura',
}
