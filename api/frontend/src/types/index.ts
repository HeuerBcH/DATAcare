export type UserRole = 'gestor' | 'acs' | 'profissional_saude' | 'admin';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  phone?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  role_display?: string;
  phone?: string;
  cpf?: string;
  bio?: string;
  created_at?: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface Patient {
  id: number;
  user: User;
  cpf?: string;
  date_of_birth?: string;
  age?: number;
  gender?: string;
  latest_vitals?: VitalSigns | null;
  created_at: string;
}

export interface VitalSigns {
  id: number;
  blood_pressure_systolic: number;
  blood_pressure_diastolic: number;
  heart_rate: number;
  temperature: number;
  weight: number;
  height: number;
  blood_glucose?: number;
  bmi?: number;
  measured_at: string;
}

export interface PredictionModel {
  id: number;
  name: string;
  version: string;
  description: string;
  is_active: boolean;
}

export interface Prediction {
  id: number;
  patient: number;
  patient_name?: string;
  model: number;
  model_name?: string;
  risk_level: RiskLevel;
  risk_level_display?: string;
  probability: number;
  prediction_data: Record<string, unknown>;
  clinical_notes?: string;
  created_at: string;
}

export interface ApiError {
  detail?: string;
  [field: string]: string | string[] | undefined;
}
