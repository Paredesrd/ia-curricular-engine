import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiRequest } from '../api/client'
import { UserWithTenant, TokenResponse, RegisterData, LoginData } from '../types'

interface AuthContextType {
  token: string | null
  user: UserWithTenant | null
  loading: boolean
  login: (data: LoginData) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('access_token')
  )
  const [user, setUser] = useState<UserWithTenant | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      apiRequest<UserWithTenant>('GET', '/auth/me')
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('access_token')
          setToken(null)
          setUser(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  const login = async (data: LoginData) => {
    const resp = await apiRequest<TokenResponse>('POST', '/auth/login', data, {
      isForm: true,
    })
    localStorage.setItem('access_token', resp.access_token)
    setToken(resp.access_token)
    const me = await apiRequest<UserWithTenant>('GET', '/auth/me')
    setUser(me)
  }

  const register = async (data: RegisterData) => {
    await apiRequest<UserWithTenant>('POST', '/auth/register', data)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth debe usarse dentro de AuthProvider')
  }
  return ctx
}