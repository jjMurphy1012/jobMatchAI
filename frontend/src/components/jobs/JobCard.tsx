import { motion } from 'framer-motion'
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import { JobResponse } from '../../api/client'

interface JobCardProps {
  job: JobResponse
  isExpanded: boolean
  onToggleExpand: () => void
  children?: React.ReactNode
}

export function JobCard({ job, isExpanded, onToggleExpand, children }: JobCardProps) {
  const getMatchColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600 bg-emerald-50 ring-emerald-500/30'
    if (score >= 60) return 'text-amber-600 bg-amber-50 ring-amber-500/30'
    return 'text-slate-500 bg-slate-50 ring-slate-500/30'
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={`group relative overflow-hidden rounded-2xl border transition-all duration-300 ${
        isExpanded 
          ? 'bg-white/80 border-primary-200 shadow-xl shadow-primary-900/5' 
          : 'bg-white/60 border-white/50 hover:bg-white/90 hover:border-white hover:shadow-lg hover:shadow-indigo-500/10'
      } backdrop-blur-sm`}
    >
      <div className="p-6">
        <div className="flex items-start gap-5">
          {/* Match Score */}
          <div className={`flex-shrink-0 flex flex-col items-center justify-center w-20 h-20 rounded-2xl ring-1 ${getMatchColor(job.match_score)} transition-colors`}>
            <span className="text-2xl font-bold tracking-tight">{job.match_score}</span>
            <span className="text-[10px] uppercase font-medium tracking-wider opacity-80">Match</span>
          </div>

          {/* Job Info */}
          <div className="flex-1 min-w-0 py-1">
            <h3 className="text-xl font-bold text-slate-800 group-hover:text-primary-700 transition-colors truncate">
              {job.title}
            </h3>
            <p className="text-slate-500 font-medium mt-1">{job.company}</p>
            
            <div className="flex flex-wrap gap-3 mt-3">
              {job.location && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 text-xs font-medium border border-slate-200">
                  {job.location}
                </span>
              )}
              {job.salary && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-100">
                  {job.salary}
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2 pt-1">
            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-primary-50 text-primary-600 hover:bg-primary-600 hover:text-white transition-all duration-300"
                title="Apply Now"
              >
                <ExternalLink size={18} />
              </a>
            )}
            <button
              onClick={onToggleExpand}
              className={`inline-flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 ${
                isExpanded 
                  ? 'bg-slate-100 text-slate-900' 
                  : 'bg-white text-slate-400 border border-slate-200 hover:border-slate-300 hover:text-slate-600'
              }`}
              title="View Details"
            >
              {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
          </div>
        </div>

        {/* Expanded Content using Framer Motion via children */}
        {children}
      </div>
    </motion.div>
  )
}
