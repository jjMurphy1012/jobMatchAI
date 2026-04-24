import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircle, Circle, ExternalLink, PartyPopper, Briefcase, TrendingUp, FileText, Settings, Search } from 'lucide-react'
import { tasksApi, DailyTask, TaskStatsResponse, resumeApi, preferencesApi } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Progress } from '../components/ui/progress'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { cn } from '../lib/utils'

export default function Dashboard() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<DailyTask[]>([])
  const [stats, setStats] = useState<TaskStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [hasResume, setHasResume] = useState(false)
  const [hasProfile, setHasProfile] = useState(false)

  const allCompleted = Boolean(stats?.all_completed)

  useEffect(() => {
    loadInitial()
  }, [])

  async function loadInitial() {
    setLoading(true)
    const [tasksRes, statsRes, resumeRes, profileRes] = await Promise.all([
      tasksApi.list(),
      tasksApi.stats(),
      resumeApi.get(),
      preferencesApi.get(),
    ])

    if (tasksRes.data) setTasks(tasksRes.data.tasks)
    if (statsRes.data) setStats(statsRes.data)
    setHasResume(Boolean(resumeRes.data))
    setHasProfile(Boolean(profileRes.data?.raw_text || profileRes.data?.effective_fields?.keywords?.length))
    setLoading(false)
  }

  async function refreshTasks() {
    const [tasksRes, statsRes] = await Promise.all([tasksApi.list(), tasksApi.stats()])
    if (tasksRes.data) setTasks(tasksRes.data.tasks)
    if (statsRes.data) setStats(statsRes.data)
  }

  async function toggleTask(taskId: string, isCompleted: boolean) {
    const api = isCompleted ? tasksApi.uncomplete : tasksApi.complete
    const result = await api(taskId)
    if (result.data) {
      await refreshTasks()
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
      <section className="page-shell overflow-hidden p-8 sm:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(26,86,219,0.12),_transparent_36%),radial-gradient(circle_at_right,_rgba(14,159,110,0.07),_transparent_28%)]" />
        <div className="relative flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">Today</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Welcome back
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
              Resume and Career Profile are your setup steps. Matches only appear after you manually run a new search from the Matches page.
            </p>
          </div>
          <Button className="gap-2" size="lg" onClick={() => navigate('/matches')}>
            <Search className="h-4 w-4" />
            Open Matches
          </Button>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className={cn("border-slate-200/80", hasResume && "border-emerald-200 bg-emerald-50/40")}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Resume</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-2xl font-bold">{hasResume ? 'Ready' : 'Missing'}</div>
            <p className="text-xs text-muted-foreground">
              Upload your latest resume before running a new match cycle.
            </p>
            <Button variant={hasResume ? 'outline' : 'default'} size="sm" onClick={() => navigate('/resume')}>
              {hasResume ? 'Review Resume' : 'Upload Resume'}
            </Button>
          </CardContent>
        </Card>

        <Card className={cn("border-slate-200/80", hasProfile && "border-emerald-200 bg-emerald-50/40")}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Career Profile</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-2xl font-bold">{hasProfile ? 'Ready' : 'Missing'}</div>
            <p className="text-xs text-muted-foreground">
              Tell the system what roles, locations, and companies you care about.
            </p>
            <Button variant={hasProfile ? 'outline' : 'default'} size="sm" onClick={() => navigate('/preferences')}>
              {hasProfile ? 'Edit Profile' : 'Create Profile'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-slate-200/80">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Manual Match</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-2xl font-bold">{tasks.length > 0 ? 'Active' : 'Not run yet'}</div>
            <p className="text-xs text-muted-foreground">
              Run Match from the Matches page whenever you want a fresh set of opportunities.
            </p>
            <Button variant="outline" size="sm" onClick={() => navigate('/matches')}>
              Open Matches
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Header & Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Today
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
              Application Queue
            </CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tasks.length}</div>
            <p className="text-xs text-muted-foreground">
              Matched roles currently in your task list
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
          <h2 className="text-xl font-semibold tracking-tight">Today's Application Queue</h2>
        </div>

        {tasks.length === 0 ? (
          <Card className="py-12 flex flex-col items-center justify-center text-center">
            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
              <Briefcase className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-lg">No tasks yet</h3>
            <p className="text-muted-foreground max-w-sm mt-2">
              Upload your resume, fill your Career Profile, then run Match manually from the Matches page. New tasks will appear here after that.
            </p>
            <div className="mt-6">
              <Button onClick={() => navigate('/matches')}>
                Go to Matches
              </Button>
            </div>
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
