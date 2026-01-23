import { useEffect, useState } from 'react'
import { RefreshCw, ExternalLink, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react'
import { jobsApi, JobResponse } from '../api/client'

export default function Jobs() {
  const [jobs, setJobs] = useState<JobResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastSearch, setLastSearch] = useState<string | null>(null)
  const [expandedJob, setExpandedJob] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  useEffect(() => {
    loadJobs()
  }, [])

  async function loadJobs() {
    setLoading(true)
    const result = await jobsApi.list(0, 20)
    if (result.data) {
      setJobs(result.data.jobs)
      setLastSearch(result.data.last_search)
    }
    setLoading(false)
  }

  async function handleRefresh() {
    setRefreshing(true)
    await jobsApi.refresh()
    // Wait a bit for the background job to start
    setTimeout(() => {
      loadJobs()
      setRefreshing(false)
    }, 2000)
  }

  function toggleExpand(jobId: string) {
    setExpandedJob(expandedJob === jobId ? null : jobId)
  }

  async function copyToClipboard(text: string, jobId: string) {
    await navigator.clipboard.writeText(text)
    setCopiedId(jobId)
    setTimeout(() => setCopiedId(null), 2000)
  }

  function parseSkills(skillsJson: string | undefined): string[] {
    if (!skillsJson) return []
    try {
      return JSON.parse(skillsJson)
    } catch {
      return []
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Matched Jobs</h1>
          {lastSearch && (
            <p className="text-sm text-gray-500 mt-1">
              Last searched: {new Date(lastSearch).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw className={refreshing ? 'animate-spin' : ''} size={18} />
          {refreshing ? 'Searching...' : 'Search Now'}
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500 mb-4">No matched jobs yet.</p>
          <p className="text-sm text-gray-400">
            Click "Search Now" to find jobs matching your profile.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <div key={job.id} className="card">
              {/* Job Header */}
              <div className="flex items-start gap-4">
                {/* Match Score */}
                <div
                  className={`flex-shrink-0 w-16 h-16 rounded-xl flex flex-col items-center justify-center ${
                    job.match_score >= 80
                      ? 'bg-green-100 text-green-700'
                      : job.match_score >= 60
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  <span className="text-xl font-bold">{job.match_score}</span>
                  <span className="text-xs">Match</span>
                </div>

                {/* Job Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 text-lg">{job.title}</h3>
                  <p className="text-gray-600">{job.company}</p>
                  <div className="flex flex-wrap gap-2 mt-2 text-sm text-gray-500">
                    {job.location && <span>{job.location}</span>}
                    {job.salary && (
                      <>
                        <span>•</span>
                        <span>{job.salary}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex-shrink-0 flex gap-2">
                  {job.url && (
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-primary flex items-center gap-2"
                    >
                      Apply
                      <ExternalLink size={16} />
                    </a>
                  )}
                  <button
                    onClick={() => toggleExpand(job.id)}
                    className="btn-secondary flex items-center gap-1"
                  >
                    Details
                    {expandedJob === job.id ? (
                      <ChevronUp size={16} />
                    ) : (
                      <ChevronDown size={16} />
                    )}
                  </button>
                </div>
              </div>

              {/* Expanded Details */}
              {expandedJob === job.id && (
                <div className="mt-6 pt-6 border-t border-gray-200 space-y-6">
                  {/* Match Reason */}
                  {job.match_reason && (
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Why You Match</h4>
                      <p className="text-gray-600">{job.match_reason}</p>
                    </div>
                  )}

                  {/* Skills */}
                  <div className="grid grid-cols-2 gap-4">
                    {/* Matched Skills */}
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Matched Skills</h4>
                      <div className="flex flex-wrap gap-2">
                        {parseSkills(job.matched_skills).map((skill, i) => (
                          <span
                            key={i}
                            className="px-2 py-1 bg-green-100 text-green-700 text-sm rounded"
                          >
                            {skill}
                          </span>
                        ))}
                        {parseSkills(job.matched_skills).length === 0 && (
                          <span className="text-gray-400 text-sm">None identified</span>
                        )}
                      </div>
                    </div>

                    {/* Missing Skills */}
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Skills to Develop</h4>
                      <div className="flex flex-wrap gap-2">
                        {parseSkills(job.missing_skills).map((skill, i) => (
                          <span
                            key={i}
                            className="px-2 py-1 bg-orange-100 text-orange-700 text-sm rounded"
                          >
                            {skill}
                          </span>
                        ))}
                        {parseSkills(job.missing_skills).length === 0 && (
                          <span className="text-gray-400 text-sm">None - you're a great fit!</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Cover Letter */}
                  {job.cover_letter && (
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <h4 className="font-medium text-gray-900">Generated Cover Letter</h4>
                        <button
                          onClick={() => copyToClipboard(job.cover_letter!, job.id)}
                          className="text-primary-600 hover:text-primary-700 flex items-center gap-1 text-sm"
                        >
                          {copiedId === job.id ? (
                            <>
                              <Check size={16} />
                              Copied!
                            </>
                          ) : (
                            <>
                              <Copy size={16} />
                              Copy
                            </>
                          )}
                        </button>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <p className="text-gray-700 whitespace-pre-wrap text-sm">
                          {job.cover_letter}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
