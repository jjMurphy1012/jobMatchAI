import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, Pencil, Plus, RefreshCw, Search, Trash2 } from 'lucide-react'

import {
  APPLICATION_JOB_TYPE_LABELS,
  APPLICATION_STATUS_LABELS,
  ApplicationChannel,
  ApplicationRecord,
  ApplicationStatus,
  applicationsApi,
} from '../api/client'
import { ApplicationFormModal } from '../components/applications/ApplicationFormModal'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

type StageFilter = ApplicationStatus | 'all'

// Tab order is a product decision; the labels come from the shared map.
const stageOrder: StageFilter[] = ['all', 'applied', 'assessment', 'interviewing', 'offer', 'rejected', 'saved']

function stageLabel(stage: StageFilter) {
  return stage === 'all' ? 'All' : APPLICATION_STATUS_LABELS[stage]
}

function statusBadgeVariant(status: ApplicationStatus): 'success' | 'warning' | 'destructive' | 'secondary' {
  if (status === 'offer') return 'success'
  if (status === 'interviewing' || status === 'assessment') return 'warning'
  if (status === 'rejected' || status === 'withdrawn') return 'destructive'
  return 'secondary'
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleDateString() : '—'
}

export default function Applications() {
  const [applications, setApplications] = useState<ApplicationRecord[]>([])
  const [statusCounts, setStatusCounts] = useState<Partial<Record<ApplicationStatus, number>>>({})
  const [stage, setStage] = useState<StageFilter>('all')
  const [channel, setChannel] = useState<ApplicationChannel | 'all'>('all')
  const [search, setSearch] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ApplicationRecord | undefined>(undefined)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    const response = await applicationsApi.list({
      status: stage === 'all' ? undefined : stage,
      channel: channel === 'all' ? undefined : channel,
      search: appliedSearch || undefined,
    })
    if (response.data) {
      setApplications(response.data.applications)
      setStatusCounts(response.data.status_counts)
      setError(null)
    } else {
      setError(response.error || 'Unable to load your applications.')
    }
    setLoading(false)
  }, [stage, channel, appliedSearch])

  useEffect(() => {
    void load()
  }, [load])

  const total = Object.values(statusCounts).reduce((sum, count) => sum + count, 0)
  const offerCount = statusCounts.offer ?? 0
  const activeCount =
    (statusCounts.applied ?? 0) + (statusCounts.assessment ?? 0) + (statusCounts.interviewing ?? 0)

  function openCreate() {
    setEditing(undefined)
    setModalOpen(true)
  }

  function openEdit(application: ApplicationRecord) {
    setEditing(application)
    setModalOpen(true)
  }

  function handleSaved() {
    // Stage counts and ordering both come from the server, so refetch rather
    // than trying to reconcile the list locally.
    void load()
  }

  async function remove(application: ApplicationRecord) {
    if (!window.confirm(`Delete your application to ${application.company_name}?`)) return
    setDeletingId(application.id)
    const response = await applicationsApi.remove(application.id)
    if (response.error) {
      setError(response.error)
    } else {
      void load()
    }
    setDeletingId(null)
  }

  return (
    <div className="space-y-6">
      <section className="page-shell overflow-hidden p-8 sm:p-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Applications</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Every job you have applied to, whether it came from a match or you added it yourself.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <p className="text-3xl font-semibold text-slate-900">{total}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Tracked</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-slate-900">{activeCount}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">In progress</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-emerald-600">{offerCount}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Offers</p>
            </div>
          </div>
        </div>
      </section>

      <Card className="border-white/80 bg-white/92">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-xl">Your pipeline</CardTitle>
              <CardDescription>Filter by stage, then update where each one stands.</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => void load()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
              <Button onClick={openCreate}>
                <Plus className="mr-2 h-4 w-4" />
                Add application
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="flex flex-wrap gap-2">
            {stageOrder.map((tab) => {
              const count = tab === 'all' ? total : statusCounts[tab] ?? 0
              const isActive = stage === tab
              return (
                <button
                  key={tab}
                  onClick={() => setStage(tab)}
                  className={
                    isActive
                      ? 'rounded-full bg-primary px-4 py-1.5 text-sm font-semibold text-white'
                      : 'rounded-full bg-slate-100 px-4 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-200'
                  }
                >
                  {stageLabel(tab)}
                  <span className={isActive ? 'ml-2 text-white/80' : 'ml-2 text-slate-400'}>{count}</span>
                </button>
              )
            })}
          </div>

          <form
            className="flex flex-wrap items-center gap-3"
            onSubmit={(event) => {
              event.preventDefault()
              setAppliedSearch(search.trim())
            }}
          >
            <div className="relative min-w-[240px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                className="input pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search company or title"
              />
            </div>
            <select
              className="input w-auto"
              value={channel}
              onChange={(event) => setChannel(event.target.value as ApplicationChannel | 'all')}
            >
              <option value="all">All channels</option>
              <option value="online">Online</option>
              <option value="referral">Referral</option>
            </select>
            <Button type="submit" variant="outline">
              Search
            </Button>
          </form>

          {error && (
            <p className="rounded-xl border border-rose-100 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
              {error}
            </p>
          )}

          {loading ? (
            <div className="flex items-center gap-3 py-10 text-sm text-slate-500">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
              Loading applications...
            </div>
          ) : applications.length === 0 ? (
            <div className="rounded-[1.5rem] border border-dashed border-slate-200 px-6 py-12 text-center">
              <p className="text-sm font-medium text-slate-700">Nothing here yet.</p>
              <p className="mt-1 text-sm text-slate-500">
                Add one manually, or open a match and choose “I applied — track it”.
              </p>
              <Button className="mt-4" onClick={openCreate}>
                <Plus className="mr-2 h-4 w-4" />
                Add application
              </Button>
            </div>
          ) : (
            <>
              <div className="space-y-3 lg:hidden">
                {applications.map((application) => (
                  <div key={application.id} className="surface-soft rounded-[1.5rem] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-900">{application.company_name}</p>
                        <p className="truncate text-sm text-slate-600">{application.job_title}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          {application.location || 'Location not set'} · {formatDate(application.applied_at)}
                        </p>
                      </div>
                      <Badge variant={statusBadgeVariant(application.status)}>
                        {APPLICATION_STATUS_LABELS[application.status]}
                      </Badge>
                    </div>
                    <div className="mt-4 flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => openEdit(application)}>
                        <Pencil className="mr-2 h-3.5 w-3.5" />
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deletingId === application.id}
                        onClick={() => void remove(application)}
                      >
                        <Trash2 className="mr-2 h-3.5 w-3.5" />
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="hidden overflow-hidden rounded-[1.5rem] border border-slate-200 lg:block">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50/90">
                    <tr className="text-left text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                      <th className="px-4 py-3">Company</th>
                      <th className="px-4 py-3">Role</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Channel</th>
                      <th className="px-4 py-3">Applied</th>
                      <th className="px-4 py-3">Stage</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white/70">
                    {applications.map((application) => (
                      <tr key={application.id}>
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-900">{application.company_name}</p>
                          <p className="text-xs text-slate-400">{application.location || '—'}</p>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-slate-700">{application.job_title}</span>
                            {application.job_url && (
                              <a
                                href={application.job_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-primary hover:text-primary/80"
                                aria-label="Open job posting"
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                              </a>
                            )}
                          </div>
                          {application.season && (
                            <p className="text-xs text-slate-400">{application.season}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {application.job_type ? APPLICATION_JOB_TYPE_LABELS[application.job_type] : '—'}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {application.channel === 'referral' ? 'Referral' : 'Online'}
                        </td>
                        <td className="px-4 py-3 text-slate-600">{formatDate(application.applied_at)}</td>
                        <td className="px-4 py-3">
                          <Badge variant={statusBadgeVariant(application.status)}>
                            {APPLICATION_STATUS_LABELS[application.status]}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="outline" size="sm" onClick={() => openEdit(application)}>
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={deletingId === application.id}
                              onClick={() => void remove(application)}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <ApplicationFormModal
        open={modalOpen}
        application={editing}
        onClose={() => setModalOpen(false)}
        onSaved={handleSaved}
      />
    </div>
  )
}
