import { useEffect, useMemo, useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  Bell,
  BookOpen,
  Briefcase,
  FileText,
  LayoutDashboard,
  LogOut,
  Settings,
  Shield,
  Sparkles,
  User,
} from 'lucide-react'

import { cn } from '../lib/utils'
import { useAuth } from './auth/AuthProvider'

const navItems = [
  { path: '/', label: 'Today', mobileLabel: 'Today', icon: LayoutDashboard },
  { path: '/resume', label: 'Resume', mobileLabel: 'Resume', icon: FileText },
  { path: '/preferences', label: 'Career Profile', mobileLabel: 'Profile', icon: Settings },
  { path: '/matches', label: 'Matches', mobileLabel: 'Matches', icon: Briefcase },
  { path: '/interviews', label: 'Interview Prep', mobileLabel: 'Prep', icon: BookOpen },
]

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [mobileAccountOpen, setMobileAccountOpen] = useState(false)

  const fullNavItems = useMemo(
    () =>
      user?.role === 'admin'
        ? [...navItems, { path: '/admin', label: 'Admin Console', mobileLabel: 'Admin', icon: Shield }]
        : navItems,
    [user?.role]
  )

  const normalizedPath = location.pathname === '/jobs' ? '/matches' : location.pathname
  const currentPage = fullNavItems.find((item) => item.path === normalizedPath)?.label || 'Today'

  useEffect(() => {
    setMobileAccountOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen text-foreground">
      <aside className="fixed inset-y-4 left-4 z-30 hidden w-[288px] flex-col rounded-[2rem] glass-panel p-4 lg:flex">
        <div className="rounded-[1.75rem] bg-primary px-5 py-5 text-primary-foreground shadow-[0_20px_45px_-25px_rgba(26,86,219,0.8)]">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/20">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-white/70">Career OS</p>
              <h1 className="text-2xl font-semibold tracking-tight">CareerRise</h1>
            </div>
          </div>
          <p className="mt-5 text-sm leading-6 text-white/78">
            Keep resume, targeting, matches, and interview prep in one clean workflow.
          </p>
        </div>

        <nav className="mt-5 flex-1 space-y-2">
          {fullNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-3 rounded-[1.35rem] px-4 py-3.5 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-primary text-white shadow-[0_14px_30px_-18px_rgba(26,86,219,0.8)]'
                    : 'text-slate-600 hover:bg-white/80 hover:text-slate-900'
                )
              }
            >
              <item.icon className="h-5 w-5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-4 rounded-[1.6rem] border border-white/80 bg-white/88 p-4 shadow-[0_20px_45px_-30px_rgba(55,65,81,0.25)]">
          <div className="flex items-center gap-3">
            <button
              className="flex h-12 w-12 flex-shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-slate-100"
              onClick={() => navigate('/resume')}
              title="Open account area"
            >
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt={user.name || user.email} className="h-full w-full object-cover" />
              ) : (
                <User className="h-5 w-5 text-slate-500" />
              )}
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900">{user?.name || 'CareerRise User'}</p>
              <p className="truncate text-xs text-slate-500">{user?.email}</p>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between rounded-2xl bg-slate-100/90 px-3 py-2">
            <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{user?.role}</span>
            <button
              className="inline-flex items-center gap-2 text-sm font-medium text-slate-700 transition-colors hover:text-slate-950"
              onClick={logout}
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>

      <div className="min-h-screen lg:ml-[320px]">
        <header className="sticky top-0 z-20 border-b border-white/70 bg-background/88 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:hidden">
            <button
              className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl border border-white/80 bg-white/90 shadow-sm"
              onClick={() => setMobileAccountOpen((current) => !current)}
              title="Open account menu"
            >
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt={user.name || user.email} className="h-full w-full object-cover" />
              ) : (
                <User className="h-5 w-5 text-slate-500" />
              )}
            </button>

            <div className="absolute left-1/2 flex -translate-x-1/2 items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-white shadow-[0_10px_22px_-16px_rgba(26,86,219,0.9)]">
                <Sparkles className="h-5 w-5" />
              </div>
              <span className="text-[1.85rem] font-semibold tracking-tight text-primary">CareerRise</span>
            </div>

            <div className="flex items-center gap-2">
              {user?.role === 'admin' ? (
                <button
                  className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/80 bg-white/90 shadow-sm"
                  onClick={() => navigate('/admin')}
                  title="Open admin console"
                >
                  <Shield className="h-5 w-5 text-primary" />
                </button>
              ) : (
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/80 bg-white/90 shadow-sm">
                  <Bell className="h-5 w-5 text-slate-500" />
                </div>
              )}
            </div>
          </div>

          {mobileAccountOpen && (
            <div className="border-t border-white/70 bg-white/92 px-4 pb-4 pt-3 shadow-[0_18px_40px_-32px_rgba(55,65,81,0.3)] lg:hidden">
              <div className="rounded-[1.5rem] border border-slate-200/80 bg-white px-4 py-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-900">{user?.name || 'CareerRise User'}</p>
                <p className="mt-1 text-sm text-slate-500">{user?.email}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                    {user?.role}
                  </span>
                  <div className="flex items-center gap-2">
                    {user?.role === 'admin' && (
                      <button
                        className="inline-flex items-center rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700"
                        onClick={() => navigate('/admin')}
                      >
                        Admin
                      </button>
                    )}
                    <button
                      className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
                      onClick={logout}
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Sign Out
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="mx-auto hidden h-20 max-w-7xl items-center justify-between px-8 lg:flex">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Workspace</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{currentPage}</h2>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/90 px-4 py-2 text-sm font-medium text-slate-600 shadow-sm">
              <span className="h-2.5 w-2.5 rounded-full bg-[hsl(var(--brand-success))]" />
              System Online
            </div>
          </div>
        </header>

        <main className="bottom-nav-safe px-4 py-6 sm:px-6 lg:px-8 lg:py-8 lg:pb-8">
          <div className="mx-auto max-w-7xl animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>

      <nav className="fixed inset-x-3 bottom-3 z-30 lg:hidden">
        <div className="mx-auto max-w-xl rounded-[1.9rem] border border-white/80 bg-white/95 px-2 pt-2 shadow-[0_22px_55px_-28px_rgba(55,65,81,0.35)] backdrop-blur-xl">
          <div className="grid grid-cols-5 gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-[68px] flex-col items-center justify-center gap-1 rounded-[1.35rem] px-1 pb-[calc(0.45rem+env(safe-area-inset-bottom))] pt-2 text-[11px] font-medium transition-all duration-200',
                    isActive ? 'bg-primary text-white shadow-[0_12px_24px_-18px_rgba(26,86,219,0.9)]' : 'text-slate-500'
                  )
                }
              >
                <item.icon className="h-[18px] w-[18px]" />
                <span>{item.mobileLabel}</span>
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
    </div>
  )
}
