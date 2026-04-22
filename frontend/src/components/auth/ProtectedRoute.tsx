import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'

export default function ProtectedRoute({ requireAdmin = false }: { requireAdmin?: boolean }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex items-center gap-3 text-slate-600">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary/30 border-t-primary"></div>
          <span className="text-sm font-medium">Loading your workspace...</span>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (requireAdmin && user.role !== 'admin') {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
