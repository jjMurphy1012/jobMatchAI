import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, LockKeyhole, Mail, User2 } from 'lucide-react'
import { useAuth } from '../components/auth/AuthProvider'
import { authApi } from '../api/client'
import { AuthBrand, AuthDivider, AuthField, DesktopAuthPanel, GoogleMark } from '../components/auth/AuthPrimitives'
import { Button } from '../components/ui/button'

function InlineAlert({ message }: { message: string }) {
  return (
    <div className="rounded-[18px] border border-[#d7e2ff] bg-[#eef4ff] px-4 py-3 text-sm text-[#2455d6]">
      {message}
    </div>
  )
}

function SignUpForm({
  onGoogleLogin,
  onEmailRegister,
}: {
  onGoogleLogin: () => void
  onEmailRegister: (payload: { name: string; email: string; password: string }) => Promise<string | null>
}) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [notice, setNotice] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')
    if (!fullName || !email || !password) {
      setNotice('Enter your name, email, and password to create an account.')
      return
    }
    if (!agreed) {
      setNotice('Please agree to the terms before creating an account.')
      return
    }
    setIsSubmitting(true)
    const error = await onEmailRegister({ name: fullName, email, password })
    setIsSubmitting(false)
    if (error) {
      setNotice(error)
    }
  }

  return (
    <div className="space-y-6">
      {notice && <InlineAlert message={notice} />}

      <Button
        type="button"
        variant="outline"
        className="h-[70px] w-full rounded-[18px] border-[#cfd6e7] text-[1rem] font-semibold text-[#0a1630] shadow-none hover:bg-[#f7f9ff]"
        onClick={onGoogleLogin}
        disabled={isSubmitting}
      >
        <GoogleMark />
        <span className="ml-3">Sign up with Google</span>
      </Button>

      <AuthDivider label="OR REGISTER WITH EMAIL" />

      <form className="space-y-5" onSubmit={handleSubmit}>
        <AuthField
          label="Full Name"
          icon={User2}
          type="text"
          placeholder="Jane Doe"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          autoComplete="name"
        />

        <AuthField
          label="Email Address"
          icon={Mail}
          type="email"
          placeholder="jane@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
        />

        <div className="space-y-3">
          <AuthField
            label="Password"
            icon={LockKeyhole}
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
          />
          <p className="text-[0.98rem] text-[#667089]">Must be at least 8 characters long.</p>
        </div>

        <label className="flex items-start gap-3 text-[0.98rem] leading-7 text-[#4f5872]">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            className="mt-1 h-6 w-6 rounded-md border border-[#cfd6e7] text-[#1149d8] focus:ring-[#1149d8]"
          />
          <span>
            I agree to the{' '}
            <span className="font-semibold text-[#1149d8] underline underline-offset-4">Terms and Conditions</span>{' '}
            and <span className="font-semibold text-[#1149d8] underline underline-offset-4">Privacy Policy</span>.
          </span>
        </label>

        <Button
          className="h-[68px] w-full rounded-[18px] bg-[#1149d8] text-[1rem] font-semibold text-white shadow-[0_12px_30px_rgba(17,73,216,0.28)] hover:bg-[#0b3fc0]"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Creating Account...' : 'Create Account'}
          <ArrowRight className="ml-3 h-5 w-5" />
        </Button>
      </form>

      <p className="pt-1 text-center text-[1rem] text-[#5f6881]">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-[#1149d8] transition hover:text-[#0b3da9]">
          Log In
        </Link>
      </p>
    </div>
  )
}

export default function SignUp() {
  const { user, isLoading, loginWithGoogle, refreshUser } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isLoading && user) {
      navigate('/', { replace: true })
    }
  }, [isLoading, navigate, user])

  async function handleEmailRegister(payload: { name: string; email: string; password: string }) {
    const response = await authApi.register(payload)
    if (response.error) {
      return response.error
    }
    await refreshUser()
    navigate('/', { replace: true })
    return null
  }

  return (
    <div className="min-h-screen bg-[#f6f7fc] px-4 py-6 text-[#0f172a] sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-6xl flex-col lg:grid lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,520px)] lg:gap-8">
        <DesktopAuthPanel mode="signup" />

        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-[430px] lg:max-w-[520px]">
            <div className="pb-8 pt-3 lg:hidden">
              <AuthBrand />
            </div>

            <div className="space-y-4 lg:hidden">
              <h1 className="text-[3.1rem] font-semibold leading-[1.02] tracking-[-0.07em] text-[#0a1630]">
                Create an account
              </h1>
              <p className="max-w-[24rem] text-[1.05rem] leading-8 text-[#5f6881]">
                Enter your details to get started on your job search journey.
              </p>
            </div>

            <div className="mt-10 lg:hidden">
              <SignUpForm onGoogleLogin={loginWithGoogle} onEmailRegister={handleEmailRegister} />
            </div>

            <div className="hidden rounded-[30px] border border-[#d7dced] bg-white px-8 py-9 shadow-[0_16px_48px_rgba(15,23,42,0.08)] lg:block">
              <div className="mb-8 space-y-4">
                <AuthBrand />
                <div className="space-y-3">
                  <h1 className="text-[2.7rem] font-semibold tracking-[-0.06em] text-[#0a1630]">Create an account</h1>
                  <p className="max-w-[25rem] text-[1rem] leading-7 text-[#5f6881]">
                    Enter your details to get started on your job search journey.
                  </p>
                </div>
              </div>
              <SignUpForm onGoogleLogin={loginWithGoogle} onEmailRegister={handleEmailRegister} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
