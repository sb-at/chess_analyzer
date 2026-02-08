import { useState, useEffect } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'

export default function ImportGames() {
  const router = useRouter()
  const [platform, setPlatform] = useState<'chess.com' | 'lichess'>('chess.com')
  const [limit, setLimit] = useState(500)
  const [status, setStatus] = useState<'idle' | 'importing' | 'complete'>('idle')
  const [progress, setProgress] = useState(0)
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (jobId && status === 'importing') {
      const interval = setInterval(() => {
        pollJobStatus()
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [jobId, status])

  const pollJobStatus = async () => {
    if (!jobId) return

    try {
      const token = localStorage.getItem('access_token')
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      const response = await fetch(`${apiUrl}/api/jobs/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) throw new Error('Failed to fetch job status')

      const data = await response.json()

      setProgress(data.progress || 0)

      if (data.status === 'completed') {
        setStatus('complete')
      } else if (data.status === 'failed') {
        setError(data.error_message || 'Import failed')
        setStatus('idle')
      }
    } catch (err) {
      console.error('Error polling job:', err)
    }
  }

  const startImport = async () => {
    try {
      setStatus('importing')
      setError(null)
      setProgress(0)

      const token = localStorage.getItem('access_token')

      if (!token) {
        router.push('/')
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/games/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          platform,
          limit
        })
      })

      if (!response.ok) {
        throw new Error('Failed to start import')
      }

      const data = await response.json()
      setJobId(data.job_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setStatus('idle')
    }
  }

  return (
    <>
      <Head>
        <title>Import Games - ChessMirror</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
              <button
                onClick={() => router.push('/dashboard')}
                className="text-gray-600 hover:text-gray-800"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg p-8">
              <h2 className="text-3xl font-bold mb-6">Import Your Games</h2>

              {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
                  {error}
                </div>
              )}

              {status === 'idle' && (
                <div>
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select Platform
                    </label>
                    <div className="grid grid-cols-2 gap-4">
                      <button
                        onClick={() => setPlatform('chess.com')}
                        className={`p-4 border-2 rounded-lg transition ${
                          platform === 'chess.com'
                            ? 'border-green-600 bg-green-50'
                            : 'border-gray-300 hover:border-green-400'
                        }`}
                      >
                        <div className="font-semibold">Chess.com</div>
                      </button>
                      <button
                        onClick={() => setPlatform('lichess')}
                        className={`p-4 border-2 rounded-lg transition ${
                          platform === 'lichess'
                            ? 'border-black bg-gray-50'
                            : 'border-gray-300 hover:border-gray-600'
                        }`}
                      >
                        <div className="font-semibold">Lichess</div>
                      </button>
                    </div>
                  </div>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Number of Games
                    </label>
                    <input
                      type="number"
                      value={limit}
                      onChange={(e) => setLimit(parseInt(e.target.value))}
                      min="10"
                      max="1000"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-sm text-gray-500 mt-1">
                      We'll import your {limit} most recent games
                    </p>
                  </div>

                  <button
                    onClick={startImport}
                    className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition font-semibold"
                  >
                    Import Games
                  </button>
                </div>
              )}

              {status === 'importing' && (
                <div>
                  <div className="mb-4">
                    <div className="flex justify-between mb-2">
                      <span className="font-medium">Importing games from {platform}...</span>
                      <span className="font-medium">{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-4">
                      <div
                        className="bg-blue-600 h-4 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  <div className="bg-blue-50 p-4 rounded-lg mt-6">
                    <p className="text-sm text-blue-800">
                      <strong>Did you know?</strong> Magnus Carlsen plays 1. e4 in approximately 60% of his games.
                    </p>
                  </div>
                </div>
              )}

              {status === 'complete' && (
                <div className="text-center">
                  <div className="text-green-600 text-6xl mb-4">✓</div>
                  <h3 className="text-2xl font-bold mb-2">Import Complete!</h3>
                  <p className="text-gray-600 mb-6">
                    Your games have been imported. Analysis will begin shortly.
                  </p>
                  <button
                    onClick={() => router.push('/dashboard')}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition font-semibold"
                  >
                    View Dashboard
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
