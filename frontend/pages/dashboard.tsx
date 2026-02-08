import { useEffect, useState } from 'react'
import Head from 'head'
import { useRouter } from 'next/router'

interface Pattern {
  id: string
  pattern_type: string
  pattern_subtype: string
  severity: number
  frequency: number
  metadata?: any
}

export default function Dashboard() {
  const router = useRouter()
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPatterns()
  }, [])

  const fetchPatterns = async () => {
    try {
      const token = localStorage.getItem('access_token')

      if (!token) {
        router.push('/')
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/patterns`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch patterns')
      }

      const data = await response.json()
      setPatterns(data.all_patterns || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your patterns...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>Dashboard - ChessMirror</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
              <div className="space-x-4">
                <button
                  onClick={() => router.push('/analyze')}
                  className="text-gray-600 hover:text-gray-800"
                >
                  Analyze
                </button>
                <button
                  onClick={() => router.push('/import')}
                  className="text-gray-600 hover:text-gray-800"
                >
                  Import
                </button>
                <button
                  onClick={handleLogout}
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
          <h1 className="text-4xl font-bold mb-8">Your Chess Patterns</h1>

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
              {error}
            </div>
          )}

          {patterns.length === 0 ? (
            <div className="bg-white rounded-lg shadow-lg p-8 text-center">
              <h2 className="text-2xl font-bold mb-4">No Patterns Yet</h2>
              <p className="text-gray-600 mb-6">
                Import your games to start discovering patterns in your play.
              </p>
              <button
                onClick={() => router.push('/import')}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
              >
                Import Games
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-6">Your Top Blind Spots</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {patterns.slice(0, 3).map((pattern, index) => (
                  <PatternCard key={pattern.id} pattern={pattern} rank={index + 1} />
                ))}
              </div>

              {patterns.length > 3 && (
                <div className="mt-12">
                  <h3 className="text-xl font-bold mb-4">All Patterns</h3>
                  <div className="space-y-4">
                    {patterns.slice(3).map((pattern) => (
                      <PatternRow key={pattern.id} pattern={pattern} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function PatternCard({ pattern, rank }: { pattern: Pattern; rank: number }) {
  const severityColor = pattern.severity > 0.7 ? 'red' : pattern.severity > 0.4 ? 'yellow' : 'blue'
  const colorClasses = {
    red: 'bg-red-100 border-red-500',
    yellow: 'bg-yellow-100 border-yellow-500',
    blue: 'bg-blue-100 border-blue-500'
  }

  const badgeClasses = {
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
    blue: 'bg-blue-500'
  }

  const severityLabel = pattern.severity > 0.7 ? 'High' : pattern.severity > 0.4 ? 'Medium' : 'Low'

  return (
    <div className={`border-2 rounded-lg p-4 ${colorClasses[severityColor]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-3xl font-bold text-gray-700">#{rank}</span>
        <span className={`${badgeClasses[severityColor]} text-white px-3 py-1 rounded-full text-xs font-semibold`}>
          {severityLabel}
        </span>
      </div>

      <h3 className="text-lg font-semibold mb-2">
        {formatPatternName(pattern.pattern_subtype)}
      </h3>

      <div className="text-sm text-gray-600 mb-3">
        Frequency: {pattern.frequency} times
      </div>
    </div>
  )
}

function PatternRow({ pattern }: { pattern: Pattern }) {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
      <div>
        <h4 className="font-semibold">{formatPatternName(pattern.pattern_subtype)}</h4>
        <p className="text-sm text-gray-600">Type: {pattern.pattern_type}</p>
      </div>
      <div className="text-right">
        <div className="text-sm text-gray-600">Frequency: {pattern.frequency}</div>
        <div className="text-sm text-gray-600">Severity: {(pattern.severity * 100).toFixed(0)}%</div>
      </div>
    </div>
  )
}

function formatPatternName(subtype: string): string {
  return subtype
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
