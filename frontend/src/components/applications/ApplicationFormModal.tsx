import { useEffect, useState } from 'react'
import { X } from 'lucide-react'

import {
  APPLICATION_JOB_TYPE_LABELS,
  APPLICATION_REGION_LABELS,
  APPLICATION_STATUS_LABELS,
  ApplicationChannel,
  ApplicationCreatePayload,
  ApplicationJobType,
  ApplicationRecord,
  ApplicationRegion,
  ApplicationStatus,
  applicationsApi,
} from '../../api/client'
import { Button } from '../ui/button'

export interface ApplicationDraft {
  user_job_match_id?: string
  company_name: string
  job_title: string
  location: string
  job_url: string
  job_type: ApplicationJobType | ''
  region: ApplicationRegion | ''
  season: string
  channel: ApplicationChannel
  status: ApplicationStatus
  applied_on: string
  notes: string
}

interface ApplicationFormModalProps {
  open: boolean
  /** Present when editing an existing record; absent when creating. */
  application?: ApplicationRecord
  /** Pre-filled values, e.g. copied from a matched job. */
  draft?: Partial<ApplicationDraft>
  onClose: () => void
  onSaved: (application: ApplicationRecord) => void
}

const statusOptions = Object.entries(APPLICATION_STATUS_LABELS) as [ApplicationStatus, string][]
const regionOptions = Object.entries(APPLICATION_REGION_LABELS) as [ApplicationRegion, string][]
const jobTypeOptions = Object.entries(APPLICATION_JOB_TYPE_LABELS) as [ApplicationJobType, string][]

function today() {
  return new Date().toISOString().slice(0, 10)
}

function emptyDraft(): ApplicationDraft {
  return {
    company_name: '',
    job_title: '',
    location: '',
    job_url: '',
    job_type: '',
    region: '',
    season: String(new Date().getFullYear()),
    channel: 'online',
    status: 'applied',
    applied_on: today(),
    notes: '',
  }
}

function draftFromRecord(record: ApplicationRecord): ApplicationDraft {
  return {
    company_name: record.company_name,
    job_title: record.job_title,
    location: record.location || '',
    job_url: record.job_url || '',
    job_type: record.job_type || '',
    region: record.region || '',
    season: record.season || '',
    channel: record.channel,
    status: record.status,
    applied_on: record.applied_at ? record.applied_at.slice(0, 10) : '',
    notes: record.notes || '',
  }
}

export function ApplicationFormModal({
  open,
  application,
  draft,
  onClose,
  onSaved,
}: ApplicationFormModalProps) {
  const [form, setForm] = useState<ApplicationDraft>(emptyDraft())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setForm(application ? draftFromRecord(application) : { ...emptyDraft(), ...draft })
    // Seeds the form when the modal opens. `draft` is intentionally not a
    // dependency: it is an object literal at the call site, so a parent
    // re-render would otherwise discard whatever the user has typed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, application])

  if (!open) return null

  const update = (patch: Partial<ApplicationDraft>) => setForm((current) => ({ ...current, ...patch }))

  async function save() {
    if (!form.company_name.trim() || !form.job_title.trim()) {
      setError('Company and job title are required.')
      return
    }

    setSaving(true)
    setError(null)

    const payload: ApplicationCreatePayload = {
      company_name: form.company_name.trim(),
      job_title: form.job_title.trim(),
      location: form.location.trim() || undefined,
      job_url: form.job_url.trim() || undefined,
      job_type: form.job_type || undefined,
      region: form.region || undefined,
      season: form.season.trim() || undefined,
      channel: form.channel,
      status: form.status,
      applied_at: form.applied_on ? new Date(form.applied_on).toISOString() : undefined,
      notes: form.notes.trim() || undefined,
    }

    const response = application
      ? await applicationsApi.update(application.id, payload)
      : await applicationsApi.create({ ...payload, user_job_match_id: form.user_job_match_id })

    if (response.data) {
      onSaved(response.data)
      onClose()
    } else {
      setError(response.error || 'Unable to save this application.')
    }
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[1.75rem] bg-white p-6 shadow-xl sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              {application ? 'Edit application' : 'Track an application'}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {form.user_job_match_id
                ? 'Details are copied from the matched job — just confirm the date and channel.'
                : 'Record a job you applied to, whether or not it came from a match.'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Company *</span>
            <input
              className="input"
              value={form.company_name}
              onChange={(event) => update({ company_name: event.target.value })}
              placeholder="Acme"
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Job title *</span>
            <input
              className="input"
              value={form.job_title}
              onChange={(event) => update({ job_title: event.target.value })}
              placeholder="Backend Engineer"
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Location</span>
            <input
              className="input"
              value={form.location}
              onChange={(event) => update({ location: event.target.value })}
              placeholder="Boston, MA"
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Job type</span>
            <select
              className="input"
              value={form.job_type}
              onChange={(event) => update({ job_type: event.target.value as ApplicationJobType | '' })}
            >
              <option value="">Not specified</option>
              {jobTypeOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Region</span>
            <select
              className="input"
              value={form.region}
              onChange={(event) => update({ region: event.target.value as ApplicationRegion | '' })}
            >
              <option value="">Infer from location</option>
              {regionOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Applied on</span>
            <input
              type="date"
              className="input"
              value={form.applied_on}
              onChange={(event) => update({ applied_on: event.target.value })}
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Season</span>
            <input
              className="input"
              value={form.season}
              onChange={(event) => update({ season: event.target.value })}
              placeholder="2026"
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Stage</span>
            <select
              className="input"
              value={form.status}
              onChange={(event) => update({ status: event.target.value as ApplicationStatus })}
            >
              {statusOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <div className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Channel</span>
            <div className="flex items-center gap-4 pt-2">
              {(['online', 'referral'] as ApplicationChannel[]).map((value) => (
                <label key={value} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="radio"
                    name="channel"
                    checked={form.channel === value}
                    onChange={() => update({ channel: value })}
                  />
                  {value === 'online' ? 'Online' : 'Referral'}
                </label>
              ))}
            </div>
          </div>

          <label className="space-y-1.5 sm:col-span-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Job link</span>
            <input
              className="input"
              value={form.job_url}
              onChange={(event) => update({ job_url: event.target.value })}
              placeholder="https://"
            />
          </label>

          <label className="space-y-1.5 sm:col-span-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notes</span>
            <textarea
              className="input min-h-[96px]"
              value={form.notes}
              onChange={(event) => update({ notes: event.target.value })}
              placeholder="Referrer, recruiter contact, next step..."
            />
          </label>
        </div>

        {error && (
          <p className="mt-4 rounded-xl border border-rose-100 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={() => void save()} disabled={saving}>
            {saving ? 'Saving...' : application ? 'Save changes' : 'Add application'}
          </Button>
        </div>
      </div>
    </div>
  )
}
