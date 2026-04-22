import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'

export default function AuthCallback() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  useEffect(() => {
    let cancelled = false

    async function completeLogin() {
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
      if (!cancelled) {
        navigate('/', { replace: true })
      }
    }

    completeLogin()

    return () => {
      cancelled = true
    }
  }, [navigate, queryClient])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-sm">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary/30 border-t-primary"></div>
        <span className="text-sm font-medium text-slate-700">Finalizing your sign-in...</span>
      </div>
    </div>
  )
}
