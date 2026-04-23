import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AlertCircle, Loader2, RefreshCw, Save, Sparkles, Wand2, X } from 'lucide-react'

import {
  preferencesApi,
  PreferenceFields,
  PreferenceOverrideFields,
  PreferenceResponse,
} from '../api/client'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { cn } from '../lib/utils'

const emptyFields: PreferenceFields = {
  keywords: [],
  locations: [],
  is_intern: false,
  need_sponsor: false,
  experience_level: undefined,
  remote_preference: undefined,
  excluded_companies: [],
  industries: [],
  salary_min: undefined,
  salary_max: undefined,
  salary_currency: 'USD',
}

const profilePlaceholder = `I'm looking for mid-level backend roles in New York or remote. I need H1B sponsorship, prefer product-focused teams, and want to work on Go, Python, distributed systems, or platform engineering. Please avoid companies like Meta, and target compensation around $180k+.`

export default function Preferences() {
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [autosaving, setAutosaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [rawText, setRawText] = useState('')
  const [overrideFields, setOverrideFields] = useState<PreferenceOverrideFields>({})
  const [effectiveFields, setEffectiveFields] = useState<PreferenceFields>(emptyFields)
  const [reminderEnabled, setReminderEnabled] = useState(true)
  const [reminderEmail, setReminderEmail] = useState('')
  const [preferenceId, setPreferenceId] = useState<string | null>(null)
  const [usedFallback, setUsedFallback] = useState(false)

  const hydratedRef = useRef(false)
  const suppressAutosaveRef = useRef(true)
  const saveTimeoutRef = useRef<number | null>(null)

  const hasProfile = Boolean(preferenceId)
  const canAnalyze = rawText.trim().length >= 10

  const profileSummary = useMemo(() => {
    const locations = effectiveFields.locations.join(' / ') || 'Any location'
    const keywords = effectiveFields.keywords.slice(0, 4).join(', ') || 'Open-ended search'
    return `${keywords} • ${locations}`
  }, [effectiveFields])

  useEffect(() => {
    loadPreferences()
    return () => {
      if (saveTimeoutRef.current) {
        window.clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!hydratedRef.current || !preferenceId) {
      return
    }

    if (suppressAutosaveRef.current) {
      suppressAutosaveRef.current = false
      return
    }

    if (saveTimeoutRef.current) {
      window.clearTimeout(saveTimeoutRef.current)
    }

    saveTimeoutRef.current = window.setTimeout(async () => {
      setAutosaving(true)
      setError(null)

      const result = await preferencesApi.patchFields({
        override_fields: overrideFields,
        reminder_enabled: reminderEnabled,
        reminder_email: reminderEmail || undefined,
      })

      if (result.error) {
        setError(result.error)
      } else if (result.data) {
        syncPreference(result.data)
        setMessage('AI tags updated')
      }

      setAutosaving(false)
    }, 600)

    return () => {
      if (saveTimeoutRef.current) {
        window.clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [overrideFields, reminderEnabled, reminderEmail, preferenceId])

  async function loadPreferences() {
    setLoading(true)
    setError(null)

    const result = await preferencesApi.get()
    if (result.data) {
      syncPreference(result.data)
    } else {
      setRawText('')
      setOverrideFields({})
      setEffectiveFields(emptyFields)
    }

    hydratedRef.current = true
    setLoading(false)
  }

  function syncPreference(preference: PreferenceResponse) {
    suppressAutosaveRef.current = true
    setPreferenceId(preference.id)
    setRawText(preference.raw_text || '')
    setOverrideFields(preference.override_fields || {})
    setEffectiveFields(preference.effective_fields)
    setReminderEnabled(preference.reminder_enabled)
    setReminderEmail(preference.reminder_email || '')
    setUsedFallback(false)
  }

  async function handleAnalyzeAndSave() {
    if (!canAnalyze) {
      setError('Please describe your search in a bit more detail before analyzing.')
      return
    }

    setAnalyzing(true)
    setError(null)
    setMessage(null)

    const analysisResult = await preferencesApi.analyze(rawText)
    if (analysisResult.error || !analysisResult.data) {
      setError(analysisResult.error || 'Failed to analyze your profile')
      setAnalyzing(false)
      return
    }

    const extracted = analysisResult.data.extracted_fields
    setUsedFallback(analysisResult.data.used_fallback)

    const saveResult = await preferencesApi.save({
      raw_text: rawText,
      extracted_fields: extracted,
      override_fields: overrideFields,
      reminder_enabled: reminderEnabled,
      reminder_email: reminderEmail || undefined,
    })

    if (saveResult.error || !saveResult.data) {
      setError(saveResult.error || 'Failed to save your profile')
      setAnalyzing(false)
      return
    }

    syncPreference(saveResult.data)
    setMessage('Profile analyzed and saved')
    setAnalyzing(false)
  }

  function updateArrayField(field: keyof Pick<PreferenceFields, 'keywords' | 'locations' | 'excluded_companies' | 'industries'>, values: string[]) {
    setOverrideFields((current) => ({ ...current, [field]: values }))
    setEffectiveFields((current) => ({ ...current, [field]: values }))
  }

  function updateEnumField(field: 'experience_level' | 'remote_preference', value: PreferenceOverrideFields['experience_level'] | PreferenceOverrideFields['remote_preference']) {
    setOverrideFields((current) => ({ ...current, [field]: value }))
    setEffectiveFields((current) => ({ ...current, [field]: value as any }))
  }

  function updateBoolField(field: 'is_intern' | 'need_sponsor', value: boolean) {
    setOverrideFields((current) => ({ ...current, [field]: value }))
    setEffectiveFields((current) => ({ ...current, [field]: value }))
  }

  function updateNumberField(field: 'salary_min' | 'salary_max', value: string) {
    const normalized = value ? Number(value) : null
    setOverrideFields((current) => ({ ...current, [field]: normalized }))
    setEffectiveFields((current) => ({ ...current, [field]: normalized ?? undefined }))
  }

  function updateCurrency(value: string) {
    const normalized = value || null
    setOverrideFields((current) => ({ ...current, salary_currency: normalized }))
    setEffectiveFields((current) => ({ ...current, salary_currency: normalized ?? undefined }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-primary" size={28} />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <section className="page-shell overflow-hidden p-8 lg:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(26,86,219,0.12),_transparent_40%),radial-gradient(circle_at_right,_rgba(14,159,110,0.08),_transparent_28%)]" />
        <div className="relative grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/10 bg-primary/5 px-3 py-1 text-sm font-medium text-primary">
              <Sparkles size={16} />
              Career Profile
            </div>
            <div className="space-y-3">
              <h1 className="text-3xl lg:text-4xl font-semibold tracking-tight text-slate-900">
                Tell the system what kind of job you actually want.
              </h1>
              <p className="text-slate-600 text-base leading-7 max-w-2xl">
                Write naturally, in English or Chinese. Describe role scope, location, seniority,
                sponsorship, industries, compensation, and anything you want to avoid.
              </p>
            </div>

            <div className="rounded-[1.75rem] border border-white/80 bg-white/92 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
              <textarea
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
                className="min-h-[260px] w-full resize-none rounded-2xl border-0 bg-transparent p-3 text-[15px] leading-7 text-slate-800 outline-none placeholder:text-slate-400"
                placeholder={profilePlaceholder}
              />
              <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
                  <Badge variant="secondary" className="rounded-full bg-slate-100 text-slate-700">
                    {rawText.trim().length} chars
                  </Badge>
                  {hasProfile && (
                    <Badge variant="outline" className="rounded-full border-slate-300 text-slate-600">
                      {profileSummary}
                    </Badge>
                  )}
                  {usedFallback && (
                    <Badge variant="warning" className="rounded-full">
                      Heuristic fallback used
                    </Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button
                    variant="outline"
                    className="rounded-xl"
                    onClick={handleAnalyzeAndSave}
                    disabled={analyzing || !canAnalyze}
                  >
                    {analyzing ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />}
                    Reanalyze
                  </Button>
                  <Button
                    className="rounded-xl shadow-lg shadow-primary/20"
                    onClick={handleAnalyzeAndSave}
                    disabled={analyzing || !canAnalyze}
                  >
                    {analyzing ? <Loader2 className="animate-spin" size={16} /> : <Wand2 size={16} />}
                    Analyze and Save
                  </Button>
                </div>
              </div>
            </div>

            {(error || message) && (
              <div
                className={cn(
                  'rounded-2xl border px-4 py-3 text-sm',
                  error
                    ? 'border-red-200 bg-red-50 text-red-700'
                    : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                )}
              >
                <div className="flex items-center gap-2">
                  {error ? <AlertCircle size={16} /> : <Save size={16} />}
                  <span>{error || message}</span>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-4">
            <Card className="rounded-[24px] border-white/80 bg-[linear-gradient(180deg,#374151_0%,#2b3445_100%)] text-white shadow-[0_24px_60px_-35px_rgba(15,23,42,0.55)]">
              <CardHeader className="space-y-3">
                <CardDescription className="text-slate-400">What the system sees</CardDescription>
                <CardTitle className="text-2xl text-white">Structured profile</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-slate-300">
                <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3">
                  <span>Autosave</span>
                  <span className="font-medium text-white">{autosaving ? 'Syncing...' : 'Active'}</span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <StatCard label="Keywords" value={String(effectiveFields.keywords.length)} />
                  <StatCard label="Locations" value={String(effectiveFields.locations.length)} />
                  <StatCard label="Companies Excluded" value={String(effectiveFields.excluded_companies.length)} />
                  <StatCard label="Industries" value={String(effectiveFields.industries.length)} />
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Active Filters</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {effectiveFields.need_sponsor && <MiniPill>Needs sponsorship</MiniPill>}
                    {effectiveFields.is_intern && <MiniPill>Intern only</MiniPill>}
                    {effectiveFields.remote_preference && <MiniPill>{effectiveFields.remote_preference}</MiniPill>}
                    {effectiveFields.experience_level && <MiniPill>{effectiveFields.experience_level}</MiniPill>}
                    {!effectiveFields.need_sponsor && !effectiveFields.is_intern && !effectiveFields.remote_preference && !effectiveFields.experience_level && (
                      <span className="text-slate-500">No hard filters yet</span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="border-white/80 bg-white/92">
          <CardHeader>
            <CardDescription>Editable AI interpretation</CardDescription>
            <CardTitle className="text-2xl text-slate-900">Signals extracted from your note</CardTitle>
          </CardHeader>
          <CardContent className="space-y-7">
            <TagEditor
              label="Role Keywords"
              description="These are the terms used for search and matching."
              values={effectiveFields.keywords}
              onChange={(values) => updateArrayField('keywords', values)}
            />
            <TagEditor
              label="Locations"
              description="Use explicit cities or Remote."
              values={effectiveFields.locations}
              onChange={(values) => updateArrayField('locations', values)}
            />
            <TagEditor
              label="Excluded Companies"
              description="Keep companies you do not want surfaced."
              values={effectiveFields.excluded_companies}
              onChange={(values) => updateArrayField('excluded_companies', values)}
            />
            <TagEditor
              label="Industries"
              description="Optional industry bias for future Greenhouse filtering."
              values={effectiveFields.industries}
              onChange={(values) => updateArrayField('industries', values)}
            />

            <div className="grid gap-6 md:grid-cols-2">
              <OptionGroup
                label="Experience Level"
                options={[
                  { label: 'Entry', value: 'entry' },
                  { label: 'Mid', value: 'mid' },
                  { label: 'Senior', value: 'senior' },
                ]}
                value={effectiveFields.experience_level || null}
                onChange={(value) => updateEnumField('experience_level', value as PreferenceOverrideFields['experience_level'])}
              />
              <OptionGroup
                label="Work Style"
                options={[
                  { label: 'Remote', value: 'remote' },
                  { label: 'Hybrid', value: 'hybrid' },
                  { label: 'Onsite', value: 'onsite' },
                ]}
                value={effectiveFields.remote_preference || null}
                onChange={(value) => updateEnumField('remote_preference', value as PreferenceOverrideFields['remote_preference'])}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <ToggleRow
                label="Internship only"
                description="Hard-filter to intern roles."
                checked={effectiveFields.is_intern}
                onChange={(checked) => updateBoolField('is_intern', checked)}
              />
              <ToggleRow
                label="Need sponsorship"
                description="Keep H1B / visa sponsor signal explicit."
                checked={effectiveFields.need_sponsor}
                onChange={(checked) => updateBoolField('need_sponsor', checked)}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <LabeledNumberInput
                label="Salary Min"
                value={effectiveFields.salary_min}
                onChange={(value) => updateNumberField('salary_min', value)}
              />
              <LabeledNumberInput
                label="Salary Max"
                value={effectiveFields.salary_max}
                onChange={(value) => updateNumberField('salary_max', value)}
              />
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Currency</label>
                <select
                  value={effectiveFields.salary_currency || ''}
                  onChange={(event) => updateCurrency(event.target.value)}
                  className="input h-11 rounded-2xl"
                >
                  <option value="">Unset</option>
                  <option value="USD">USD</option>
                  <option value="CNY">CNY</option>
                  <option value="EUR">EUR</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-white/80 bg-white/92">
            <CardHeader>
              <CardDescription>Notifications</CardDescription>
              <CardTitle className="text-2xl text-slate-900">Reminder Email</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ToggleRow
                label="Daily reminders"
                description="Keep email nudges enabled for this profile."
                checked={reminderEnabled}
                onChange={setReminderEnabled}
              />
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Email address</label>
                <input
                  value={reminderEmail}
                  onChange={(event) => setReminderEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="input h-11 rounded-2xl"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/80 bg-[linear-gradient(180deg,rgba(26,86,219,0.05),rgba(255,255,255,0.98))]">
            <CardHeader>
              <CardDescription>How it works</CardDescription>
              <CardTitle className="text-2xl text-slate-900">Profile loop</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-slate-600 leading-6">
              <p>1. Write naturally about the job you want.</p>
              <p>2. The backend extracts structured signals for filtering and scoring.</p>
              <p>3. You correct chips instead of rewriting a rigid form.</p>
              <p>4. Future Greenhouse syncing will use these exact signals for pre-filtering.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
    </div>
  )
}

function MiniPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-white">
      {children}
    </span>
  )
}

function TagEditor({
  label,
  description,
  values,
  onChange,
}: {
  label: string
  description: string
  values: string[]
  onChange: (values: string[]) => void
}) {
  const [draft, setDraft] = useState('')

  function addDraft() {
    const value = draft.trim()
    if (!value) {
      return
    }

    onChange([...values, value])
    setDraft('')
  }

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-semibold text-slate-900">{label}</h3>
        <p className="text-sm text-slate-500">{description}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {values.length === 0 && (
          <span className="rounded-full border border-dashed border-slate-300 px-3 py-1 text-xs text-slate-500">
            Nothing captured yet
          </span>
        )}
        {values.map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => onChange(values.filter((item) => item !== value))}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
          >
            {value}
            <X size={14} />
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              addDraft()
            }
          }}
          className="input h-11 rounded-2xl"
          placeholder={`Add ${label.toLowerCase()}`}
        />
        <Button variant="outline" className="rounded-2xl" onClick={addDraft}>
          Add
        </Button>
      </div>
    </div>
  )
}

function OptionGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: Array<{ label: string; value: string }>
  value: string | null
  onChange: (value: string | null) => void
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-700">{label}</label>
        <button type="button" className="text-xs text-slate-500 hover:text-slate-700" onClick={() => onChange(null)}>
          Clear
        </button>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'rounded-2xl border px-4 py-3 text-sm font-medium transition',
              value === option.value
                ? 'border-primary bg-primary/8 text-primary'
                : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={cn(
        'flex items-start justify-between gap-4 rounded-3xl border p-4 text-left transition',
        checked
          ? 'border-primary/30 bg-primary/5'
          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
      )}
    >
      <div>
        <p className="font-medium text-slate-900">{label}</p>
        <p className="text-sm text-slate-500 mt-1">{description}</p>
      </div>
      <div
        className={cn(
          'mt-1 flex h-6 w-11 items-center rounded-full p-1 transition',
          checked ? 'bg-primary' : 'bg-slate-200'
        )}
      >
        <span
          className={cn(
            'h-4 w-4 rounded-full bg-white transition',
            checked ? 'translate-x-5' : 'translate-x-0'
          )}
        />
      </div>
    </button>
  )
}

function LabeledNumberInput({
  label,
  value,
  onChange,
}: {
  label: string
  value?: number
  onChange: (value: string) => void
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-slate-700">{label}</label>
      <input
        type="number"
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
        className="input h-11 rounded-2xl"
        placeholder="Optional"
      />
    </div>
  )
}
