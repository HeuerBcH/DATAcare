export type Role = 'gestor' | 'acs' | 'profissional_saude' | 'admin';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  role_display: string;
  phone?: string;
}

export type RiskLevel = 'baixo' | 'medio' | 'alto' | '';

export interface Symptom {
  id: number;
  name: string;
  is_respiratory: boolean;
}

export interface Comorbidity {
  id: number;
  name: string;
  is_critical: boolean;
}

export interface VisitSymptom {
  symptom: number;
  name: string;
  is_respiratory: boolean;
  severity: number;
  duration_days: number;
}

export interface Visit {
  id: number;
  patient: number;
  patient_name: string;
  patient_age: number;
  acs: number | null;
  acs_name: string | null;
  visit_date: string;
  medications: string;
  notes: string;
  symptoms: VisitSymptom[];
  comorbidities: Comorbidity[];
  risk_level: RiskLevel;
  risk_level_display: string;
  risk_score: number | null;
  model_version: string;
  predicted_at: string | null;
  created_at: string;
}

export interface DashboardData {
  total_patients: number;
  total_visits: number;
  active_alerts: number;
  risk_distribution: Record<'baixo' | 'medio' | 'alto', number>;
  alerts_by_severity: Record<string, number>;
  top_symptoms: { name: string; count: number }[];
  visits_over_time: { date: string; count: number }[];
  critical_patients: {
    visit_id: number;
    patient_name: string;
    age: number;
    risk_score: number | null;
    visit_date: string;
  }[];
}

export interface Alert {
  id: number;
  alert_type: string;
  type_display: string;
  severity: 'info' | 'warning' | 'critical';
  severity_display: string;
  title: string;
  message: string;
  patient: number | null;
  patient_name: string | null;
  visit: number | null;
  is_resolved: boolean;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
