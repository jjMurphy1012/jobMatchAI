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
    <div className="mx-auto max-w-6xl space-y-8">
      <section className="page-shell overflow-hidden p-8 sm:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(26,86,219,0.12),_transparent_36%),radial-gradient(circle_at_right,_rgba(14,159,110,0.08),_transparent_28%)]" />
        <div className="relative flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">Interview Prep</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Relevant interview experiences
            </h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
              Curated big-tech interview notes ranked against your current matches and career profile, so prep time goes to the companies and roles you actually care about.
            </p>
          </div>
          <Button variant="outline" className="gap-2" size="lg" onClick={() => void loadExperiences()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="surface-soft">
          <CardHeader className="pb-2">
            <CardDescription>Curated notes</CardDescription>
            <CardTitle className="text-3xl">{experiences.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="surface-soft">
          <CardHeader className="pb-2">
            <CardDescription>Company-matched</CardDescription>
            <CardTitle className="text-3xl">{experiences.filter((item) => item.matched_company).length}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="surface-soft bg-[linear-gradient(180deg,rgba(26,86,219,0.06),rgba(255,255,255,0.94))]">
          <CardHeader className="pb-2">
            <CardDescription>Ranking model</CardDescription>
            <CardTitle className="text-base leading-relaxed">
              Company overlap first, profile keywords second.
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {error && (
        <div className="rounded-[1.35rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="surface-soft h-64 animate-pulse rounded-[1.75rem]" />
          ))}
        </div>
      ) : experiences.length === 0 ? (
        <Card className="page-shell py-16">
          <CardContent className="flex flex-col items-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
              <BookOpen className="h-8 w-8" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-slate-900">No interview prep yet</h2>
              <p className="max-w-xl text-sm leading-6 text-slate-600">
                Once interview experiences are added to the system, this page will rank and show the ones most relevant to your target roles and matched companies.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {experiences.map((experience) => (
            <Card key={experience.id} className="overflow-hidden border-white/80 bg-white/92">
              <CardHeader className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={experience.matched_company ? 'success' : 'secondary'}>
                    {experience.company_name}
                  </Badge>
                  {experience.level && <Badge variant="outline">{experience.level}</Badge>}
                  {experience.year && <Badge variant="outline">{experience.year}</Badge>}
                  <Badge variant="default" className="bg-primary/10 text-primary hover:bg-primary/15">
                    score {experience.relevance_score}
                  </Badge>
                </div>
                <div>
                  <CardTitle className="text-xl text-slate-900">{experience.role}</CardTitle>
                  <CardDescription className="mt-2">
                    {experience.matched_company ? 'This company already appears in your current matches.' : 'Ranked from profile overlap and prep relevance.'}
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {experience.rounds && (
                  <div className="rounded-[1.4rem] border border-primary/10 bg-primary/5 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-medium text-primary">
                      <Sparkles className="h-4 w-4" />
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
