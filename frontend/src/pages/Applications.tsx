import { useCallback, useEffect, useState } from 'react'
import { Download, Link2, MapPin, Pencil, Plus, PlusCircle, Search, Trash2 } from 'lucide-react'

import {
  APPLICATION_JOB_TYPE_LABELS,
  APPLICATION_REGION_LABELS,
  APPLICATION_STATUS_LABELS,
  ApplicationJobType,
  ApplicationListParams,
  ApplicationRecord,
  ApplicationRegion,
  ApplicationStatus,
  applicationsApi,
} from '../api/client'
import { ApplicationEventModal } from '../components/applications/ApplicationEventModal'
import { ApplicationFormModal } from '../components/applications/ApplicationFormModal'
import { Button } from '../components/ui/button'

type StageFilter = ApplicationStatus | 'all'
type TypeFilter = ApplicationJobType | 'all'
type RegionFilter = ApplicationRegion | 'all'
type SearchField = 'company' | 'role'

const stageOrder: StageFilter[] = ['all', 'applied', 'assessment', 'interviewing', 'offer', 'rejected', 'saved']
const typeOrder: TypeFilter[] = ['all', 'internship', 'full_time', 'new_grad', 'contract']
const regionOrder: RegionFilter[] = [
  'all',
  'us',
  'uk',
  'canada',
  'australia',
  'hong_kong',
  'mainland_china',
  'singapore',
  'other',
]

/** Matches the reference layout's date style, e.g. 2026.07.22 */
function formatStamp(value?: string) {
  if (!value) return null
  const [year, month, day] = value.slice(0, 10).split('-')
  return `${year}.${month}.${day}`
}

/** The most recent event of a kind — the cell the stage columns render. */
function latestEvent(application: ApplicationRecord, kind: 'applied' | 'assessment' | 'interview') {
  const matching = application.events
    .filter((event) => event.kind === kind)
    .sort((a, b) => a.occurred_on.localeCompare(b.occurred_on))
  return matching.length ? matching[matching.length - 1] : undefined
}

function FilterRow<T extends string>({
  options,
  value,
  onChange,
  label,
  counts,
}: {
  options: T[]
  value: T
  onChange: (next: T) => void
  label: (option: T) => string
  counts?: Partial<Record<string, number>>
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-1 gap-y-2">
      {options.map((option) => {
        const isActive = value === option
        const count = counts?.[option]
        return (
          <button
            key={option}
            onClick={() => onChange(option)}
            className={
              isActive
                ? 'rounded-lg bg-primary/10 px-3 py-1.5 text-sm font-semibold text-primary'
                : 'rounded-lg px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100'
            }
          >
            {label(option)}
            {count !== undefined && <span className="ml-1 text-slate-400">({count})</span>}
          </button>
        )
      })}
    </div>
  )
}

export default function Applications() {
  const [applications, setApplications] = useState<ApplicationRecord[]>([])
  const [statusCounts, setStatusCounts] = useState<Partial<Record<ApplicationStatus, number>>>({})
  const [stage, setStage] = useState<StageFilter>('all')
  const [jobType, setJobType] = useState<TypeFilter>('all')
  const [region, setRegion] = useState<RegionFilter>('all')
  const [searchField, setSearchField] = useState<SearchField>('company')
  const [search, setSearch] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<ApplicationRecord | undefined>(undefined)
  const [eventTarget, setEventTarget] = useState<ApplicationRecord | undefined>(undefined)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const filters: ApplicationListParams = {
    status: stage === 'all' ? undefined : stage,
    job_type: jobType === 'all' ? undefined : jobType,
    region: region === 'all' ? undefined : region,
    search: appliedSearch || undefined,
    search_field: searchField,
  }

  const load = useCallback(async () => {
    setLoading(true)
    const response = await applicationsApi.list({
      status: stage === 'all' ? undefined : stage,
      job_type: jobType === 'all' ? undefined : jobType,
      region: region === 'all' ? undefined : region,
      search: appliedSearch || undefined,
      search_field: searchField,
    })
    if (response.data) {
      setApplications(response.data.applications)
      setStatusCounts(response.data.status_counts)
      setError(null)
    } else {
      setError(response.error || 'Unable to load your applications.')
    }
    setLoading(false)
  }, [stage, jobType, region, appliedSearch, searchField])

  useEffect(() => {
    void load()
  }, [load])

  const total = Object.values(statusCounts).reduce((sum, count) => sum + count, 0)
  const stageCounts: Partial<Record<string, number>> = { ...statusCounts, all: total }

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

  const columns: { kind: 'applied' | 'assessment' | 'interview'; header: string }[] = [
    { kind: 'applied', header: 'Applied / Referral' },
    { kind: 'assessment', header: 'OA / Assessment' },
    { kind: 'interview', header: 'Interview' },
  ]

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Applications</h1>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => {
              setEditing(undefined)
              setFormOpen(true)
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New application
          </Button>
          <a href={applicationsApi.exportUrl(filters)} download>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export CSV
            </Button>
          </a>
        </div>
      </div>

      <div className="page-shell space-y-4 p-6">
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            setAppliedSearch(search.trim())
          }}
        >
          <select
            className="input w-auto"
            value={searchField}
            onChange={(event) => setSearchField(event.target.value as SearchField)}
          >
            <option value="company">Company</option>
            <option value="role">Role</option>
          </select>
          <div className="relative min-w-[220px] flex-1">
            <input
              className="input pr-10"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Type to search"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </button>
          </div>
        </form>

        <div className="space-y-1 border-t border-slate-100 pt-3">
          <FilterRow
            options={stageOrder}
            value={stage}
            onChange={setStage}
            counts={stageCounts}
            label={(option) => (option === 'all' ? 'All stages' : APPLICATION_STATUS_LABELS[option])}
          />
          <FilterRow
            options={typeOrder}
            value={jobType}
            onChange={setJobType}
            label={(option) => (option === 'all' ? 'All types' : APPLICATION_JOB_TYPE_LABELS[option])}
          />
          <FilterRow
            options={regionOrder}
            value={region}
            onChange={setRegion}
            label={(option) => (option === 'all' ? 'All regions' : APPLICATION_REGION_LABELS[option])}
          />
        </div>

        {error && (
          <p className="rounded-xl border border-rose-100 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
            {error}
          </p>
        )}

        {loading ? (
          <div className="flex items-center gap-3 py-12 text-sm text-slate-500">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
            Loading applications...
          </div>
        ) : applications.length === 0 ? (
          <div className="rounded-[1.25rem] border border-dashed border-slate-200 px-6 py-14 text-center">
            <p className="text-sm font-medium text-slate-700">No applications match these filters.</p>
            <p className="mt-1 text-sm text-slate-500">
              Add one here, or open a match and choose “I applied — track it”.
            </p>
          </div>
        ) : (
          <>
            {/* Desktop: the stage-per-column table from the reference layout. */}
            <div className="hidden overflow-x-auto rounded-[1rem] border border-slate-200 lg:block">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50/90">
                  <tr className="text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    <th className="px-4 py-3">Company · Region</th>
                    <th className="px-4 py-3">Role</th>
                    {columns.map((column) => (
                      <th key={column.kind} className="px-4 py-3">
                        {column.header}
                      </th>
                    ))}
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white/70">
                  {applications.map((application) => (
                    <tr key={application.id} className="align-top">
                      <td className="px-4 py-4">
                        <p className="font-medium text-slate-900">{application.company_name}</p>
                        <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                          <MapPin className="h-3 w-3" />
                          {application.location ||
                            (application.region ? APPLICATION_REGION_LABELS[application.region] : '—')}
                        </p>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-start gap-1.5">
                          <span className="text-slate-700">{application.job_title}</span>
                          {application.job_url && (
                            <a
                              href={application.job_url}
                              target="_blank"
                              rel="noreferrer"
                              className="mt-0.5 text-primary hover:text-primary/80"
                              aria-label="Open job posting"
                            >
                              <Link2 className="h-3.5 w-3.5" />
                            </a>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-slate-400">
                          {[
                            application.job_type ? APPLICATION_JOB_TYPE_LABELS[application.job_type] : null,
                            application.season,
                          ]
                            .filter(Boolean)
                            .join(' | ') || '—'}
                        </p>
                      </td>
                      {columns.map((column) => {
                        const event = latestEvent(application, column.kind)
                        return (
                          <td key={column.kind} className="px-4 py-4 text-slate-600">
                            {event ? (
                              <span>
                                {formatStamp(event.occurred_on)}
                                {event.label && <span className="ml-1.5 text-slate-500">{event.label}</span>}
                              </span>
                            ) : (
                              <span className="text-slate-300">–</span>
                            )}
                          </td>
                        )
                      })}
                      <td className="px-4 py-4">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => {
                              setEditing(application)
                              setFormOpen(true)
                            }}
                            className="rounded-md p-1.5 text-primary transition-colors hover:bg-primary/10"
                            aria-label="Edit application"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => setEventTarget(application)}
                            className="rounded-md p-1.5 text-emerald-600 transition-colors hover:bg-emerald-50"
                            aria-label="Add stage"
                          >
                            <PlusCircle className="h-4 w-4" />
                          </button>
                          <button
                            disabled={deletingId === application.id}
                            onClick={() => void remove(application)}
                            className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"
                            aria-label="Delete application"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: the same fields stacked, since the table cannot fit. */}
            <div className="space-y-3 lg:hidden">
              {applications.map((application) => (
                <div key={application.id} className="surface-soft rounded-[1.25rem] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">{application.company_name}</p>
                      <p className="truncate text-sm text-slate-600">{application.job_title}</p>
                      <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                        <MapPin className="h-3 w-3" />
                        {application.location ||
                          (application.region ? APPLICATION_REGION_LABELS[application.region] : '—')}
                      </p>
                    </div>
                    <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary">
                      {APPLICATION_STATUS_LABELS[application.status]}
                    </span>
                  </div>

                  <dl className="mt-3 space-y-1 text-xs text-slate-500">
                    {columns.map((column) => {
                      const event = latestEvent(application, column.kind)
                      return (
                        <div key={column.kind} className="flex justify-between gap-3">
                          <dt>{column.header}</dt>
                          <dd className={event ? 'text-slate-700' : 'text-slate-300'}>
                            {event
                              ? `${formatStamp(event.occurred_on)}${event.label ? ` ${event.label}` : ''}`
                              : '–'}
                          </dd>
                        </div>
                      )
                    })}
                  </dl>

                  <div className="mt-4 flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditing(application)
                        setFormOpen(true)
                      }}
                    >
                      <Pencil className="mr-2 h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setEventTarget(application)}>
                      <PlusCircle className="mr-2 h-3.5 w-3.5" />
                      Add stage
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
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <ApplicationFormModal
        open={formOpen}
        application={editing}
        onClose={() => setFormOpen(false)}
        onSaved={() => void load()}
      />

      <ApplicationEventModal
        application={eventTarget}
        onClose={() => setEventTarget(undefined)}
        onSaved={() => void load()}
      />
    </div>
  )
}
