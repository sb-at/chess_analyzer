import { useEffect, useState } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'
import InstanceViewer from '../../components/InstanceViewer'
import { openings as openingsApi, analysis as analysisApi } from '../../lib/api'

interface Pattern {
  _id: string  // MongoDB ObjectId for public analyses
  id?: string  // PostgreSQL UUID for authenticated users
  pattern_type: string
  pattern_subtype: string
  severity: number
  frequency: number
  metadata?: any
}

interface OpeningStats {
  white_openings: Opening[]
  black_openings: Opening[]
  total_white_games: number
  total_black_games: number
}

interface Opening {
  name: string
  eco: string | null
  count: number
  wins: number
  draws: number
  losses: number
  win_rate: number
}

interface JobResult {
  job_id: string
  status: string
  progress: number
  metadata: {
    platform: string
    username: string
    limit: number
    time_control?: string
  }
  patterns?: Pattern[]
  opening_stats?: OpeningStats
  games_analyzed?: number
  created_at: string
  completed_at?: string
}

export default function Results() {
  const router = useRouter()
  const { jobId } = router.query
  const [result, setResult] = useState<JobResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Instance Viewer state
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerInstances, setViewerInstances] = useState<any[]>([])
  const [viewerTitle, setViewerTitle] = useState('')
  const [viewerKey, setViewerKey] = useState(0)
  const [loadingInstances, setLoadingInstances] = useState(false)

  useEffect(() => {
    if (!jobId) return

    const pollResults = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/analysis/results/${jobId}`)

        if (!response.ok) {
          throw new Error('Failed to fetch results')
        }

        const data = await response.json()
        console.log('Raw API response keys:', Object.keys(data))
        console.log('Has opening_stats in response:', 'opening_stats' in data)
        console.log('opening_stats value:', data.opening_stats)
        console.log('Full API response:', JSON.stringify(data, null, 2))
        setResult(data)

        // If not complete, poll again
        if (data.status !== 'completed' && data.status !== 'failed') {
          setTimeout(pollResults, 3000) // Poll every 3 seconds
        } else {
          setLoading(false)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred')
        setLoading(false)
      }
    }

    pollResults()
  }, [jobId])

  const handlePatternClick = async (patternId: string, patternName: string) => {
    setLoadingInstances(true)
    setViewerTitle(`${patternName} - Review Instances`)

    // Use analysis API for MongoDB-based patterns (public analyses)
    const response = await analysisApi.getPatternInstances(patternId)

    if (response.data?.instances) {
      setViewerKey(k => k + 1)
      setViewerInstances(response.data.instances)
      setViewerOpen(true)
    } else {
      console.error('Failed to load pattern instances:', response.error)
      alert(`Failed to load pattern instances: ${response.error || 'Unknown error'}`)
    }

    setLoadingInstances(false)
  }

  const handleOpeningClick = async (opening: Opening, userColor: string) => {
    setLoadingInstances(true)
    setViewerTitle(`${opening.name} - Problematic Positions`)

    const response = await openingsApi.getInstances({
      opening_name: opening.name,
      opening_eco: opening.eco || undefined,
      user_color: userColor,
      job_id: typeof jobId === 'string' ? jobId : undefined,
    })

    if (response.data?.instances) {
      setViewerKey(k => k + 1)
      setViewerInstances(response.data.instances)
      setViewerOpen(true)
    } else {
      console.error('Failed to load opening instances:', response.error)
      alert(`Failed to load opening instances: ${response.error || 'Unknown error'}`)
    }

    setLoadingInstances(false)
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">Error</div>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (result.status === 'failed') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">Analysis Failed</div>
          <p className="text-gray-600 mb-6">
            Unable to complete analysis for {result.metadata.username}
          </p>
          <button
            onClick={() => router.push('/')}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (result.status !== 'completed') {
    return (
      <>
        <Head>
          <title>Analyzing Games - ChessMirror</title>
        </Head>

        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white shadow-sm">
            <div className="container mx-auto px-4 py-4">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
            </div>
          </nav>

          <div className="container mx-auto px-4 py-16">
            <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
              <h1 className="text-3xl font-bold mb-6 text-center">
                Analyzing {result.metadata.username}'s Games
              </h1>

              <div className="mb-6">
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">Progress</span>
                  <span className="text-gray-600">{result.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-blue-600 h-4 rounded-full transition-all duration-300"
                    style={{ width: `${result.progress}%` }}
                  />
                </div>
              </div>

              <div className="text-center text-gray-600">
                <p className="mb-2">Platform: {result.metadata.platform}</p>
                {result.metadata.time_control && (
                  <p className="mb-2">Time Control: {result.metadata.time_control}</p>
                )}
                <p>This may take a few minutes...</p>
              </div>

              <div className="mt-8 flex justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            </div>
          </div>
        </div>
      </>
    )
  }

  // Completed - show results
  const patterns = result.patterns || []
  const openingStats = result.opening_stats

  // Debug logging
  console.log('Result data:', result)
  console.log('Opening stats:', openingStats)

  return (
    <>
      <Head>
        <title>Analysis Results - ChessMirror</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
              <button
                onClick={() => router.push('/')}
                className="text-gray-600 hover:text-gray-800"
              >
                Analyze Another
              </button>
            </div>
          </div>
        </nav>

        <div className="container mx-auto px-4 py-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">
              {result.metadata.username}'s Chess Patterns
            </h1>
            <p className="text-gray-600">
              Analyzed {result.games_analyzed} games from {result.metadata.platform}
              {result.metadata.time_control && (
                <span> • Time Control: {result.metadata.time_control}</span>
              )}
            </p>
          </div>

          {/* Opening Statistics Section */}
          {openingStats && (
            <div className="mb-8 bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-6">Openings</h2>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* White Openings */}
                <div>
                  <h3 className="text-xl font-semibold mb-4 text-gray-700">
                    As White ({openingStats.total_white_games} games)
                  </h3>
                  {openingStats.white_openings.length > 0 ? (
                    <div className="space-y-3">
                      {openingStats.white_openings.slice(0, 10).map((opening, index) => (
                        <OpeningRow
                          key={index}
                          opening={opening}
                          onClick={() => handleOpeningClick(opening, 'white')}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">No games played as white</p>
                  )}
                </div>

                {/* Black Openings */}
                <div>
                  <h3 className="text-xl font-semibold mb-4 text-gray-700">
                    As Black ({openingStats.total_black_games} games)
                  </h3>
                  {openingStats.black_openings.length > 0 ? (
                    <div className="space-y-3">
                      {openingStats.black_openings.slice(0, 10).map((opening, index) => (
                        <OpeningRow
                          key={index}
                          opening={opening}
                          onClick={() => handleOpeningClick(opening, 'black')}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">No games played as black</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {patterns.length === 0 ? (
            <div className="bg-white rounded-lg shadow-lg p-8 text-center">
              <h2 className="text-2xl font-bold mb-4">No Patterns Found</h2>
              <p className="text-gray-600 mb-6">
                Not enough games or no significant patterns detected.
              </p>
              <button
                onClick={() => router.push('/')}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
              >
                Analyze Another Player
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-6">Top Blind Spots</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {patterns.slice(0, 3).map((pattern, index) => (
                  <PatternCard
                    key={pattern._id || pattern.id}
                    pattern={pattern}
                    rank={index + 1}
                    onClick={() =>
                      handlePatternClick(pattern._id || pattern.id!, formatPatternName(pattern.pattern_subtype))
                    }
                  />
                ))}
              </div>

              {patterns.length > 3 && (
                <div className="mt-12">
                  <h3 className="text-xl font-bold mb-4">All Patterns</h3>
                  <div className="space-y-4">
                    {patterns.slice(3).map((pattern) => (
                      <PatternRow
                        key={pattern._id || pattern.id}
                        pattern={pattern}
                        onClick={() =>
                          handlePatternClick(pattern._id || pattern.id!, formatPatternName(pattern.pattern_subtype))
                        }
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Instance Viewer Modal */}
        <InstanceViewer
          key={viewerKey}
          instances={viewerInstances}
          isOpen={viewerOpen}
          onClose={() => setViewerOpen(false)}
          title={viewerTitle}
        />

        {/* Loading Overlay */}
        {loadingInstances && (
          <div className="fixed inset-0 z-40 flex items-center justify-center bg-black bg-opacity-30">
            <div className="bg-white rounded-lg p-6 shadow-xl">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading instances...</p>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

function PatternCard({
  pattern,
  rank,
  onClick,
}: {
  pattern: Pattern
  rank: number
  onClick?: () => void
}) {
  const severityColor = pattern.severity > 0.7 ? 'red' : pattern.severity > 0.4 ? 'yellow' : 'blue'
  const colorClasses = {
    red: 'bg-red-100 border-red-500',
    yellow: 'bg-yellow-100 border-yellow-500',
    blue: 'bg-blue-100 border-blue-500',
  }

  const badgeClasses = {
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
    blue: 'bg-blue-500',
  }

  const severityLabel = pattern.severity > 0.7 ? 'High' : pattern.severity > 0.4 ? 'Medium' : 'Low'

  return (
    <div
      className={`border-2 rounded-lg p-4 ${colorClasses[severityColor]} cursor-pointer hover:shadow-lg transition-shadow`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-3xl font-bold text-gray-700">#{rank}</span>
        <span
          className={`${badgeClasses[severityColor]} text-white px-3 py-1 rounded-full text-xs font-semibold`}
        >
          {severityLabel}
        </span>
      </div>

      <h3 className="text-lg font-semibold mb-2">{formatPatternName(pattern.pattern_subtype)}</h3>

      <div className="text-sm text-gray-600 mb-3">Frequency: {pattern.frequency} times</div>

      <div className="text-xs text-blue-600 font-medium mt-2">Click to review instances →</div>
    </div>
  )
}

function PatternRow({ pattern, onClick }: { pattern: Pattern; onClick?: () => void }) {
  return (
    <div
      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
      onClick={onClick}
    >
      <div className="flex-1">
        <h4 className="font-semibold">{formatPatternName(pattern.pattern_subtype)}</h4>
        <p className="text-sm text-gray-600">Type: {pattern.pattern_type}</p>
      </div>
      <div className="text-right mr-4">
        <div className="text-sm text-gray-600">Frequency: {pattern.frequency}</div>
        <div className="text-sm text-gray-600">Severity: {(pattern.severity * 100).toFixed(0)}%</div>
      </div>
      <div className="text-blue-600 text-sm font-medium">Review →</div>
    </div>
  )
}

function formatPatternName(subtype: string): string {
  return subtype
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function OpeningRow({
  opening,
  onClick,
}: {
  opening: Opening
  onClick?: () => void
}) {
  const winRateColor =
    opening.win_rate >= 60 ? 'text-green-600' : opening.win_rate >= 40 ? 'text-gray-700' : 'text-red-600'
  const bgColor =
    opening.win_rate >= 60 ? 'bg-green-50' : opening.win_rate >= 40 ? 'bg-gray-50' : 'bg-red-50'

  return (
    <div
      className={`${bgColor} rounded-lg p-4 border border-gray-200 cursor-pointer hover:shadow-md transition-shadow`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="font-semibold text-gray-800 mb-1">
            {opening.name}
            {opening.eco && (
              <span className="ml-2 text-xs font-normal text-gray-500 bg-gray-200 px-2 py-1 rounded">
                {opening.eco}
              </span>
            )}
          </div>
          <div className="text-sm text-gray-600">
            {opening.count} game{opening.count !== 1 ? 's' : ''} •{' '}
            {opening.wins}W / {opening.draws}D / {opening.losses}L
          </div>
          <div className="text-xs text-blue-600 font-medium mt-1">Click to review positions →</div>
        </div>
        <div className={`text-right font-bold text-lg ${winRateColor}`}>{opening.win_rate}%</div>
      </div>
    </div>
  )
}
