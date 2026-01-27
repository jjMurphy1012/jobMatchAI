import { motion } from 'framer-motion'
import { Copy, Check, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useState } from 'react'
import { JobResponse } from '../../api/client'

interface JobDetailsProps {
  job: JobResponse
}

export function JobDetails({ job }: JobDetailsProps) {
  const [copied, setCopied] = useState(false)

  const copyToClipboard = async () => {
    if (job.cover_letter) {
      await navigator.clipboard.writeText(job.cover_letter)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
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
          <div className="relative bg-indigo-50/50 rounded-xl p-5 border border-indigo-100/50">
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

        {/* Cover Letter Section */}
        {job.cover_letter && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-slate-800 text-sm">AI Generated Cover Letter</h4>
              <button
                onClick={copyToClipboard}
                className="flex items-center gap-1.5 text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors bg-primary-50 px-3 py-1.5 rounded-lg"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </button>
            </div>
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-primary-100 to-indigo-100 rounded-2xl blur opacity-30 group-hover:opacity-50 transition duration-500"></div>
              <div className="relative bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <p className="text-slate-600 text-sm whitespace-pre-wrap leading-relaxed font-mono">
                  {job.cover_letter}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
