import { useEffect, useState } from 'react'
import { Save, Loader } from 'lucide-react'
import { preferencesApi, PreferenceData } from '../api/client'

export default function Preferences() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState<PreferenceData>({
    keywords: '',
    location: '',
    is_intern: false,
    need_sponsor: false,
    experience_level: '',
    job_description: '',
    remote_preference: '',
    reminder_enabled: true,
    reminder_email: '',
  })

  useEffect(() => {
    loadPreferences()
  }, [])

  async function loadPreferences() {
    setLoading(true)
    const result = await preferencesApi.get()
    if (result.data) {
      setForm({
        keywords: result.data.keywords || '',
        location: result.data.location || '',
        is_intern: result.data.is_intern,
        need_sponsor: result.data.need_sponsor,
        experience_level: result.data.experience_level || '',
        job_description: result.data.job_description || '',
        remote_preference: result.data.remote_preference || '',
        reminder_enabled: result.data.reminder_enabled,
        reminder_email: result.data.reminder_email || '',
      })
    }
    setLoading(false)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)

    const result = await preferencesApi.save(form)

    if (result.error) {
      setError(result.error)
    } else {
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    }

    setSaving(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Job Preferences</h1>
      <p className="text-gray-600 mb-8">
        Set your job search criteria for personalized matches
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {saved && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
          Preferences saved successfully!
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Keywords */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Search Keywords</h3>
          <input
            type="text"
            className="input"
            placeholder="e.g., React, Frontend Developer, TypeScript"
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
            required
          />
          <p className="text-sm text-gray-500 mt-2">
            Separate keywords with commas
          </p>
        </div>

        {/* Location */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Location</h3>
          <input
            type="text"
            className="input"
            placeholder="e.g., Boston, MA or New York"
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
          />
        </div>

        {/* Job Type Options */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Job Type</h3>

          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                checked={form.is_intern}
                onChange={(e) => setForm({ ...form, is_intern: e.target.checked })}
              />
              <div>
                <span className="font-medium text-gray-900">Internship positions only</span>
                <p className="text-sm text-gray-500">Filter for intern/internship roles</p>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                checked={form.need_sponsor}
                onChange={(e) => setForm({ ...form, need_sponsor: e.target.checked })}
              />
              <div>
                <span className="font-medium text-gray-900">Need visa sponsorship</span>
                <p className="text-sm text-gray-500">Looking for H1B/visa sponsoring companies</p>
              </div>
            </label>
          </div>
        </div>

        {/* Remote Preference */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Work Preference</h3>
          <div className="grid grid-cols-3 gap-3">
            {['remote', 'hybrid', 'onsite'].map((option) => (
              <label
                key={option}
                className={`flex items-center justify-center p-3 border rounded-lg cursor-pointer transition-colors ${
                  form.remote_preference === option
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="remote_preference"
                  value={option}
                  checked={form.remote_preference === option}
                  onChange={(e) => setForm({ ...form, remote_preference: e.target.value })}
                  className="sr-only"
                />
                <span className="capitalize font-medium">{option}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Experience Level */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Experience Level</h3>
          <select
            className="input"
            value={form.experience_level}
            onChange={(e) => setForm({ ...form, experience_level: e.target.value })}
          >
            <option value="">Any level</option>
            <option value="entry">Entry Level (0-2 years)</option>
            <option value="mid">Mid Level (2-5 years)</option>
            <option value="senior">Senior Level (5+ years)</option>
          </select>
        </div>

        {/* Job Description */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Target Job Description</h3>
          <textarea
            className="input min-h-[120px]"
            placeholder="Describe your ideal job role, responsibilities, and what you're looking for..."
            value={form.job_description}
            onChange={(e) => setForm({ ...form, job_description: e.target.value })}
          />
          <p className="text-sm text-gray-500 mt-2">
            This helps AI better understand what you're looking for
          </p>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={saving}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {saving ? (
            <Loader className="animate-spin" size={20} />
          ) : (
            <Save size={20} />
          )}
          {saving ? 'Saving...' : 'Save Preferences'}
        </button>
      </form>
    </div>
  )
}
