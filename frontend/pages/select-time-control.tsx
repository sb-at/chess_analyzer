import { useEffect, useState } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'
import {
  TimeControl,
  getTimeControlIcon,
  getCategoryColorClasses,
  groupByCategory,
  getCategoryOrder
} from '../utils/timeControl'

export default function SelectTimeControl() {
  const router = useRouter()
  const { platform, username } = router.query

  const [timeControls, setTimeControls] = useState<TimeControl[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!platform || !username) return

    const fetchTimeControls = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/analysis/time-controls`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            platform,
            username,
            sample_size: 100
          })
        })

        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.detail || 'Failed to fetch time controls')
        }

        const data = await response.json()
        setTimeControls(data.time_controls)
        setLoading(false)

        // Auto-select if only one time control
        if (data.time_controls.length === 1) {
          handleSelectTimeControl(data.time_controls[0].time_control)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch time controls')
        setLoading(false)
      }
    }

    fetchTimeControls()
  }, [platform, username])

  const handleSelectTimeControl = (timeControl: string) => {
    router.push({
      pathname: '/select-game-count',
      query: {
        platform,
        username,
        timeControl
      }
    })
  }

  if (loading) {
    return (
      <>
        <Head>
          <title>Finding Time Controls - ChessMirror</title>
        </Head>

        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white shadow-sm">
            <div className="container mx-auto px-4 py-4">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
            </div>
          </nav>

          <div className="container mx-auto px-4 py-16">
            <div className="max-w-2xl mx-auto text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-6"></div>
              <h1 className="text-2xl font-bold mb-4">
                Looking for your played time controls...
              </h1>
              <p className="text-gray-600">
                Scanning {username}'s recent games on {platform}
              </p>
            </div>
          </div>
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <Head>
          <title>Error - ChessMirror</title>
        </Head>

        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white shadow-sm">
            <div className="container mx-auto px-4 py-4">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
            </div>
          </nav>

          <div className="container mx-auto px-4 py-16">
            <div className="max-w-2xl mx-auto text-center">
              <div className="text-red-600 text-xl mb-4">Error</div>
              <p className="text-gray-600 mb-6">{error}</p>
              <button
                onClick={() => router.push('/')}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      </>
    )
  }

  if (timeControls.length === 0) {
    return (
      <>
        <Head>
          <title>No Games Found - ChessMirror</title>
        </Head>

        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white shadow-sm">
            <div className="container mx-auto px-4 py-4">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
            </div>
          </nav>

          <div className="container mx-auto px-4 py-16">
            <div className="max-w-2xl mx-auto text-center">
              <h1 className="text-3xl font-bold mb-4">No Games Found</h1>
              <p className="text-gray-600 mb-6">
                We couldn't find any games for {username} on {platform}.
              </p>
              <button
                onClick={() => router.push('/')}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
              >
                Try Another Username
              </button>
            </div>
          </div>
        </div>
      </>
    )
  }

  // Group time controls by category
  const grouped = groupByCategory(timeControls)
  const categoryOrder = getCategoryOrder()
  const orderedCategories = categoryOrder.filter(cat => grouped[cat])

  return (
    <>
      <Head>
        <title>Select Time Control - ChessMirror</title>
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
                Back
              </button>
            </div>
          </div>
        </nav>

        <div className="container mx-auto px-4 py-12">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold mb-4">
                Choose Time Control to Analyze
              </h1>
              <p className="text-gray-600 text-lg">
                Select which time control you'd like to analyze for {username}
              </p>
            </div>

            <div className="space-y-8">
              {orderedCategories.map((category) => (
                <div key={category}>
                  <h2 className="text-2xl font-bold mb-4 capitalize flex items-center gap-2">
                    <span>{getTimeControlIcon(category)}</span>
                    <span>{category}</span>
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {grouped[category].map((tc) => (
                      <TimeControlCard
                        key={tc.time_control}
                        timeControl={tc}
                        onSelect={handleSelectTimeControl}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function TimeControlCard({
  timeControl,
  onSelect
}: {
  timeControl: TimeControl
  onSelect: (tc: string) => void
}) {
  const colors = getCategoryColorClasses(timeControl.category)
  const icon = getTimeControlIcon(timeControl.category)

  return (
    <button
      onClick={() => onSelect(timeControl.time_control)}
      className={`
        ${colors.bg} ${colors.border} ${colors.hover}
        border-2 rounded-lg p-6 text-left transition-all cursor-pointer
      `}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-3xl">{icon}</span>
        <span className={`${colors.text} font-semibold text-sm uppercase`}>
          {timeControl.category}
        </span>
      </div>

      <h3 className="text-xl font-bold mb-2">
        {timeControl.display_name}
      </h3>

      <p className="text-gray-600 text-sm">
        {timeControl.count} {timeControl.count === 1 ? 'game' : 'games'} played
      </p>
    </button>
  )
}
