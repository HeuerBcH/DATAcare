import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, loginRequest, logoutRequest, tokens } from '../lib/api';
import type { User } from '../lib/types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>(null!);

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (tokens.access || tokens.refresh) {
        try {
          const me = await api.get('/auth/me/');
          setUser(me.data);
        } catch {
          tokens.clear();
        }
      }
      setLoading(false);
    })();
  }, []);

  async function login(username: string, password: string) {
    const data = await loginRequest(username, password);
    tokens.set(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }

  async function logout() {
    await logoutRequest();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
