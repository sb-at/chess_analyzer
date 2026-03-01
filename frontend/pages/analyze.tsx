import { useState, useEffect } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'

export default function AnalyzePage() {
  const router = useRouter()
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [detectingPatterns, setDetectingPatterns] = useState(false)
  const [analysisJobId, setAnalysisJobId] = useState<string | null>(null)
  const [patternsJobId, setPatternsJobId] = useState<string | null>(null)
  const [activeJob, setActiveJob] = useState<any>(null)

  // Analysis configuration
  const [selectedLimit, setSelectedLimit] = useState<number>(25)
  const [selectedTimeControl, setSelectedTimeControl] = useState<string>('all')
  const [timeControls, setTimeControls] = useState<any[]>([])
  const [loadingTimeControls, setLoadingTimeControls] = useState(false)

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  // Poll active job status
  useEffect(() => {
    if (!analysisJobId && !patternsJobId) return

    const pollJob = async () => {
      const jobId = analysisJobId || patternsJobId
      if (!jobId) return

      try {
        const token = localStorage.getItem('access_token')
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) return

        const job = await response.json()
        setActiveJob(job)

        // Stop polling when job completes or fails
        if (job.status === 'completed' || job.status === 'failed') {
          setAnalysisJobId(null)
          setPatternsJobId(null)
          setActiveJob(null)
          fetchStats() // Refresh stats
        }
      } catch (err) {
        console.error('Error polling job:', err)
      }
    }

    pollJob() // Poll immediately
    const interval = setInterval(pollJob, 2000) // Poll every 2 seconds
    return () => clearInterval(interval)
  }, [analysisJobId, patternsJobId])

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        router.push('/')
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/analysis/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) throw new Error('Failed to fetch stats')

      const data = await response.json()
      setStats(data)

      // Set time controls from stats
      if (data.time_controls && data.time_controls.length > 0) {
        setTimeControls(data.time_controls)
      }
    } catch (err) {
      console.error('Error fetching stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const getEngagingMessage = (job: any) => {
    if (!job) return ''

    const { job_type, status, progress, processed_items, total_items } = job

    if (status === 'completed') {
      if (job_type === 'analysis') {
        return '✅ Analysis complete! All games analyzed.'
      } else if (job_type === 'pattern_detection') {
        return '✅ Pattern detection complete!'
      }
    }

    if (status === 'failed') {
      return '❌ Job failed. Please try again.'
    }

    if (job_type === 'analysis') {
      if (total_items && processed_items) {
        return `🔍 Analyzing game ${processed_items} of ${total_items}...`
      } else if (progress < 30) {
        return 'Reading your games...'
      } else if (progress < 70) {
        return 'Running Stockfish analysis...'
      } else {
        return 'Finalizing analysis results...'
      }
    }

    if (job_type === 'pattern_detection') {
      if (progress < 30) {
        return '🔎 Scanning games for patterns...'
      } else if (progress < 70) {
        return '🧩 Identifying recurring mistakes...'
      } else {
        return '📈 Compiling pattern insights...'
      }
    }

    return 'Processing...'
  }

  const startAnalysis = async () => {
    try {
      setAnalyzing(true)
      const token = localStorage.getItem('access_token')
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      const requestBody: any = { limit: selectedLimit }

      // Only include time_control if a specific one is selected
      if (selectedTimeControl && selectedTimeControl !== 'all') {
        requestBody.time_control = selectedTimeControl
      }

      const response = await fetch(`${apiUrl}/api/analysis/analyze-games`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) throw new Error('Failed to start analysis')

      const data = await response.json()
      setAnalysisJobId(data.job_id)
    } catch (err) {
      console.error('Error starting analysis:', err)
      alert('Failed to start analysis')
    } finally {
      setAnalyzing(false)
    }
  }

  const startPatternDetection = async () => {
    try {
      setDetectingPatterns(true)
      const token = localStorage.getItem('access_token')
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      const response = await fetch(`${apiUrl}/api/analysis/detect-patterns`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) throw new Error('Failed to start pattern detection')

      const data = await response.json()
      setPatternsJobId(data.job_id)
    } catch (err) {
      console.error('Error starting pattern detection:', err)
      alert('Failed to start pattern detection')
    } finally {
      setDetectingPatterns(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>Analyze Games - ChessMirror</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
              <div className="space-x-4">
                <button
                  onClick={() => router.push('/dashboard')}
                  className="text-gray-600 hover:text-gray-800"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => {
                    localStorage.clear()
                    router.push('/')
                  }}
                  className="text-gray-600 hover:text-gray-800"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-4xl font-bold mb-8">Game Analysis</h1>

          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <StatCard
              title="Total Games"
              value={stats?.total_games || 0}
              color="blue"
            />
            <StatCard
              title="Analyzed Games"
              value={stats?.analyzed_games || 0}
              color="green"
            />
            <StatCard
              title="Pending Analysis"
              value={stats?.pending_analysis || 0}
              color="yellow"
            />
          </div>

          {/* Active Job Progress */}
          {activeJob && activeJob.status === 'running' && (
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow-lg p-6 mb-8 border-2 border-blue-200">
              <div className="flex items-center mb-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-3"></div>
                <h3 className="text-xl font-bold text-gray-800">
                  {getEngagingMessage(activeJob)}
                </h3>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-blue-500 to-purple-500 h-6 rounded-full transition-all duration-500 flex items-center justify-center text-white text-sm font-semibold"
                  style={{ width: `${activeJob.progress || 0}%` }}
                >
                  {activeJob.progress || 0}%
                </div>
              </div>
              {activeJob.total_items && activeJob.processed_items && (
                <p className="text-sm text-gray-600 mt-2">
                  Progress: {activeJob.processed_items} / {activeJob.total_items} games
                </p>
              )}
            </div>
          )}

          {/* Overall Progress Bar */}
          {stats && !activeJob && (
            <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-lg font-semibold">Overall Analysis Progress</h3>
                <span className="text-sm text-gray-600">
                  {stats.analysis_percentage}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className="bg-blue-600 h-4 rounded-full transition-all"
                  style={{ width: `${stats.analysis_percentage}%` }}
                />
              </div>
            </div>
          )}

          {/* Speed Tip */}
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  <strong>Speed Tip:</strong> Analyzing fewer games or filtering by a specific time control will complete much faster.
                  Start with 10-25 games to get quick insights, then analyze more if needed.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-2xl font-bold mb-6">Analysis Actions</h2>

            <div className="space-y-4">
              <div className="border-b pb-4">
                <h3 className="text-lg font-semibold mb-2">1. Analyze Games with Stockfish</h3>
                <p className="text-gray-600 mb-4">
                  Analyze your games with the Stockfish chess engine to identify mistakes and calculate accuracy.
                </p>

                {/* Analysis Configuration */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {/* Number of Games Selector */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Number of Games
                    </label>
                    <select
                      value={selectedLimit}
                      onChange={(e) => setSelectedLimit(Number(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value={10}>10 games (Fastest)</option>
                      <option value={25}>25 games (Recommended)</option>
                      <option value={50}>50 games</option>
                      <option value={100}>100 games</option>
                      <option value={200}>200 games</option>
                    </select>
                  </div>

                  {/* Time Control Selector */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Time Control
                    </label>
                    <select
                      value={selectedTimeControl}
                      onChange={(e) => setSelectedTimeControl(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="all">All Time Controls</option>
                      {timeControls.map((tc) => (
                        <option key={tc.time_control} value={tc.time_control}>
                          {tc.display_name} ({tc.count} games)
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  onClick={startAnalysis}
                  disabled={analyzing || stats?.pending_analysis === 0 || (activeJob?.status === 'running')}
                  className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {analyzing ? 'Starting Analysis...' : activeJob?.job_type === 'analysis' && activeJob?.status === 'running' ? 'Analysis Running...' : `Analyze ${selectedLimit} Games`}
                </button>
                {stats?.pending_analysis === 0 && (
                  <p className="text-sm text-green-600 mt-2">All games are analyzed!</p>
                )}
                {selectedTimeControl !== 'all' && (
                  <p className="text-sm text-blue-600 mt-2">
                    Filtering by: {timeControls.find(tc => tc.time_control === selectedTimeControl)?.display_name}
                  </p>
                )}
              </div>

              <div className="pt-4">
                <h3 className="text-lg font-semibold mb-2">2. Detect Patterns</h3>
                <p className="text-gray-600 mb-4">
                  Detect recurring patterns in your play including tactical mistakes, opening weaknesses, and time management issues.
                </p>
                <button
                  onClick={startPatternDetection}
                  disabled={detectingPatterns || stats?.analyzed_games < 5 || (activeJob?.status === 'running')}
                  className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {detectingPatterns ? 'Detecting Patterns...' : activeJob?.job_type === 'pattern_detection' && activeJob?.status === 'running' ? 'Detection Running...' : 'Detect Patterns'}
                </button>
                {stats?.analyzed_games < 5 && (
                  <p className="text-sm text-yellow-600 mt-2">
                    Need at least 5 analyzed games for pattern detection
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Recent Jobs */}
          {stats?.recent_jobs && stats.recent_jobs.length > 0 && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-4">Recent Jobs</h2>
              <div className="space-y-3">
                {stats.recent_jobs.map((job: any) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function StatCard({ title, value, color }: { title: string; value: number; color: string }) {
  const colors = {
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    yellow: 'bg-yellow-100 text-yellow-800'
  }

  return (
    <div className={`${colors[color as keyof typeof colors]} rounded-lg p-6`}>
      <h3 className="text-sm font-semibold uppercase mb-2">{title}</h3>
      <p className="text-3xl font-bold">{value}</p>
    </div>
  )
}

function JobCard({ job }: { job: any }) {
  const statusColors = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
  }

  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
      <div>
        <h4 className="font-semibold capitalize">{job.type.replace('_', ' ')}</h4>
        <p className="text-sm text-gray-600">
          {new Date(job.created_at).toLocaleString()}
        </p>
      </div>
      <div className="flex items-center space-x-4">
        {job.status === 'running' && (
          <div className="text-sm text-gray-600">{job.progress}%</div>
        )}
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusColors[job.status as keyof typeof statusColors]}`}>
          {job.status}
        </span>
      </div>
    </div>
  )
}
