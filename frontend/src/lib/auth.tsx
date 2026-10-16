import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, configureAuth, request } from './api'
import { cognito, decodeJwt, type CognitoConfig } from './cognito'

// Session tokens live in sessionStorage (cleared when the tab closes) and in
// memory. They are never written to localStorage or exposed in URLs.
const SESSION_KEY = 'fi.session'

interface PublicConfig {
  auth_mode: 'local' | 'cognito'
  cognito: CognitoConfig | null
  demo_data_enabled: boolean
  receipt_upload_mode: 'direct' | 'presigned'
}

interface Session {
  accessToken: string
  refreshToken?: string
  expiresAt: number
  user: { id: string; email: string; name: string }
}

type Status = 'loading' | 'authenticated' | 'anonymous' | 'unavailable'

interface AuthContextValue {
  status: Status
  config: PublicConfig | null
  user: Session['user'] | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<'signed_in' | 'confirm_required'>
  confirmSignUp: (email: string, code: string) => Promise<void>
  resendCode: (email: string) => Promise<void>
  logout: (reason?: string) => void
  retry: () => void
  sessionMessage: string | null
}

const AuthContext = createContext<AuthContextValue | null>(null)

function loadSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

function saveSession(session: Session | null) {
  try {
    if (session) sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    else sessionStorage.removeItem(SESSION_KEY)
  } catch {
    /* storage unavailable: session stays in memory only */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [session, setSession] = useState<Session | null>(() => loadSession())
  const [status, setStatus] = useState<Status>('loading')
  const [sessionMessage, setSessionMessage] = useState<string | null>(null)
  const sessionRef = useRef(session)
  const configRef = useRef(config)
  const [attempt, setAttempt] = useState(0)

  const update = useCallback((next: Session | null) => {
    sessionRef.current = next
    saveSession(next)
    setSession(next)
    setStatus(next ? 'authenticated' : 'anonymous')
  }, [])

  const logout = useCallback((reason?: string) => {
    const current = sessionRef.current
    const cfg = configRef.current
    if (current && cfg?.auth_mode === 'cognito' && cfg.cognito) void cognito.signOut(cfg.cognito, current.accessToken)
    setSessionMessage(reason ?? null)
    update(null)
  }, [update])

  // Provide tokens to the API client, refreshing Cognito tokens when needed.
  useEffect(() => {
    configureAuth(
      async () => {
        const current = sessionRef.current
        if (!current) return null
        const cfg = configRef.current
        if (Date.now() > current.expiresAt - 60_000) {
          if (cfg?.auth_mode === 'cognito' && cfg.cognito && current.refreshToken) {
            try {
              const t = await cognito.refresh(cfg.cognito, current.refreshToken)
              const next = { ...current, accessToken: t.accessToken, refreshToken: t.refreshToken, expiresAt: Date.now() + t.expiresIn * 1000 }
              update(next)
              return next.accessToken
            } catch {
              logout('Your session has expired. Please sign in again.')
              return null
            }
          }
          if (Date.now() > current.expiresAt) {
            logout('Your session has expired. Please sign in again.')
            return null
          }
        }
        return current.accessToken
      },
      () => logout('Your session has expired. Please sign in again.'),
    )
  }, [logout, update])

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    request<PublicConfig>('/config', { auth: false })
      .then((cfg) => {
        if (cancelled) return
        configRef.current = cfg
        setConfig(cfg)
        const existing = sessionRef.current
        setStatus(existing && existing.expiresAt > Date.now() - 1 ? 'authenticated' : 'anonymous')
        if (existing && existing.expiresAt <= Date.now() && !existing.refreshToken) update(null)
      })
      .catch(() => !cancelled && setStatus('unavailable'))
    return () => {
      cancelled = true
    }
  }, [attempt, update])

  const login = useCallback(async (email: string, password: string) => {
    const cfg = configRef.current
    setSessionMessage(null)
    if (cfg?.auth_mode === 'cognito' && cfg.cognito) {
      const t = await cognito.signIn(cfg.cognito, email, password)
      const claims = decodeJwt(t.idToken)
      update({ accessToken: t.accessToken, refreshToken: t.refreshToken, expiresAt: Date.now() + t.expiresIn * 1000,
        user: { id: claims.sub, email: claims.email ?? email, name: claims.name ?? email } })
      return
    }
    const res = await request<{ access_token: string; expires_in: number; user: Session['user'] }>('/auth/login', {
      method: 'POST', body: { email, password }, auth: false,
    })
    update({ accessToken: res.access_token, expiresAt: Date.now() + res.expires_in * 1000, user: res.user })
  }, [update])

  const register = useCallback(async (name: string, email: string, password: string) => {
    const cfg = configRef.current
    if (cfg?.auth_mode === 'cognito' && cfg.cognito) {
      await cognito.signUp(cfg.cognito, name, email, password)
      return 'confirm_required' as const
    }
    const res = await request<{ access_token: string; expires_in: number; user: Session['user'] }>('/auth/register', {
      method: 'POST', body: { name, email, password }, auth: false,
    })
    update({ accessToken: res.access_token, expiresAt: Date.now() + res.expires_in * 1000, user: res.user })
    return 'signed_in' as const
  }, [update])

  const confirmSignUp = useCallback(async (email: string, code: string) => {
    const cfg = configRef.current
    if (!cfg?.cognito) return
    await cognito.confirm(cfg.cognito, email, code)
  }, [])

  const resendCode = useCallback(async (email: string) => {
    const cfg = configRef.current
    if (!cfg?.cognito) return
    await cognito.resendCode(cfg.cognito, email)
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    status, config, user: session?.user ?? null, login, register, confirmSignUp, resendCode, logout,
    retry: () => setAttempt((a) => a + 1), sessionMessage,
  }), [status, config, session, login, register, confirmSignUp, resendCode, logout, sessionMessage])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export { api }
