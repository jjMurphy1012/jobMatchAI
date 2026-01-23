import { useEffect, useState } from 'react'
import { CheckCircle, Circle, ExternalLink, PartyPopper } from 'lucide-react'
import { tasksApi, DailyTask, TaskStatsResponse } from '../api/client'

export default function Dashboard() {
  const [tasks, setTasks] = useState<DailyTask[]>([])
  const [stats, setStats] = useState<TaskStatsResponse | null>(null)
  const [allCompleted, setAllCompleted] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    const [tasksRes, statsRes] = await Promise.all([
      tasksApi.list(),
      tasksApi.stats(),
    ])

    if (tasksRes.data) {
      setTasks(tasksRes.data.tasks)
      setAllCompleted(tasksRes.data.all_completed)
    }
    if (statsRes.data) {
      setStats(statsRes.data)
    }
    setLoading(false)
  }

  async function toggleTask(taskId: string, isCompleted: boolean) {
    const api = isCompleted ? tasksApi.uncomplete : tasksApi.complete
    const result = await api(taskId)

    if (result.data) {
      // Reload data to get updated state
      loadData()

      // Check for celebration
      if ('all_completed' in result.data && result.data.all_completed) {
        setAllCompleted(true)
      }
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
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Today's Tasks</h1>
      <p className="text-gray-600 mb-8">Apply to at least 10 jobs today!</p>

      {/* Progress Bar */}
      {stats && (
        <div className="card mb-8">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm text-gray-600">
              {stats.today_completed} / {stats.today_total} completed
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-primary-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${stats.completion_rate}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Celebration Message */}
      {allCompleted && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-8 flex items-center gap-4">
          <PartyPopper className="text-green-600" size={32} />
          <div>
            <h3 className="text-lg font-semibold text-green-800">
              Today's tasks completed!
            </h3>
            <p className="text-green-700">Great job! Keep up the momentum.</p>
          </div>
        </div>
      )}

      {/* Task List */}
      <div className="space-y-4">
        {tasks.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-gray-500 mb-4">No tasks for today yet.</p>
            <p className="text-sm text-gray-400">
              Upload your resume and set preferences to get started.
            </p>
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className={`card flex items-center gap-4 transition-all ${
                task.is_completed ? 'bg-green-50 border-green-200' : ''
              }`}
            >
              {/* Checkbox */}
              <button
                onClick={() => toggleTask(task.id, task.is_completed)}
                className="flex-shrink-0"
              >
                {task.is_completed ? (
                  <CheckCircle className="text-green-600" size={24} />
                ) : (
                  <Circle className="text-gray-400 hover:text-primary-600" size={24} />
                )}
              </button>

              {/* Job Info */}
              <div className="flex-1 min-w-0">
                <h3
                  className={`font-medium ${
                    task.is_completed ? 'text-green-800 line-through' : 'text-gray-900'
                  }`}
                >
                  {task.job.title}
                </h3>
                <p className="text-sm text-gray-600 truncate">
                  {task.job.company} • {task.job.location || 'Remote'}
                </p>
              </div>

              {/* Match Score */}
              <div className="flex-shrink-0 text-center">
                <div
                  className={`text-lg font-bold ${
                    task.job.match_score >= 80
                      ? 'text-green-600'
                      : task.job.match_score >= 60
                      ? 'text-yellow-600'
                      : 'text-gray-600'
                  }`}
                >
                  {task.job.match_score}%
                </div>
                <div className="text-xs text-gray-500">Match</div>
              </div>

              {/* Apply Link */}
              {task.job.url && (
                <a
                  href={task.job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 btn-primary flex items-center gap-2"
                >
                  Apply
                  <ExternalLink size={16} />
                </a>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
