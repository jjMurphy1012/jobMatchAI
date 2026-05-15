import { motion } from 'framer-motion'
import { Copy, Check, Sparkles, AlertCircle, CheckCircle2, Loader2, ExternalLink, BookOpen } from 'lucide-react'
import { useState } from 'react'
import { JobResponse, jobsApi } from '../../api/client'

interface JobDetailsProps {
  job: JobResponse
  onCoverLetterGenerated?: (jobId: string, coverLetter: string) => void
}

export function JobDetails({ job, onCoverLetterGenerated }: JobDetailsProps) {
  const [copied, setCopied] = useState(false)
  const [coverLetter, setCoverLetter] = useState(job.cover_letter || '')
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState('')

  const copyToClipboard = async () => {
    if (coverLetter) {
      await navigator.clipboard.writeText(coverLetter)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const generateCoverLetter = async () => {
    setIsGenerating(true)
    setError('')
    try {
      const result = await jobsApi.generateCoverLetter(job.id)
      if (result.error || !result.data) {
        throw new Error(result.error || 'Unable to generate cover letter')
      }
      setCoverLetter(result.data.cover_letter)
      onCoverLetterGenerated?.(job.id, result.data.cover_letter)
    } catch (err: any) {
      setError(err.message || 'Unable to generate cover letter')
    } finally {
      setIsGenerating(false)
    }
  }

  const parseSkills = (skillsJson: string | undefined): string[] => {
    if (!skillsJson) return []
    try {
      return JSON.parse(skillsJson)
    } catch {
      return []
    }
  }

  const matchedSkills = parseSkills(job.matched_skills)
  const missingSkills = parseSkills(job.missing_skills)
  const relatedInterviews = job.related_interviews ?? []

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="overflow-hidden"
    >
      <div className="pt-6 mt-6 border-t border-slate-100 space-y-8">
        
        {/* Why You Match Section */}
        {job.match_reason && (
          <div className="relative rounded-[1.4rem] border border-primary/10 bg-primary/5 p-5">
            <div className="flex items-center gap-2 mb-3 text-indigo-900 font-semibold">
              <Sparkles className="w-4 h-4 text-indigo-500" />
              <h4>Why It's a Match</h4>
            </div>
            <p className="text-slate-700 leading-relaxed text-sm">
              {job.match_reason}
            </p>
          </div>
        )}

        {/* Skills Analysis */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Matched Skills */}
          <div>
            <div className="flex items-center gap-2 mb-4 text-emerald-800 font-medium text-sm">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Your Strengths</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {matchedSkills.length > 0 ? (
                matchedSkills.map((skill, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-lg border border-emerald-100/50"
                  >
                    {skill}
                  </span>
                ))
              ) : (
                <span className="text-slate-400 text-sm italic">No specific skills listed</span>
              )}
            </div>
          </div>

          {/* Missing Skills */}
          <div>
            <div className="flex items-center gap-2 mb-4 text-amber-800 font-medium text-sm">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              <span>Skills to Develop</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {missingSkills.length > 0 ? (
                missingSkills.map((skill, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 bg-amber-50 text-amber-700 text-xs font-medium rounded-lg border border-amber-100/50"
                  >
                    {skill}
                  </span>
                ))
              ) : (
                <span className="text-slate-400 text-sm italic">You match all required skills!</span>
              )}
            </div>
          </div>
        </div>

        {relatedInterviews.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <BookOpen className="h-4 w-4 text-primary" />
              <h4>Related Interview Prep</h4>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {relatedInterviews.map((experience) => (
                <div key={experience.id} className="rounded-[1.25rem] border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary">
                      {experience.company_name}
                    </span>
                    {experience.level && (
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                        {experience.level}
                      </span>
                    )}
                    {experience.year && (
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                        {experience.year}
                      </span>
                    )}
                  </div>
                  <h5 className="mt-3 text-sm font-semibold text-slate-900">{experience.role}</h5>
                  <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-600">{experience.summary}</p>
                  {experience.topics.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {experience.topics.slice(0, 3).map((topic) => (
                        <span key={topic} className="rounded-full bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700">
                          {topic}
                        </span>
                      ))}
                    </div>
                  )}
                  {(experience.source_url || experience.source_site) && (
                    <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
                      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                        {experience.source_site || 'Source'}
                      </span>
                      {experience.source_url && (
                        <a
                          href={experience.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary/80"
                        >
                          Open
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cover Letter Section */}
        <div className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h4 className="font-semibold text-slate-800 text-sm">AI Generated Cover Letter</h4>
            {coverLetter ? (
              <button
                onClick={copyToClipboard}
                className="inline-flex items-center justify-center gap-1.5 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/15"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </button>
            ) : (
              <button
                onClick={generateCoverLetter}
                disabled={isGenerating}
                className="inline-flex items-center justify-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isGenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                {isGenerating ? 'Generating...' : 'Generate'}
              </button>
            )}
          </div>
          {error && (
            <p className="rounded-xl border border-rose-100 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
              {error}
            </p>
          )}
          {coverLetter && (
            <div className="relative group">
              <div className="absolute -inset-0.5 rounded-[1.5rem] bg-gradient-to-r from-primary/15 to-emerald-200/40 blur opacity-40 transition duration-500 group-hover:opacity-60"></div>
              <div className="relative rounded-[1.35rem] border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-slate-600 text-sm whitespace-pre-wrap leading-relaxed font-mono">
                  {coverLetter}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
