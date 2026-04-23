import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Shield, Trash2, Users } from 'lucide-react'

import {
  adminApi,
  AdminInterviewExperience,
  AdminInterviewExperiencePayload,
  AdminUser,
} from '../api/client'
import { useAuth } from '../components/auth/AuthProvider'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

const emptyExperienceForm: AdminInterviewExperiencePayload = {
  company_name: '',
  role: '',
  level: '',
  year: undefined,
  rounds: '',
  topics: [],
  summary: '',
  source_url: '',
  source_site: '',
  review_status: 'draft',
  relevance_keywords: [],
}

function splitCsv(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export default function Admin() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [experiences, setExperiences] = useState<AdminInterviewExperience[]>([])
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [loadingExperiences, setLoadingExperiences] = useState(true)
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)
  const [savingExperience, setSavingExperience] = useState(false)
  const [deletingExperienceId, setDeletingExperienceId] = useState<string | null>(null)
  const [editingExperienceId, setEditingExperienceId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [experienceForm, setExperienceForm] = useState({
    ...emptyExperienceForm,
    topics_input: '',
    relevance_keywords_input: '',
  })

  useEffect(() => {
    void Promise.all([loadUsers(), loadExperiences()])
  }, [])

  const adminsCount = useMemo(() => users.filter((item) => item.role === 'admin').length, [users])

  async function loadUsers() {
    setLoadingUsers(true)
    const response = await adminApi.listUsers()
    if (response.data) {
      setUsers(response.data)
      setError(null)
    } else {
      setError(response.error || 'Unable to load users.')
    }
    setLoadingUsers(false)
  }

  async function loadExperiences() {
    setLoadingExperiences(true)
    const response = await adminApi.listInterviewExperiences()
    if (response.data) {
      setExperiences(response.data)
      setError(null)
    } else {
      setError(response.error || 'Unable to load interview experiences.')
    }
    setLoadingExperiences(false)
  }

  async function toggleRole(user: AdminUser) {
    const isSelf = currentUser?.id === user.id
    if (isSelf && user.role === 'admin') {
      return
    }

    const nextRole = user.role === 'admin' ? 'user' : 'admin'
    setUpdatingUserId(user.id)
    const response = await adminApi.updateUserRole(user.id, nextRole)
    if (response.data) {
      setUsers((current) => current.map((item) => (item.id === user.id ? response.data! : item)))
      setError(null)
    } else {
      setError(response.error || 'Unable to update user role.')
    }
    setUpdatingUserId(null)
  }

  function startCreateExperience() {
    setEditingExperienceId(null)
    setExperienceForm({
      ...emptyExperienceForm,
      topics_input: '',
      relevance_keywords_input: '',
    })
  }

  function startEditExperience(experience: AdminInterviewExperience) {
    setEditingExperienceId(experience.id)
    setExperienceForm({
      company_name: experience.company_name,
      role: experience.role,
      level: experience.level || '',
      year: experience.year,
      rounds: experience.rounds || '',
      topics: experience.topics,
      summary: experience.summary,
      source_url: experience.source_url || '',
      source_site: experience.source_site || '',
      review_status: experience.review_status,
      relevance_keywords: experience.relevance_keywords,
      topics_input: experience.topics.join(', '),
      relevance_keywords_input: experience.relevance_keywords.join(', '),
    })
  }

  async function saveExperience() {
    setSavingExperience(true)
    const payload: AdminInterviewExperiencePayload = {
      company_name: experienceForm.company_name.trim(),
      role: experienceForm.role.trim(),
      level: experienceForm.level?.trim() || null,
      year: experienceForm.year || null,
      rounds: experienceForm.rounds?.trim() || null,
      topics: splitCsv(experienceForm.topics_input),
      summary: experienceForm.summary.trim(),
      source_url: experienceForm.source_url?.trim() || null,
      source_site: experienceForm.source_site?.trim() || null,
      review_status: experienceForm.review_status,
      relevance_keywords: splitCsv(experienceForm.relevance_keywords_input),
    }

    const response = editingExperienceId
      ? await adminApi.updateInterviewExperience(editingExperienceId, payload)
      : await adminApi.createInterviewExperience(payload)

    if (response.data) {
      setError(null)
      startCreateExperience()
      await loadExperiences()
    } else {
      setError(response.error || 'Unable to save interview experience.')
    }
    setSavingExperience(false)
  }

  async function removeExperience(id: string) {
    setDeletingExperienceId(id)
    const response = await adminApi.deleteInterviewExperience(id)
    if (response.data) {
      setExperiences((current) => current.filter((item) => item.id !== id))
      setError(null)
      if (editingExperienceId === id) {
        startCreateExperience()
      }
    } else {
      setError(response.error || 'Unable to delete interview experience.')
    }
    setDeletingExperienceId(null)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-indigo-600">Admin Console</p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Access and content operations</h1>
          <p className="mt-2 max-w-3xl text-slate-600">
            Manage who can administer the product, and curate interview experiences that appear in the user-facing Interview Prep section.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">
          <Shield className="h-4 w-4" />
          Admin-only route
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total users</CardDescription>
            <CardTitle>{users.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Admins</CardDescription>
            <CardTitle>{adminsCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Interview experiences</CardDescription>
            <CardTitle>{experiences.length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <Card className="border-slate-200/80">
          <CardHeader>
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-slate-500" />
              <div>
                <CardTitle className="text-xl">Users and roles</CardTitle>
                <CardDescription>
                  Promote or demote other users. Your own admin role cannot be removed here.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingUsers ? (
              <div className="flex items-center gap-3 py-8 text-sm text-slate-500">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700"></div>
                Loading users...
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-slate-500">User</th>
                      <th className="px-4 py-3 text-left font-medium text-slate-500">Role</th>
                      <th className="px-4 py-3 text-left font-medium text-slate-500">Last Login</th>
                      <th className="px-4 py-3 text-right font-medium text-slate-500">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {users.map((user) => {
                      const isSelf = currentUser?.id === user.id
                      const demoteDisabled = isSelf && user.role === 'admin'
                      return (
                        <tr key={user.id}>
                          <td className="px-4 py-4">
                            <div className="font-medium text-slate-900">
                              {user.name || user.email}
                              {isSelf ? ' (You)' : ''}
                            </div>
                            <div className="text-slate-500">{user.email}</div>
                          </td>
                          <td className="px-4 py-4">
                            <Badge variant={user.role === 'admin' ? 'success' : 'secondary'}>
                              {user.role}
                            </Badge>
                          </td>
                          <td className="px-4 py-4 text-slate-500">
                            {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}
                          </td>
                          <td className="px-4 py-4 text-right">
                            <div className="inline-flex flex-col items-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={updatingUserId === user.id || demoteDisabled}
                                onClick={() => void toggleRole(user)}
                              >
                                {updatingUserId === user.id
                                  ? 'Updating...'
                                  : user.role === 'admin'
                                    ? 'Make User'
                                    : 'Make Admin'}
                              </Button>
                              {demoteDisabled && (
                                <span className="text-xs text-slate-400">You cannot demote yourself.</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200/80">
          <CardHeader>
            <div className="flex items-center gap-3">
              <BookOpen className="h-5 w-5 text-slate-500" />
              <div>
                <CardTitle className="text-xl">{editingExperienceId ? 'Edit interview experience' : 'Add interview experience'}</CardTitle>
                <CardDescription>
                  This is the admin entry point for the Interview Prep section. Crawlers can feed into this later.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-2 text-sm text-slate-700">
                Company
                <input
                  className="rounded-xl border border-slate-200 px-3 py-2"
                  value={experienceForm.company_name}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, company_name: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Role
                <input
                  className="rounded-xl border border-slate-200 px-3 py-2"
                  value={experienceForm.role}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, role: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Level
                <input
                  className="rounded-xl border border-slate-200 px-3 py-2"
                  value={experienceForm.level || ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, level: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Year
                <input
                  className="rounded-xl border border-slate-200 px-3 py-2"
                  type="number"
                  value={experienceForm.year ?? ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, year: event.target.value ? Number(event.target.value) : undefined }))}
                />
              </label>
            </div>

            <label className="grid gap-2 text-sm text-slate-700">
              Interview rounds summary
              <textarea
                className="min-h-[88px] rounded-xl border border-slate-200 px-3 py-2"
                value={experienceForm.rounds || ''}
                onChange={(event) => setExperienceForm((current) => ({ ...current, rounds: event.target.value }))}
              />
            </label>

            <label className="grid gap-2 text-sm text-slate-700">
              Topics
              <input
                className="rounded-xl border border-slate-200 px-3 py-2"
                placeholder="Algorithms, System Design, Behavioral"
                value={experienceForm.topics_input}
                onChange={(event) => setExperienceForm((current) => ({ ...current, topics_input: event.target.value }))}
              />
            </label>

            <label className="grid gap-2 text-sm text-slate-700">
              Relevance keywords
              <input
                className="rounded-xl border border-slate-200 px-3 py-2"
                placeholder="backend, platform, distributed systems"
                value={experienceForm.relevance_keywords_input}
                onChange={(event) => setExperienceForm((current) => ({ ...current, relevance_keywords_input: event.target.value }))}
              />
            </label>

            <label className="grid gap-2 text-sm text-slate-700">
              Summary
              <textarea
                className="min-h-[140px] rounded-xl border border-slate-200 px-3 py-2"
                value={experienceForm.summary}
                onChange={(event) => setExperienceForm((current) => ({ ...current, summary: event.target.value }))}
              />
            </label>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="grid gap-2 text-sm text-slate-700 md:col-span-2">
                Source URL
                <input
                  className="rounded-xl border border-slate-200 px-3 py-2"
                  value={experienceForm.source_url || ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, source_url: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Source site
                <input
                  className="rounded-xl border border-slate-200 px-3 py-2"
                  value={experienceForm.source_site || ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, source_site: event.target.value }))}
                />
              </label>
            </div>

            <label className="grid gap-2 text-sm text-slate-700">
              Status
              <select
                className="rounded-xl border border-slate-200 px-3 py-2"
                value={experienceForm.review_status}
                onChange={(event) => setExperienceForm((current) => ({ ...current, review_status: event.target.value as 'draft' | 'published' }))}
              >
                <option value="draft">draft</option>
                <option value="published">published</option>
              </select>
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={() => void saveExperience()} disabled={savingExperience}>
                {savingExperience ? 'Saving...' : editingExperienceId ? 'Save Changes' : 'Create Entry'}
              </Button>
              <Button variant="outline" onClick={startCreateExperience}>
                Reset
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200/80">
        <CardHeader>
          <CardTitle className="text-xl">Interview library</CardTitle>
          <CardDescription>
            Published items will appear in the user-facing Interview Prep page. Drafts stay here until you publish them.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingExperiences ? (
            <div className="flex items-center gap-3 py-8 text-sm text-slate-500">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700"></div>
              Loading interview experiences...
            </div>
          ) : experiences.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 px-6 py-10 text-center text-sm text-slate-500">
              No interview experiences yet. Create the first one from the form above.
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {experiences.map((experience) => (
                <div key={experience.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={experience.review_status === 'published' ? 'success' : 'secondary'}>
                      {experience.review_status}
                    </Badge>
                    <Badge variant="outline">{experience.company_name}</Badge>
                    {experience.level && <Badge variant="outline">{experience.level}</Badge>}
                    {experience.year && <Badge variant="outline">{experience.year}</Badge>}
                  </div>
                  <div className="mt-4">
                    <h3 className="text-lg font-semibold text-slate-900">{experience.role}</h3>
                    <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-600">{experience.summary}</p>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {experience.topics.slice(0, 4).map((topic) => (
                      <Badge key={topic} variant="warning">
                        {topic}
                      </Badge>
                    ))}
                  </div>
                  <div className="mt-5 flex items-center justify-between">
                    <Button variant="outline" size="sm" onClick={() => startEditExperience(experience)}>
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      disabled={deletingExperienceId === experience.id}
                      onClick={() => void removeExperience(experience.id)}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      {deletingExperienceId === experience.id ? 'Deleting...' : 'Delete'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
