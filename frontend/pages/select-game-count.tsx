import { useEffect, useState } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'

const GAME_COUNT_OPTIONS = [
  { value: 25, label: '25 games', description: 'Quick analysis' },
  { value: 50, label: '50 games', description: 'Balanced' },
  { value: 100, label: '100 games', description: 'Detailed' },
  { value: 250, label: '250 games', description: 'Comprehensive' },
  { value: 500, label: '500 games', description: 'Deep dive' },
]

export default function SelectGameCount() {
  const router = useRouter()
  const { platform, username, timeControl } = router.query

  const [startingAnalysis, setStartingAnalysis] = useState(false)
  const [selectedCount, setSelectedCount] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!platform || !username || !timeControl) {
      router.push('/')
    }
  }, [platform, username, timeControl, router])

  const handleSelectCount = async (count: number) => {
    setSelectedCount(count)
    setStartingAnalysis(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/analysis/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          platform,
          username,
          limit: count,
          time_control: timeControl
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to start analysis')
      }

      const data = await response.json()
      router.push(`/results/${data.job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis')
      setStartingAnalysis(false)
      setSelectedCount(null)
    }
  }

  if (!platform || !username || !timeControl) {
    return null
  }

  return (
    <>
      <Head>
        <title>Select Number of Games - ChessMirror</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
              <button
                onClick={() => router.back()}
                className="text-gray-600 hover:text-gray-800"
                disabled={startingAnalysis}
              >
                Back
              </button>
            </div>
          </div>
        </nav>

        <div className="container mx-auto px-4 py-12">
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold mb-4">
                How Many Games to Analyze?
              </h1>
              <p className="text-gray-600 text-lg">
                Select the number of recent {timeControl} games to analyze for {username}
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-300 rounded-lg p-4 mb-6 text-center">
                <p className="text-red-700">{error}</p>
              </div>
            )}

            {startingAnalysis && (
              <div className="bg-blue-50 border border-blue-300 rounded-lg p-4 mb-6 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                <p className="text-blue-700">Starting analysis...</p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {GAME_COUNT_OPTIONS.map((option) => (
                <GameCountCard
                  key={option.value}
                  option={option}
                  onSelect={handleSelectCount}
                  disabled={startingAnalysis}
                  selected={selectedCount === option.value}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function GameCountCard({
  option,
  onSelect,
  disabled,
  selected
}: {
  option: typeof GAME_COUNT_OPTIONS[0]
  onSelect: (count: number) => void
  disabled: boolean
  selected: boolean
}) {
  return (
    <button
      onClick={() => onSelect(option.value)}
      disabled={disabled}
      className={`
        bg-white border-2 rounded-lg p-6 text-left transition-all
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-blue-400 hover:shadow-md'}
        ${selected ? 'border-blue-500 ring-2 ring-blue-500 scale-105' : 'border-gray-200'}
      `}
    >
      <h3 className="text-2xl font-bold mb-2">
        {option.label}
      </h3>
      <p className="text-gray-600 text-sm">
        {option.description}
      </p>
    </button>
  )
}
