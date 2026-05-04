import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Database, Power, RefreshCw, Shield, Trash2, Users } from 'lucide-react'

import {
  adminApi,
  AdminInterviewExperience,
  AdminInterviewExperiencePayload,
  AdminUser,
  CompanySource,
  CompanySourcePayload,
  SourceSyncRun,
} from '../api/client'
import { useAuth } from '../components/auth/AuthProvider'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

type ExperienceFormState = Omit<AdminInterviewExperiencePayload, 'topics' | 'relevance_keywords'> & {
  topics_input: string
  relevance_keywords_input: string
}

type SourceFormState = CompanySourcePayload

const emptyExperienceForm: ExperienceFormState = {
  company_name: '',
  role: '',
  level: '',
  year: undefined,
  rounds: '',
  summary: '',
  source_url: '',
  source_site: '',
  review_status: 'draft',
  topics_input: '',
  relevance_keywords_input: '',
}

const emptySourceForm: SourceFormState = {
  source_type: 'greenhouse',
  company_name: '',
  board_token: '',
  is_active: true,
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
  const [companySources, setCompanySources] = useState<CompanySource[]>([])
  const [syncRuns, setSyncRuns] = useState<SourceSyncRun[]>([])
  const [experiences, setExperiences] = useState<AdminInterviewExperience[]>([])
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [loadingSources, setLoadingSources] = useState(true)
  const [loadingSyncRuns, setLoadingSyncRuns] = useState(true)
  const [loadingExperiences, setLoadingExperiences] = useState(true)
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)
  const [savingSource, setSavingSource] = useState(false)
  const [syncingSourceId, setSyncingSourceId] = useState<string | null>(null)
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null)
  const [savingExperience, setSavingExperience] = useState(false)
  const [deletingExperienceId, setDeletingExperienceId] = useState<string | null>(null)
  const [editingExperienceId, setEditingExperienceId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sourceForm, setSourceForm] = useState<SourceFormState>(emptySourceForm)
  const [experienceForm, setExperienceForm] = useState<ExperienceFormState>(emptyExperienceForm)

  useEffect(() => {
    void Promise.all([loadUsers(), loadCompanySources(), loadSyncRuns(), loadExperiences()])
  }, [])

  const adminsCount = useMemo(() => users.filter((item) => item.role === 'admin').length, [users])
  const activeSourceCount = useMemo(
    () => companySources.filter((item) => item.is_active).length,
    [companySources]
  )
  const publishedCount = useMemo(
    () => experiences.filter((item) => item.review_status === 'published').length,
    [experiences]
  )

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

  async function loadCompanySources() {
    setLoadingSources(true)
    const response = await adminApi.listCompanySources()
    if (response.data) {
      setCompanySources(response.data)
      setError(null)
    } else {
      setError(response.error || 'Unable to load company sources.')
    }
    setLoadingSources(false)
  }

  async function loadSyncRuns() {
    setLoadingSyncRuns(true)
    const response = await adminApi.listSourceSyncRuns(12)
    if (response.data) {
      setSyncRuns(response.data)
      setError(null)
    } else {
      setError(response.error || 'Unable to load source sync logs.')
    }
    setLoadingSyncRuns(false)
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

  function startCreateSource() {
    setEditingSourceId(null)
    setSourceForm(emptySourceForm)
  }

  function startEditSource(source: CompanySource) {
    setEditingSourceId(source.id)
    setSourceForm({
      source_type: source.source_type,
      company_name: source.company_name,
      board_token: source.board_token,
      is_active: source.is_active,
    })
  }

  async function saveSource() {
    setSavingSource(true)
    const payload: CompanySourcePayload = {
      source_type: 'greenhouse',
      company_name: sourceForm.company_name.trim(),
      board_token: sourceForm.board_token.trim(),
      is_active: sourceForm.is_active,
    }

    const response = editingSourceId
      ? await adminApi.updateCompanySource(editingSourceId, payload)
      : await adminApi.createCompanySource(payload)

    if (response.data) {
      setError(null)
      startCreateSource()
      await loadCompanySources()
    } else {
      setError(response.error || 'Unable to save company source.')
    }
    setSavingSource(false)
  }

  async function deactivateSource(id: string) {
    const response = await adminApi.deactivateCompanySource(id)
    if (response.data) {
      const updated = response.data
      setCompanySources((current) =>
        current.map((source) => (source.id === id ? updated : source))
      )
      setError(null)
      if (editingSourceId === id) {
        startCreateSource()
      }
    } else {
      setError(response.error || 'Unable to deactivate company source.')
    }
  }

  async function syncSource(id: string) {
    setSyncingSourceId(id)
    const response = await adminApi.syncCompanySource(id)
    if (response.data) {
      const run = response.data
      setError(run.status === 'failed' ? run.error_message || 'Source sync failed.' : null)
      await Promise.all([loadCompanySources(), loadSyncRuns()])
    } else {
      setError(response.error || 'Unable to sync company source.')
    }
    setSyncingSourceId(null)
  }

  function startCreateExperience() {
    setEditingExperienceId(null)
    setExperienceForm(emptyExperienceForm)
  }

  function startEditExperience(experience: AdminInterviewExperience) {
    setEditingExperienceId(experience.id)
    setExperienceForm({
      company_name: experience.company_name,
      role: experience.role,
      level: experience.level || '',
      year: experience.year,
      rounds: experience.rounds || '',
      summary: experience.summary,
      source_url: experience.source_url || '',
      source_site: experience.source_site || '',
      review_status: experience.review_status,
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
    <div className="mx-auto max-w-7xl space-y-8">
      <section className="page-shell overflow-hidden p-8 sm:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(26,86,219,0.12),_transparent_36%),radial-gradient(circle_at_right,_rgba(14,159,110,0.07),_transparent_28%)]" />
        <div className="relative flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">Admin Console</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Access and content operations
            </h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
              Manage access, configure Greenhouse job sources, curate the interview library, and control user-facing career content.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/10 bg-primary/5 px-4 py-2 text-sm font-semibold text-primary">
            <Shield className="h-4 w-4" />
            Admin-only route
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-[1.35rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="surface-soft">
          <CardHeader className="pb-2">
            <CardDescription>Total users</CardDescription>
            <CardTitle className="text-3xl">{users.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="surface-soft">
          <CardHeader className="pb-2">
            <CardDescription>Admins</CardDescription>
            <CardTitle className="text-3xl">{adminsCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="surface-soft">
          <CardHeader className="pb-2">
            <CardDescription>Active sources</CardDescription>
            <CardTitle className="text-3xl">{activeSourceCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="surface-soft bg-[linear-gradient(180deg,rgba(26,86,219,0.06),rgba(255,255,255,0.94))]">
          <CardHeader className="pb-2">
            <CardDescription>Interview experiences</CardDescription>
            <CardTitle className="text-3xl">{publishedCount} published</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="border-white/80 bg-white/92">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Database className="h-5 w-5 text-slate-500" />
            <div>
              <CardTitle className="text-xl">Company job sources</CardTitle>
              <CardDescription>
                Configure Greenhouse boards and sync them into the shared opportunities pool.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              <label className="grid gap-2 text-sm text-slate-700">
                Source type
                <select
                  className="input"
                  value={sourceForm.source_type}
                  onChange={(event) =>
                    setSourceForm((current) => ({ ...current, source_type: event.target.value as 'greenhouse' }))
                  }
                >
                  <option value="greenhouse">greenhouse</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Company
                <input
                  className="input"
                  value={sourceForm.company_name}
                  onChange={(event) => setSourceForm((current) => ({ ...current, company_name: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700 md:col-span-2 xl:col-span-1">
                Board token
                <input
                  className="input"
                  value={sourceForm.board_token}
                  onChange={(event) => setSourceForm((current) => ({ ...current, board_token: event.target.value }))}
                />
              </label>
            </div>
            <label className="inline-flex items-center gap-3 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                checked={sourceForm.is_active}
                onChange={(event) => setSourceForm((current) => ({ ...current, is_active: event.target.checked }))}
                className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary"
              />
              Active source
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={() => void saveSource()}
                disabled={savingSource || !sourceForm.company_name.trim() || !sourceForm.board_token.trim()}
              >
                {savingSource ? 'Saving...' : editingSourceId ? 'Save Source' : 'Add Source'}
              </Button>
              <Button variant="outline" onClick={startCreateSource}>
                Reset
              </Button>
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Sources</h3>
                <Button variant="ghost" size="sm" onClick={() => void loadCompanySources()}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh
                </Button>
              </div>
              {loadingSources ? (
                <div className="flex items-center gap-3 py-8 text-sm text-slate-500">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
                  Loading sources...
                </div>
              ) : companySources.length === 0 ? (
                <div className="rounded-[1.5rem] border border-dashed border-slate-200 px-6 py-8 text-center text-sm text-slate-500">
                  No company sources yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {companySources.map((source) => (
                    <div key={source.id} className="surface-soft rounded-[1.5rem] p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-slate-900">{source.company_name}</p>
                            <Badge variant={source.is_active ? 'success' : 'secondary'}>
                              {source.is_active ? 'active' : 'inactive'}
                            </Badge>
                          </div>
                          <p className="mt-1 truncate text-sm text-slate-500">{source.board_token}</p>
                          <p className="mt-2 text-xs text-slate-400">
                            {source.last_synced_at
                              ? `Last synced ${new Date(source.last_synced_at).toLocaleString()}`
                              : 'Never synced'}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2">
                          <Button variant="outline" size="sm" onClick={() => startEditSource(source)}>
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            disabled={!source.is_active || syncingSourceId === source.id}
                            onClick={() => void syncSource(source.id)}
                          >
                            <RefreshCw
                              className={`mr-2 h-4 w-4 ${syncingSourceId === source.id ? 'animate-spin' : ''}`}
                            />
                            {syncingSourceId === source.id ? 'Syncing...' : 'Sync'}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={!source.is_active}
                            onClick={() => void deactivateSource(source.id)}
                          >
                            <Power className="mr-2 h-4 w-4" />
                            Disable
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Sync log</h3>
                <Button variant="ghost" size="sm" onClick={() => void loadSyncRuns()}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh
                </Button>
              </div>
              {loadingSyncRuns ? (
                <div className="flex items-center gap-3 py-8 text-sm text-slate-500">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
                  Loading sync logs...
                </div>
              ) : syncRuns.length === 0 ? (
                <div className="rounded-[1.5rem] border border-dashed border-slate-200 px-6 py-8 text-center text-sm text-slate-500">
                  No sync runs yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {syncRuns.map((run) => (
                    <div key={run.id} className="rounded-[1.5rem] border border-slate-200 bg-white/80 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-900">
                            {run.company_name || run.board_token || run.company_source_id}
                          </p>
                          <p className="text-xs text-slate-400">
                            {run.started_at ? new Date(run.started_at).toLocaleString() : 'Pending'}
                          </p>
                        </div>
                        <Badge
                          variant={
                            run.status === 'success'
                              ? 'success'
                              : run.status === 'failed'
                                ? 'destructive'
                                : 'warning'
                          }
                        >
                          {run.status}
                        </Badge>
                      </div>
                      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-slate-500">
                        <span>{run.fetched_count} fetched</span>
                        <span>{run.upserted_count} upserted</span>
                        <span>{run.closed_count} closed</span>
                      </div>
                      {run.error_message && (
                        <p className="mt-3 line-clamp-3 text-xs leading-5 text-rose-600">{run.error_message}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="border-white/80 bg-white/92">
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
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
                Loading users...
              </div>
            ) : (
              <>
                <div className="space-y-3 lg:hidden">
                  {users.map((user) => {
                    const isSelf = currentUser?.id === user.id
                    const demoteDisabled = isSelf && user.role === 'admin'
                    return (
                      <div key={user.id} className="surface-soft rounded-[1.5rem] p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-slate-900">
                              {user.name || user.email}
                              {isSelf ? ' (You)' : ''}
                            </p>
                            <p className="truncate text-sm text-slate-500">{user.email}</p>
                            <p className="mt-2 text-xs text-slate-400">
                              {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never logged in'}
                            </p>
                          </div>
                          <Badge variant={user.role === 'admin' ? 'success' : 'secondary'}>{user.role}</Badge>
                        </div>
                        <div className="mt-4 flex flex-col items-start gap-2">
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
                      </div>
                    )
                  })}
                </div>

                <div className="hidden overflow-hidden rounded-[1.5rem] border border-slate-200 lg:block">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50/90">
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
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-white/80 bg-white/92">
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
                  className="input"
                  value={experienceForm.company_name}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, company_name: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Role
                <input
                  className="input"
                  value={experienceForm.role}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, role: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Level
                <input
                  className="input"
                  value={experienceForm.level || ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, level: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Year
                <input
                  className="input"
                  type="number"
                  value={experienceForm.year ?? ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, year: event.target.value ? Number(event.target.value) : undefined }))}
                />
              </label>
            </div>

            <label className="grid gap-2 text-sm text-slate-700">
              Interview rounds summary
              <textarea
                className="input min-h-[96px] rounded-[1.5rem] py-3"
                value={experienceForm.rounds || ''}
                onChange={(event) => setExperienceForm((current) => ({ ...current, rounds: event.target.value }))}
              />
            </label>

            <label className="grid gap-2 text-sm text-slate-700">
              Topics
              <input
                className="input"
                placeholder="Algorithms, System Design, Behavioral"
                value={experienceForm.topics_input}
                onChange={(event) => setExperienceForm((current) => ({ ...current, topics_input: event.target.value }))}
              />
            </label>

            <label className="grid gap-2 text-sm text-slate-700">
              Relevance keywords
              <input
                className="input"
                placeholder="backend, platform, distributed systems"
                value={experienceForm.relevance_keywords_input}
                onChange={(event) => setExperienceForm((current) => ({ ...current, relevance_keywords_input: event.target.value }))}
              />
            </label>

            <label className="grid gap-2 text-sm text-slate-700">
              Summary
              <textarea
                className="input min-h-[160px] rounded-[1.5rem] py-3"
                value={experienceForm.summary}
                onChange={(event) => setExperienceForm((current) => ({ ...current, summary: event.target.value }))}
              />
            </label>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="grid gap-2 text-sm text-slate-700 md:col-span-2">
                Source URL
                <input
                  className="input"
                  value={experienceForm.source_url || ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, source_url: event.target.value }))}
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-700">
                Source site
                <input
                  className="input"
                  value={experienceForm.source_site || ''}
                  onChange={(event) => setExperienceForm((current) => ({ ...current, source_site: event.target.value }))}
                />
              </label>
            </div>

            <label className="grid gap-2 text-sm text-slate-700">
              Status
              <select
                className="input"
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

      <Card className="border-white/80 bg-white/92">
        <CardHeader>
          <CardTitle className="text-xl">Interview library</CardTitle>
          <CardDescription>
            Published items will appear in the user-facing Interview Prep page. Drafts stay here until you publish them.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingExperiences ? (
            <div className="flex items-center gap-3 py-8 text-sm text-slate-500">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
              Loading interview experiences...
            </div>
          ) : experiences.length === 0 ? (
            <div className="rounded-[1.5rem] border border-dashed border-slate-200 px-6 py-10 text-center text-sm text-slate-500">
              No interview experiences yet. Create the first one from the form above.
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {experiences.map((experience) => (
                <div key={experience.id} className="surface-soft rounded-[1.5rem] p-5">
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
                  <div className="mt-5 flex items-center justify-between gap-3">
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
