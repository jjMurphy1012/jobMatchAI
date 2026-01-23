import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Resume from './pages/Resume'
import Preferences from './pages/Preferences'
import Jobs from './pages/Jobs'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="resume" element={<Resume />} />
        <Route path="preferences" element={<Preferences />} />
        <Route path="jobs" element={<Jobs />} />
      </Route>
    </Routes>
  )
}

export default App
