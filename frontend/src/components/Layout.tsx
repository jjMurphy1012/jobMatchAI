import { Outlet, NavLink } from 'react-router-dom'
import { LayoutDashboard, FileText, Settings, Briefcase } from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/resume', label: 'Resume', icon: FileText },
  { path: '/preferences', label: 'Preferences', icon: Settings },
  { path: '/jobs', label: 'Jobs', icon: Briefcase },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 fixed h-full">
        <div className="p-6">
          <h1 className="text-xl font-bold text-gray-900">
            Job Matching AI
          </h1>
          <p className="text-sm text-gray-500 mt-1">Find your dream job</p>
        </div>

        <nav className="px-4">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg mb-1 transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              <item.icon size={20} />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-64 p-8">
        <Outlet />
      </main>
    </div>
  )
}
