import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, Circle, ExternalLink, PartyPopper, Briefcase, TrendingUp } from 'lucide-react'
import { tasksApi, DailyTask, TaskStatsResponse } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Progress } from '../components/ui/progress'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { cn } from '../lib/utils'

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
      loadData()
      const data = result.data as any
      if (data.all_completed) {
        setAllCompleted(true)
      }
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header & Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Daily Goal
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.today_completed || 0} / {stats?.today_total || 10}</div>
            <p className="text-xs text-muted-foreground">
              Applications sent today
            </p>
            <div className="mt-4">
              <Progress value={stats?.completion_rate || 0} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Opportunities
            </CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tasks.length}</div>
            <p className="text-xs text-muted-foreground">
              Jobs matched for you today
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Celebration Message */}
      {allCompleted && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-green-50 border border-green-200 rounded-xl p-6 flex items-center gap-4 text-green-800"
        >
          <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
            <PartyPopper className="text-green-600" size={24} />
          </div>
          <div>
            <h3 className="font-semibold text-lg">Daily Goal Achieved!</h3>
            <p className="text-green-700">You're on fire! Keeping this streak up will increase your chances significantly.</p>
          </div>
        </motion.div>
      )}

      {/* Task List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold tracking-tight">Today's Matches</h2>
        </div>

        {tasks.length === 0 ? (
          <Card className="py-12 flex flex-col items-center justify-center text-center">
            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
              <Briefcase className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-lg">No matches found yet</h3>
            <p className="text-muted-foreground max-w-sm mt-2">
              We're analyzing the job market for you. Make sure your resume and preferences are up to date.
            </p>
          </Card>
        ) : (
          <motion.div 
            variants={container}
            initial="hidden"
            animate="show"
            className="grid gap-4"
          >
            {tasks.map((task) => (
              <motion.div key={task.id} variants={item}>
                <Card className={cn(
                  "transition-all duration-200 hover:shadow-md",
                  task.is_completed && "bg-muted/50 border-muted"
                )}>
                  <div className="p-6 flex items-start gap-4">
                    {/* Checkbox */}
                    <button
                      onClick={() => toggleTask(task.id, task.is_completed)}
                      className="mt-1 flex-shrink-0"
                    >
                      {task.is_completed ? (
                        <CheckCircle className="text-green-600 h-6 w-6" />
                      ) : (
                        <Circle className="text-muted-foreground hover:text-primary h-6 w-6 transition-colors" />
                      )}
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0 grid gap-1">
                      <div className="flex items-center justify-between">
                        <h3 className={cn(
                          "font-semibold text-lg leading-none truncate",
                          task.is_completed && "text-muted-foreground line-through decoration-muted-foreground/50"
                        )}>
                          {task.job.title}
                        </h3>
                        {task.job.url && (
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="h-8 gap-2 hidden sm:flex"
                            onClick={() => window.open(task.job.url, '_blank')}
                          >
                            Apply Now
                            <ExternalLink size={14} />
                          </Button>
                        )}
                      </div>
                      
                      <p className="text-sm text-muted-foreground">
                        {task.job.company} • {task.job.location || 'Remote'}
                      </p>

                      <div className="flex items-center gap-2 mt-2">
                         <Badge variant={
                           task.job.match_score >= 80 ? 'success' : 
                           task.job.match_score >= 60 ? 'warning' : 'secondary'
                         }>
                           {task.job.match_score}% Match
                         </Badge>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  )
}