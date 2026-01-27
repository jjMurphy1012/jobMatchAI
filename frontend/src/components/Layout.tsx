import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, FileText, Settings, Briefcase, User, Sparkles } from 'lucide-react'
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

  return (
    <div className="min-h-screen font-sans">
      {/* Sidebar - Dark Glass */}
      <aside className="fixed inset-y-0 left-0 z-30 w-72 glass-panel flex flex-col transition-transform duration-300 ease-in-out">
        {/* Logo */}
        <div className="h-20 flex items-center px-8 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="text-white w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-xl tracking-tight text-white">Job Matcher</h1>
              <p className="text-xs text-slate-400 font-medium">AI Powered</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-8 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-200 group relative overflow-hidden",
                  isActive 
                    ? "bg-primary text-white shadow-lg shadow-primary/25 font-medium" 
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                )
              }
            >
              <item.icon size={20} className={cn("transition-colors", "opacity-80")} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-white/10 bg-black/20">
          <button className="flex items-center gap-3 w-full p-2 rounded-xl hover:bg-white/5 transition-colors">
            <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-indigo-400 to-rose-400 p-[2px]">
              <div className="h-full w-full rounded-full bg-slate-900 flex items-center justify-center">
                 <User size={18} className="text-indigo-200" />
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
      <div className="ml-72 flex flex-col min-h-screen transition-all duration-300">
        {/* Header */}
        <header className="h-20 px-8 flex items-center justify-between sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-slate-200/50">
          <div>
            <h2 className="text-xl font-bold text-slate-800">{currentPage}</h2>
          </div>
          <div className="flex items-center gap-4">
             {/* Add global actions like notifications here later */}
             <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
             <span className="text-sm font-medium text-slate-500">System Online</span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-8">
          <div className="max-w-7xl mx-auto animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}