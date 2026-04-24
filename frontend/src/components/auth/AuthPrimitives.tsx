import type { InputHTMLAttributes, ReactNode } from 'react'
import { ArrowRight, Briefcase, CheckCircle2, LineChart, type LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'
import { Button } from '../ui/button'

type AuthMode = 'login' | 'signup'
type AlertTone = 'neutral' | 'error'

export function AuthInlineAlert({ tone = 'neutral', message }: { tone?: AlertTone; message: string }) {
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

export function GoogleAuthButton({
  label,
  onClick,
  disabled,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <Button
      type="button"
      variant="outline"
      className="h-[70px] w-full rounded-[18px] border-[#cfd6e7] text-[1rem] font-semibold text-[#0a1630] shadow-none hover:bg-[#f7f9ff]"
      onClick={onClick}
      disabled={disabled}
    >
      <GoogleMark />
      <span className="ml-3">{label}</span>
    </Button>
  )
}

export function AuthBrand({
  centered = false,
  light = false,
}: {
  centered?: boolean
  light?: boolean
}) {
  return (
    <div className={cn('flex items-center gap-3', centered && 'justify-center')}>
      <div
        className={cn(
          'flex h-11 w-11 items-center justify-center rounded-2xl',
          light ? 'bg-white/14 text-white' : 'bg-[#1149d8] text-white',
        )}
      >
        <Briefcase className="h-6 w-6" strokeWidth={2.2} />
      </div>
      <div
        className={cn(
          'text-[2.1rem] font-semibold tracking-[-0.05em]',
          light ? 'text-white' : 'text-[#1149d8]',
        )}
      >
        CareerRise
      </div>
    </div>
  )
}

export function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6">
      <path
        fill="#EA4335"
        d="M12.24 10.286v3.821h5.414c-.229 1.23-.917 2.273-1.95 2.974l3.153 2.448c1.838-1.694 2.897-4.193 2.897-7.154 0-.701-.063-1.375-.179-2.024z"
      />
      <path
        fill="#34A853"
        d="M12 21c2.628 0 4.832-.867 6.442-2.357l-3.153-2.448c-.876.588-1.995.936-3.289.936-2.526 0-4.664-1.706-5.428-4.001H3.316v2.514A9.72 9.72 0 0 0 12 21z"
      />
      <path
        fill="#FBBC05"
        d="M6.572 13.13A5.84 5.84 0 0 1 6.268 11.5c0-.565.101-1.112.284-1.63V7.356H3.316A9.72 9.72 0 0 0 2.28 11.5c0 1.559.373 3.034 1.036 4.356z"
      />
      <path
        fill="#4285F4"
        d="M12 5.87c1.43 0 2.716.492 3.729 1.457l2.798-2.799C16.829 2.945 14.626 2 12 2a9.72 9.72 0 0 0-8.684 5.356l3.236 2.514C7.336 7.575 9.474 5.87 12 5.87z"
      />
    </svg>
  )
}

export function AuthDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-4 text-[0.78rem] font-semibold uppercase tracking-[0.24em] text-[#8a92ab]">
      <div className="h-px flex-1 bg-[#d7dced]" />
      <span>{label}</span>
      <div className="h-px flex-1 bg-[#d7dced]" />
    </div>
  )
}

export function AuthField({
  label,
  icon: Icon,
  trailing,
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string
  icon: LucideIcon
  trailing?: ReactNode
}) {
  return (
    <label className="block space-y-3">
      <div className="flex items-center justify-between gap-4">
        <span className="text-[1.03rem] font-semibold text-[#0f172a]">{label}</span>
        {trailing}
      </div>
      <div className="flex h-[68px] items-center rounded-[18px] border border-[#d7dced] bg-white px-5 shadow-[0_1px_0_rgba(148,163,184,0.08)] transition-colors focus-within:border-[#1149d8] focus-within:ring-4 focus-within:ring-[#1149d8]/10">
        <Icon className="mr-4 h-5 w-5 shrink-0 text-[#8b93a8]" strokeWidth={2.2} />
        <input
          className={cn(
            'w-full border-0 bg-transparent p-0 text-[1rem] text-[#0f172a] placeholder:text-[#8a92ab] focus:outline-none focus:ring-0',
            className,
          )}
          {...props}
        />
      </div>
    </label>
  )
}

export function DesktopAuthPanel({ mode }: { mode: AuthMode }) {
  const content =
    mode === 'signup'
      ? {
          eyebrow: 'Build your search operating system',
          title: 'Start structured, stay fast, and keep every opportunity in one place.',
          body:
            'CareerRise keeps your resume, profile, matches, and next actions in a single secure workspace built for modern job search loops.',
        }
      : {
          eyebrow: 'Return to your search cockpit',
          title: 'Come back to the jobs, materials, and next actions already lined up for you.',
          body:
            'Pick up exactly where you left off with your saved profile, matched roles, and application workflow already scoped to your account.',
        }

  return (
    <div className="relative hidden overflow-hidden rounded-[34px] bg-[linear-gradient(155deg,#0d1b46_0%,#123fa3_58%,#0d53e5_100%)] p-10 text-white shadow-[0_36px_90px_rgba(17,73,216,0.22)] lg:flex lg:min-h-[760px] lg:flex-col">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.24),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(125,211,252,0.2),transparent_34%)]" />
      <div className="relative z-10 flex h-full flex-col">
        <AuthBrand light />

        <div className="mt-14 inline-flex w-fit items-center gap-2 rounded-full border border-white/18 bg-white/10 px-4 py-2 text-xs font-medium uppercase tracking-[0.22em] text-white/82">
          <CheckCircle2 className="h-4 w-4" />
          {content.eyebrow}
        </div>

        <div className="relative z-10 mt-auto space-y-8">
          <div className="space-y-5">
            <h1 className="max-w-xl text-5xl font-semibold leading-[1.02] tracking-[-0.05em]">
              {content.title}
            </h1>
            <p className="max-w-xl text-lg leading-8 text-white/78">{content.body}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-[24px] border border-white/14 bg-white/10 p-5 backdrop-blur-sm">
              <div className="text-sm text-white/66">Workspace</div>
              <div className="mt-4 text-3xl font-semibold">1 hub</div>
              <div className="mt-2 text-sm leading-6 text-white/76">
                Resume, career profile, jobs, and interview prep stay connected.
              </div>
            </div>
            <div className="rounded-[24px] border border-white/14 bg-white/10 p-5 backdrop-blur-sm">
              <div className="flex items-center gap-2 text-sm text-white/66">
                <LineChart className="h-4 w-4" />
                Progress loop
              </div>
              <div className="mt-4 text-3xl font-semibold">Focused</div>
              <div className="mt-2 text-sm leading-6 text-white/76">
                One login to keep profile updates, matches, and next actions moving.
              </div>
            </div>
          </div>

          <div className="inline-flex items-center gap-2 text-sm font-medium text-white/72">
            Secure session cookies
            <ArrowRight className="h-4 w-4" />
            Google sign-in live now
          </div>
        </div>
      </div>
    </div>
  )
}
