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

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

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
    } catch (err) {
      console.error('Error fetching stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const startAnalysis = async () => {
    try {
      setAnalyzing(true)
      const token = localStorage.getItem('access_token')
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      const response = await fetch(`${apiUrl}/api/analysis/analyze-games`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ limit: 100 })
      })

      if (!response.ok) throw new Error('Failed to start analysis')

      const data = await response.json()
      setAnalysisJobId(data.job_id)
      alert('Game analysis started! This may take several minutes.')
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
      alert('Pattern detection started!')
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

          {/* Progress Bar */}
          {stats && (
            <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-lg font-semibold">Analysis Progress</h3>
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

          {/* Action Buttons */}
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-2xl font-bold mb-6">Analysis Actions</h2>

            <div className="space-y-4">
              <div className="border-b pb-4">
                <h3 className="text-lg font-semibold mb-2">1. Analyze Games with Stockfish</h3>
                <p className="text-gray-600 mb-4">
                  Analyze your games with the Stockfish chess engine to identify mistakes and calculate accuracy.
                </p>
                <button
                  onClick={startAnalysis}
                  disabled={analyzing || stats?.pending_analysis === 0}
                  className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {analyzing ? 'Starting Analysis...' : 'Analyze Unanalyzed Games'}
                </button>
                {stats?.pending_analysis === 0 && (
                  <p className="text-sm text-green-600 mt-2">All games are analyzed!</p>
                )}
              </div>

              <div className="pt-4">
                <h3 className="text-lg font-semibold mb-2">2. Detect Patterns</h3>
                <p className="text-gray-600 mb-4">
                  Detect recurring patterns in your play including tactical mistakes, opening weaknesses, and time management issues.
                </p>
                <button
                  onClick={startPatternDetection}
                  disabled={detectingPatterns || stats?.analyzed_games < 5}
                  className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {detectingPatterns ? 'Detecting Patterns...' : 'Detect Patterns'}
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
