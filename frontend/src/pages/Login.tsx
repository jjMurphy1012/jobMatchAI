import { FormEvent, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { LockKeyhole, Mail } from 'lucide-react'
import { useAuth } from '../components/auth/AuthProvider'
import { authApi } from '../api/client'
import { AuthBrand, AuthDivider, AuthField, DesktopAuthPanel, GoogleMark } from '../components/auth/AuthPrimitives'
import { Button } from '../components/ui/button'

const errorMessages: Record<string, string> = {
  oauth_state_mismatch: 'Google sign-in could not be verified. Please try again.',
  google_exchange_failed: 'Google sign-in failed during token exchange. Check the backend OAuth configuration.',
}

function InlineAlert({ tone = 'neutral', message }: { tone?: 'neutral' | 'error'; message: string }) {
  return (
    <div
      className={
        tone === 'error'
          ? 'rounded-[18px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700'
          : 'rounded-[18px] border border-[#d7e2ff] bg-[#eef4ff] px-4 py-3 text-sm text-[#2455d6]'
      }
    >
      {message}
    </div>
  )
}

export default function Login() {
  const { user, isLoading, loginWithGoogle, refreshUser } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const errorCode = searchParams.get('error') || ''
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [notice, setNotice] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!isLoading && user) {
      const from = (location.state as { from?: string } | null)?.from || '/'
      navigate(from, { replace: true })
    }
  }, [isLoading, location.state, navigate, user])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')
    if (!email || !password) {
      setNotice('Enter both email and password to continue.')
      return
    }
    setIsSubmitting(true)
    const response = await authApi.login({ email, password })
    setIsSubmitting(false)

    if (response.error) {
      setNotice(response.error)
      return
    }

    await refreshUser()
    navigate((location.state as { from?: string } | null)?.from || '/', { replace: true })
  }

  return (
    <div className="min-h-screen bg-[#f6f7fc] px-4 py-6 text-[#0f172a] sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-6xl flex-col lg:grid lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,500px)] lg:gap-8">
        <DesktopAuthPanel mode="login" />

        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-[430px]">
            <div className="pb-10 pt-6 lg:hidden">
              <AuthBrand centered />
            </div>

            <div className="rounded-[30px] border border-[#d7dced] bg-white px-6 py-8 shadow-[0_16px_48px_rgba(15,23,42,0.08)] sm:px-8">
              <div className="space-y-3 text-center">
                <h1 className="text-[2.6rem] font-semibold tracking-[-0.06em] text-[#0a1630]">Welcome back</h1>
                <p className="text-[1.02rem] leading-8 text-[#5f6881]">Please enter your details to log in.</p>
              </div>

              <div className="mt-7 space-y-4">
                {errorCode && <InlineAlert tone="error" message={errorMessages[errorCode] || decodeURIComponent(errorCode)} />}
                {notice && <InlineAlert message={notice} />}

                <Button
                  type="button"
                  variant="outline"
                  className="h-[70px] w-full rounded-[18px] border-[#cfd6e7] text-[1rem] font-semibold text-[#0a1630] shadow-none hover:bg-[#f7f9ff]"
                  onClick={loginWithGoogle}
                  disabled={isSubmitting}
                >
                  <GoogleMark />
                  <span className="ml-3">Sign in with Google</span>
                </Button>

                <AuthDivider label="OR" />

                <form className="space-y-5" onSubmit={handleSubmit}>
                  <AuthField
                    label="Email"
                    icon={Mail}
                    type="email"
                    placeholder="name@company.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    autoComplete="email"
                  />

                  <AuthField
                    label="Password"
                    icon={LockKeyhole}
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                    trailing={
                      <button
                        type="button"
                        className="text-[0.95rem] font-medium text-[#1149d8] transition hover:text-[#0b3da9]"
                        onClick={() =>
                          setNotice('Password reset is not enabled yet. Use your existing password or Google sign-in.')
                        }
                      >
                        Forgot Password?
                      </button>
                    }
                  />

                  <Button
                    className="mt-2 h-[68px] w-full rounded-[18px] bg-[#1149d8] text-[1rem] font-semibold text-white shadow-[0_12px_30px_rgba(17,73,216,0.28)] hover:bg-[#0b3fc0]"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Logging In...' : 'Log In'}
                  </Button>
                </form>

                <p className="pt-2 text-center text-[1rem] text-[#5f6881]">
                  Don&apos;t have an account?{' '}
                  <Link to="/signup" className="font-semibold text-[#1149d8] transition hover:text-[#0b3da9]">
                    Sign Up
                  </Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
