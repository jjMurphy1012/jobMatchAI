import { useEffect, useState } from 'react'
import { BookOpen, ExternalLink, RefreshCw, Sparkles } from 'lucide-react'

import { interviewExperiencesApi, InterviewExperience } from '../api/client'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

export default function InterviewPrep() {
  const [experiences, setExperiences] = useState<InterviewExperience[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void loadExperiences()
  }, [])

  async function loadExperiences() {
    setLoading(true)
    setError(null)
    const response = await interviewExperiencesApi.list(12)
    if (response.data) {
      setExperiences(response.data)
    } else {
      setError(response.error || 'Unable to load interview prep right now.')
    }
    setLoading(false)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-indigo-600">Interview Prep</p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Relevant interview experiences</h1>
          <p className="mt-2 max-w-3xl text-slate-600">
            This section prioritizes big-tech interview notes that overlap with your current matches and career profile, so you can prep against companies and roles you actually care about.
          </p>
        </div>
        <Button variant="outline" className="gap-2" onClick={() => void loadExperiences()} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Curated notes</CardDescription>
            <CardTitle>{experiences.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Company-matched</CardDescription>
            <CardTitle>{experiences.filter((item) => item.matched_company).length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>How it works</CardDescription>
            <CardTitle className="text-base leading-relaxed">
              Company overlap first, profile keywords second.
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-56 animate-pulse rounded-3xl border border-slate-200 bg-white/80" />
          ))}
        </div>
      ) : experiences.length === 0 ? (
        <Card className="py-16">
          <CardContent className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
              <BookOpen className="h-7 w-7 text-slate-500" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-slate-900">No interview prep yet</h2>
              <p className="max-w-xl text-sm text-slate-600">
                Once interview experiences are added to the system, this page will rank and show the ones most relevant to your target roles and matched companies.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {experiences.map((experience) => (
            <Card key={experience.id} className="overflow-hidden border-slate-200/80 bg-white/90">
              <CardHeader className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={experience.matched_company ? 'success' : 'secondary'}>
                    {experience.company_name}
                  </Badge>
                  {experience.level && <Badge variant="outline">{experience.level}</Badge>}
                  {experience.year && <Badge variant="outline">{experience.year}</Badge>}
                </div>
                <div>
                  <CardTitle className="text-xl text-slate-900">{experience.role}</CardTitle>
                  <CardDescription className="mt-1">
                    relevance score {experience.relevance_score}
                    {experience.matched_company ? ' • company already appears in your matches' : ''}
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {experience.rounds && (
                  <div className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-indigo-900">
                      <Sparkles className="h-4 w-4 text-indigo-500" />
                      Interview flow
                    </div>
                    <p className="text-sm leading-relaxed text-slate-700">{experience.rounds}</p>
                  </div>
                )}

                <p className="text-sm leading-7 text-slate-700">{experience.summary}</p>

                {experience.topics.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {experience.topics.map((topic) => (
                      <Badge key={topic} variant="warning">
                        {topic}
                      </Badge>
                    ))}
                  </div>
                )}

                {(experience.source_url || experience.source_site) && (
                  <div className="flex items-center justify-between border-t border-slate-100 pt-4">
                    <span className="text-xs uppercase tracking-[0.2em] text-slate-400">
                      {experience.source_site || 'Source'}
                    </span>
                    {experience.source_url ? (
                      <a
                        href={experience.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary/80"
                      >
                        Open source
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    ) : null}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
