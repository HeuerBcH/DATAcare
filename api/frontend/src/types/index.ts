// ── Auth ──────────────────────────────────────────────────────────────────────

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'doctor' | 'nurse' | 'patient';
  is_active: boolean;
  date_joined: string;
}

// ── Patients ──────────────────────────────────────────────────────────────────

export interface Patient {
  id: number;
  user: number;
  cpf: string;
  birth_date: string;
  gender: 'M' | 'F' | 'O';
  phone: string;
  address: string;
  created_at: string;
  updated_at: string;
}

export interface VitalSigns {
  id: number;
  patient: number;
  blood_pressure_systolic: number;
  blood_pressure_diastolic: number;
  heart_rate: number;
  temperature: number;
  weight: number;
  height: number;
  blood_glucose: number;
  recorded_at: string;
}

// ── Predictions ───────────────────────────────────────────────────────────────

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
  model: number;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  input_data: Record<string, unknown>;
  result: Record<string, unknown>;
  created_at: string;
}

// ── API helpers ───────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail?: string;
  [field: string]: string | string[] | undefined;
}
