import { useState, useCallback } from 'react';
import { api } from '@/services';
import type { AuthTokens, LoginCredentials, User } from '@/types';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setLoading(true);
    setError(null);
    try {
      const { data: tokens } = await api.post<AuthTokens>('/auth/login/', credentials);
      localStorage.setItem('access_token', tokens.access);
      localStorage.setItem('refresh_token', tokens.refresh);

      const { data: profile } = await api.get<User>('/auth/me/');
      setUser(profile);
      return profile;
    } catch (err) {
      setError('Credenciais inválidas. Verifique usuário e senha.');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  }, []);

  return { user, loading, error, login, logout };
}
