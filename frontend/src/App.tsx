import { Routes, Route } from 'react-router-dom'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Layout from './components/Layout'
import Admin from './pages/Admin'
import AuthCallback from './pages/AuthCallback'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import SignUp from './pages/SignUp'
import Resume from './pages/Resume'
import Preferences from './pages/Preferences'
import Jobs from './pages/Jobs'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/register" element={<SignUp />} />
      <Route path="/auth/callback" element={<AuthCallback />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="resume" element={<Resume />} />
          <Route path="preferences" element={<Preferences />} />
          <Route path="jobs" element={<Jobs />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute requireAdmin />}>
        <Route path="/admin" element={<Layout />}>
          <Route index element={<Admin />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
