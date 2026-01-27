import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Search } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { jobsApi } from '../api/client'
import { JobCard } from '../components/jobs/JobCard'
import { JobDetails } from '../components/jobs/JobDetails'

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
    onSuccess: () => {
      // Invalidate and refetch jobs after a short delay to allow backend to process
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['jobs'] })
      }, 2000)
      
      // Simple feedback for the user
      alert("Search started! The AI is now scanning for new positions. This might take a few moments.")
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
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700 pb-1">
            Matched Opportunities
          </h1>
          <p className="text-slate-500 mt-2 text-lg">
            AI-curated positions based on your profile
          </p>
          {lastSearch && (
            <p className="text-sm text-slate-400 mt-1 font-medium">
              Last updated: {new Date(lastSearch).toLocaleString()}
            </p>
          )}
        </div>

        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="btn-primary flex items-center gap-2.5 shadow-indigo-500/25"
        >
          <RefreshCw 
            className={`w-5 h-5 ${refreshMutation.isPending ? 'animate-spin' : ''}`} 
          />
          {refreshMutation.isPending ? 'Analyzing Market...' : 'Run New Search'}
        </button>
      </div>

      {/* Content Area */}
      <div className="relative min-h-[400px]">
        {isLoading ? (
          // Skeleton Loading State
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 rounded-2xl bg-white/40 animate-pulse border border-white/50" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          // Empty State
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center py-20 bg-white/50 backdrop-blur-sm rounded-3xl border border-dashed border-slate-300"
          >
            <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-6">
              <Search className="w-10 h-10 text-slate-400" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-2">No jobs found yet</h3>
            <p className="text-slate-500 max-w-sm text-center mb-8">
              Click "Run New Search" to let our AI scan the market for positions matching your resume.
            </p>
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              className="px-6 py-3 bg-white text-primary-600 border border-primary-200 rounded-xl font-medium hover:bg-primary-50 transition-colors"
            >
              Start Search
            </button>
          </motion.div>
        ) : (
          // Job List
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

