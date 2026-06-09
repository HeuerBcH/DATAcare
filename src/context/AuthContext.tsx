import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import Cookies from 'js-cookie'
import api from '../api/client'
import { mockUser } from '../api/mock'

export interface User {
  id: number
  username: string
  email: string
  role: 'gestor' | 'acs' | 'profissional_saude' | 'admin'
  first_name: string
  last_name: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (USE_MOCK) {
      setUser(mockUser)
      setLoading(false)
      return
    }
    const token = Cookies.get('access_token')
    if (token) {
      api.get<User>('/api/v1/auth/me/')
        .then(res => setUser(res.data))
        .catch(() => {
          Cookies.remove('access_token')
          Cookies.remove('refresh_token')
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  async function login(username: string, password: string) {
    const { data } = await api.post('/api/v1/auth/login/', { username, password })
    Cookies.set('access_token', data.access, { secure: true, sameSite: 'strict' })
    Cookies.set('refresh_token', data.refresh, { secure: true, sameSite: 'strict' })
    setUser(data.user)
  }

  async function logout() {
    try {
      const refresh = Cookies.get('refresh_token')
      if (refresh) await api.post('/api/v1/auth/logout/', { refresh })
    } finally {
      Cookies.remove('access_token')
      Cookies.remove('refresh_token')
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
