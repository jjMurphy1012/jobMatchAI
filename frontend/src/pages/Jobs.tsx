import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Search } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { jobsApi } from '../api/client'
import { JobCard } from '../components/jobs/JobCard'
import { JobDetails } from '../components/jobs/JobDetails'
import { Button } from '../components/ui/button'

export default function Jobs() {
  const [expandedJob, setExpandedJob] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Data Fetching
  const { data, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list(0, 50),
    staleTime: 1000 * 60 * 5, // 5 minutes cache
  })

  // Refresh Mutation
  const refreshMutation = useMutation({
    mutationFn: jobsApi.refresh,
    onSuccess: (result) => {
      if (result.error) {
        alert(`Search failed: ${result.error}. Please try again later.`)
        return
      }

      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      const jobsFound = result.data?.jobs_found ?? 0
      alert(`Search complete. The AI found ${jobsFound} matched position${jobsFound === 1 ? '' : 's'}.`)
    },
    onError: (error: any) => {
      console.error('Search failed:', error)
      alert(`Failed to start search: ${error.message || 'Unknown error'}. Please try again later.`)
    }
  })

  const toggleExpand = (jobId: string) => {
    setExpandedJob(expandedJob === jobId ? null : jobId)
  }

  const jobs = data?.data?.jobs || []
  const lastSearch = data?.data?.last_search

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <section className="page-shell overflow-hidden p-8 sm:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(26,86,219,0.12),_transparent_36%),radial-gradient(circle_at_right,_rgba(14,159,110,0.08),_transparent_28%)]" />
        <div className="relative flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">Matches</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Run Match whenever you want a fresh set of roles.
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
              We combine your resume, career profile, and recent signals only when you explicitly trigger a new search.
            </p>
            {lastSearch && (
              <p className="mt-3 text-sm font-medium text-slate-500">
                Last updated: {new Date(lastSearch).toLocaleString()}
              </p>
            )}
          </div>

          <Button
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            className="gap-2.5"
            size="lg"
          >
            <RefreshCw
              className={`h-5 w-5 ${refreshMutation.isPending ? 'animate-spin' : ''}`}
            />
            {refreshMutation.isPending ? 'Running Match...' : 'Run Match'}
          </Button>
        </div>
      </section>

      <div className="relative min-h-[400px]">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 rounded-[1.75rem] border border-white/80 bg-white/70 animate-pulse shadow-sm" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="page-shell flex flex-col items-center justify-center py-20 text-center"
          >
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 text-primary mb-6">
              <Search className="h-10 w-10" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-2">No matches yet</h3>
            <p className="max-w-sm text-slate-500 mb-8">
              Upload your resume, complete your Career Profile, then click Run Match to generate your first set of recommended roles.
            </p>
            <Button onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
              Run Match
            </Button>
          </motion.div>
        ) : (
          <div className="space-y-4">
            <AnimatePresence mode="popLayout">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  isExpanded={expandedJob === job.id}
                  onToggleExpand={() => toggleExpand(job.id)}
                >
                  <JobDetails job={job} />
                </JobCard>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
