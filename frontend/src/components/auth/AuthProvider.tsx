import { ReactNode, createContext, useContext } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi, CurrentUser } from '../../api/client'

const AUTH_QUERY_KEY = ['auth', 'me']

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error?: string;
  loginWithGoogle: () => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function fetchCurrentUser() {
  const response = await authApi.me()
  if (response.data) {
    return response.data
  }
  if (response.status === 401) {
    return null
  }
  throw new Error(response.error || 'Unable to load current user.')
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: AUTH_QUERY_KEY,
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: 60_000,
  })

  const user = query.data ?? null

  async function logout() {
    await authApi.logout()
    queryClient.setQueryData(AUTH_QUERY_KEY, null)
  }

  async function refreshUser() {
    await queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY })
  }

  function loginWithGoogle() {
    window.location.href = authApi.googleLoginUrl()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading: query.isLoading,
        isAuthenticated: !!user,
        error: query.error instanceof Error ? query.error.message : undefined,
        loginWithGoogle,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider.')
  }
  return context
}
