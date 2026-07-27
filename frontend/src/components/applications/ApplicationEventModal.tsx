import { useEffect, useState } from 'react'
import { Trash2, X } from 'lucide-react'

import {
  APPLICATION_EVENT_LABELS,
  ApplicationEventKind,
  ApplicationRecord,
  applicationsApi,
} from '../../api/client'
import { Button } from '../ui/button'

interface ApplicationEventModalProps {
  /** The application to add a stage to; undefined keeps the modal closed. */
  application?: ApplicationRecord
  onClose: () => void
  onSaved: () => void
}

const kindOptions = Object.entries(APPLICATION_EVENT_LABELS) as [ApplicationEventKind, string][]

/** Suggested labels per stage, so the row reads like the reference layout. */
const labelSuggestions: Partial<Record<ApplicationEventKind, string>> = {
  assessment: 'Online Test',
  interview: 'Round 1',
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

export function ApplicationEventModal({ application, onClose, onSaved }: ApplicationEventModalProps) {
  const [kind, setKind] = useState<ApplicationEventKind>('assessment')
  const [occurredOn, setOccurredOn] = useState(today())
  const [label, setLabel] = useState(labelSuggestions.assessment ?? '')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!application) return
    setKind('assessment')
    setOccurredOn(today())
    setLabel(labelSuggestions.assessment ?? '')
    setNote('')
    setError(null)
  }, [application])

  if (!application) return null

  function selectKind(next: ApplicationEventKind) {
    setKind(next)
    setLabel(labelSuggestions[next] ?? '')
  }

  async function save() {
    if (!application) return
    setSaving(true)
    setError(null)

    const response = await applicationsApi.addEvent(application.id, {
      kind,
      occurred_on: occurredOn,
      label: label.trim() || undefined,
      note: note.trim() || undefined,
    })

    if (response.data) {
      onSaved()
      onClose()
    } else {
      setError(response.error || 'Unable to record this stage.')
    }
    setSaving(false)
  }

  async function removeEvent(eventId: string) {
    if (!application) return
    const response = await applicationsApi.removeEvent(application.id, eventId)
    if (response.error) {
      setError(response.error)
    } else {
      onSaved()
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-[1.75rem] bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold text-slate-900">Add a stage</h2>
            <p className="mt-1 truncate text-sm text-slate-500">
              {application.company_name} · {application.job_title}
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

        <div className="mt-6 space-y-4">
          <label className="block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Stage</span>
            <select
              className="input"
              value={kind}
              onChange={(event) => selectKind(event.target.value as ApplicationEventKind)}
            >
              {kindOptions.map(([value, text]) => (
                <option key={value} value={value}>
                  {text}
                </option>
              ))}
            </select>
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Date</span>
              <input
                type="date"
                className="input"
                value={occurredOn}
                onChange={(event) => setOccurredOn(event.target.value)}
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Label</span>
              <input
                className="input"
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                placeholder="Online Test, Round 1..."
              />
            </label>
          </div>

          <label className="block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Note</span>
            <textarea
              className="input min-h-[72px]"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Interviewer, topics, follow-up..."
            />
          </label>
        </div>

        {application.events.length > 0 && (
          <div className="mt-6 space-y-2 border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Timeline</p>
            {application.events.map((event) => (
              <div key={event.id} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-600">
                  {event.occurred_on} · {APPLICATION_EVENT_LABELS[event.kind]}
                  {event.label ? ` · ${event.label}` : ''}
                </span>
                <button
                  onClick={() => void removeEvent(event.id)}
                  className="rounded-md p-1 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
                  aria-label="Remove stage"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

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
            {saving ? 'Saving...' : 'Add stage'}
          </Button>
        </div>
      </div>
    </div>
  )
}
