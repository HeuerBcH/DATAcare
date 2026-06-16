import axios from 'axios';
import Cookies from 'js-cookie';

const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
export const API_ROOT = `${BASE}/api/v1`;

const ACCESS = 'datacare_access';
const REFRESH = 'datacare_refresh';

export const tokens = {
  get access() {
    return Cookies.get(ACCESS);
  },
  get refresh() {
    return Cookies.get(REFRESH);
  },
  set(access: string, refresh?: string) {
    Cookies.set(ACCESS, access, { sameSite: 'Lax', expires: 1 });
    if (refresh) Cookies.set(REFRESH, refresh, { sameSite: 'Lax', expires: 7 });
  },
  clear() {
    Cookies.remove(ACCESS);
    Cookies.remove(REFRESH);
  },
};

export const api = axios.create({ baseURL: API_ROOT });

api.interceptors.request.use((config) => {
  const token = tokens.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccess(): Promise<string | null> {
  const refresh = tokens.refresh;
  if (!refresh) return null;
  try {
    const res = await axios.post(`${API_ROOT}/auth/refresh/`, { refresh });
    tokens.set(res.data.access);
    return res.data.access as string;
  } catch {
    tokens.clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const config = error.config || {};
    if (error.response?.status === 401 && !config.__retried) {
      config.__retried = true;
      refreshing = refreshing ?? refreshAccess();
      const next = await refreshing;
      refreshing = null;
      if (next) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${next}`;
        return api(config);
      }
    }
    return Promise.reject(error);
  }
);

export async function loginRequest(username: string, password: string) {
  const res = await axios.post(`${API_ROOT}/auth/login/`, { username, password });
  return res.data as { access: string; refresh: string; user: import('./types').User };
}

export async function logoutRequest() {
  const refresh = tokens.refresh;
  try {
    if (refresh) await api.post('/auth/logout/', { refresh });
  } catch {
    /* ignore */
  } finally {
    tokens.clear();
  }
}
