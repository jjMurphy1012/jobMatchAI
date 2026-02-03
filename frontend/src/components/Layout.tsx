import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, FileText, Settings, Briefcase, User, Sparkles, Menu, X } from 'lucide-react'
import { cn } from '../lib/utils'

const navItems = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/resume', label: 'Resume Profile', icon: FileText },
  { path: '/jobs', label: 'Matched Jobs', icon: Briefcase },
  { path: '/preferences', label: 'Preferences', icon: Settings },
]

export default function Layout() {
  const location = useLocation()
  const currentPage = navItems.find(item => item.path === location.pathname)?.label || 'Dashboard'
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Close sidebar when route changes (mobile)
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Close sidebar when clicking outside (mobile)
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setSidebarOpen(false)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="min-h-screen font-sans">
      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Dark Glass */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-72 glass-panel flex flex-col transition-transform duration-300 ease-in-out",
        "lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Logo */}
        <div className="h-16 lg:h-20 flex items-center justify-between px-6 lg:px-8 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 lg:h-10 lg:w-10 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="text-white w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg lg:text-xl tracking-tight text-white">Job Matcher</h1>
              <p className="text-xs text-slate-400 font-medium">AI Powered</p>
            </div>
          </div>
          {/* Close button for mobile */}
          <button
            className="lg:hidden p-2 text-slate-400 hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={24} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 lg:px-4 py-6 lg:py-8 space-y-1 lg:space-y-2 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-4 py-3 lg:py-3.5 rounded-xl transition-all duration-200 group relative overflow-hidden",
                  isActive
                    ? "bg-primary text-white shadow-lg shadow-primary/25 font-medium"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                )
              }
            >
              <item.icon size={20} className={cn("transition-colors", "opacity-80")} />
              <span className="text-sm lg:text-base">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User Profile */}
        <div className="p-3 lg:p-4 border-t border-white/10 bg-black/20">
          <button className="flex items-center gap-3 w-full p-2 rounded-xl hover:bg-white/5 transition-colors">
            <div className="h-9 w-9 lg:h-10 lg:w-10 rounded-full bg-gradient-to-tr from-indigo-400 to-rose-400 p-[2px] flex-shrink-0">
              <div className="h-full w-full rounded-full bg-slate-900 flex items-center justify-center">
                 <User size={16} className="text-indigo-200 lg:w-[18px] lg:h-[18px]" />
              </div>
            </div>
            <div className="flex flex-col items-start overflow-hidden">
              <span className="text-sm font-medium text-white truncate w-full">User Profile</span>
              <span className="text-xs text-slate-400 truncate w-full">user@example.com</span>
            </div>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="lg:ml-72 flex flex-col min-h-screen transition-all duration-300">
        {/* Header */}
        <header className="h-14 lg:h-20 px-4 lg:px-8 flex items-center justify-between sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-slate-200/50">
          <div className="flex items-center gap-3">
            {/* Mobile menu button */}
            <button
              className="lg:hidden p-2 -ml-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu size={24} />
            </button>
            <h2 className="text-lg lg:text-xl font-bold text-slate-800">{currentPage}</h2>
          </div>
          <div className="flex items-center gap-2 lg:gap-4">
             <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
             <span className="text-xs lg:text-sm font-medium text-slate-500 hidden sm:inline">System Online</span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-8">
          <div className="max-w-7xl mx-auto animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
