import { useEffect } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, LockKeyhole, ShieldCheck, Sparkles } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { useAuth } from '../components/auth/AuthProvider'

const errorMessages: Record<string, string> = {
  oauth_state_mismatch: 'Google sign-in could not be verified. Please try again.',
  google_exchange_failed: 'Google sign-in failed during token exchange. Check the backend OAuth configuration.',
}

export default function Login() {
  const { user, isLoading, loginWithGoogle } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const errorCode = searchParams.get('error') || ''

  useEffect(() => {
    if (!isLoading && user) {
      const from = (location.state as { from?: string } | null)?.from || '/'
      navigate(from, { replace: true })
    }
  }, [isLoading, location.state, navigate, user])

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.12),_transparent_45%),linear-gradient(180deg,_#f8fafc_0%,_#eef2ff_100%)] px-6 py-12">
      <div className="mx-auto grid min-h-[calc(100vh-6rem)] max-w-6xl items-center gap-10 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white/70 px-4 py-2 text-sm font-medium text-indigo-700 shadow-sm backdrop-blur">
            <Sparkles className="h-4 w-4" />
            Google OAuth and RBAC are now part of the app shell
          </div>
          <div className="space-y-4">
            <h1 className="max-w-3xl text-5xl font-semibold tracking-tight text-slate-900">
              Sign in once. Keep your resume, preferences, matches, and tasks private.
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-slate-600">
              This workspace now separates every user&apos;s data and unlocks admin-only controls for source
              management and upcoming interview-experience moderation.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/70 bg-white/70 p-5 shadow-sm backdrop-blur">
              <ShieldCheck className="mb-3 h-5 w-5 text-emerald-600" />
              <h2 className="font-semibold text-slate-900">Private by default</h2>
              <p className="mt-2 text-sm text-slate-600">Resume, career profile, jobs, and tasks are now scoped to your account.</p>
            </div>
            <div className="rounded-2xl border border-white/70 bg-white/70 p-5 shadow-sm backdrop-blur">
              <LockKeyhole className="mb-3 h-5 w-5 text-indigo-600" />
              <h2 className="font-semibold text-slate-900">Secure sessions</h2>
              <p className="mt-2 text-sm text-slate-600">Short-lived access cookies plus refresh sessions keep sign-in persistent and revocable.</p>
            </div>
            <div className="rounded-2xl border border-white/70 bg-white/70 p-5 shadow-sm backdrop-blur">
              <ArrowRight className="mb-3 h-5 w-5 text-amber-600" />
              <h2 className="font-semibold text-slate-900">Admin-ready</h2>
              <p className="mt-2 text-sm text-slate-600">The admin role is already wired for upcoming Greenhouse source management.</p>
            </div>
          </div>
        </div>

        <Card className="border-white/70 bg-white/80 shadow-xl shadow-indigo-100 backdrop-blur">
          <CardHeader className="space-y-3">
            <CardTitle className="text-3xl text-slate-900">Continue with Google</CardTitle>
            <CardDescription className="text-base text-slate-600">
              Use your Google account to access your personalized job-matching workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {errorCode && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {errorMessages[errorCode] || decodeURIComponent(errorCode)}
              </div>
            )}
            <Button className="h-11 w-full gap-2 text-base" onClick={loginWithGoogle}>
              Continue with Google
              <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-sm leading-6 text-slate-500">
              Admin role is granted either from your configured admin email list or later via the admin panel.
            </p>
            <p className="text-xs text-slate-400">
              Need to change the allowed frontend origin or Google callback URL? Update the backend auth env vars first.
            </p>
            <Link to="/" className="inline-flex text-sm font-medium text-indigo-600 hover:text-indigo-500">
              Health-check the existing app shell
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
