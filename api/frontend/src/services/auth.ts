import api from './api';
import type { AuthResponse, LoginCredentials, RegisterPayload, User } from '@/types';

const AUTH_PREFIX = '/auth';

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>(`${AUTH_PREFIX}/login/`, credentials);
  return data;
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>(`${AUTH_PREFIX}/register/`, payload);
  return data;
}

export async function logout(refresh: string): Promise<void> {
  await api.post(`${AUTH_PREFIX}/logout/`, { refresh });
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>(`${AUTH_PREFIX}/me/`);
  return data;
}

export async function updateProfile(payload: Partial<User>): Promise<User> {
  const { data } = await api.patch<User>(`${AUTH_PREFIX}/me/update/`, payload);
  return data;
}
