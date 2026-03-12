import { useState, useEffect } from 'react'
import InstanceViewer from '../components/InstanceViewer'

// Fallback mock data — used when no real exported data is available.
// Real chess positions with known best moves in UCI format.
const MOCK_TACTICAL: Instance[] = [
  {
    game_id: 'mock-1',
    // After 1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 — White to move
    fen: 'r1bqk2r/pppp1ppp/2n2n2/4p1N1/2B1P3/8/PPPP1PPP/RNBQK2R w KQkq - 6 5',
    move_number: 5,
    move_played: 'd3',
    best_move: 'g5f7', // Nxf7! forking queen and rook
    eval_loss: 350,
    date: '2024-03-10',
    opening_name: 'Italian Game',
    opening_eco: 'C55',
    result: '0-1',
    user_color: 'white',
    time_control: '10+0',
    motif: 'fork',
    is_blunder: true,
  },
  {
    game_id: 'mock-2',
    // Back rank mate in one — White to move
    fen: '6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1',
    move_number: 32,
    move_played: 'Rb1',
    best_move: 'a1a8', // Ra8#
    eval_loss: 9999,
    date: '2024-03-08',
    opening_name: 'Ruy Lopez',
    opening_eco: 'C65',
    result: '1/2-1/2',
    user_color: 'white',
    time_control: '5+3',
    motif: 'back_rank',
    is_blunder: true,
  },
  {
    game_id: 'mock-3',
    // Italian Game — user failed to castle, best move is O-O
    fen: 'r1bqk2r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
    move_number: 4,
    move_played: 'h3',
    best_move: 'e1g1', // O-O
    eval_loss: 120,
    date: '2024-03-05',
    opening_name: 'Italian Game',
    opening_eco: 'C54',
    result: '0-1',
    user_color: 'white',
    time_control: '3+0',
    motif: 'king_safety',
    is_mistake: true,
  },
  {
    game_id: 'mock-4',
    // After 1.e4 e5 — user plays Ke2?!, best is Nf3
    fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
    move_number: 2,
    move_played: 'Ke2',
    best_move: 'g1f3', // Nf3
    eval_loss: 200,
    date: '2024-03-01',
    opening_name: "King's Pawn",
    opening_eco: 'B00',
    result: '0-1',
    user_color: 'white',
    time_control: '10+0',
    motif: 'development',
    is_blunder: true,
  },
]

const MOCK_OPENINGS: Instance[] = [
  {
    game_id: 'mock-5',
    fen: 'r1bqkb1r/pp2pppp/2np1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6',
    move_number: 6,
    move_played: 'Be3',
    best_move: 'd4b5',
    eval_loss: 180,
    date: '2024-02-20',
    opening_name: 'Sicilian Defence',
    opening_eco: 'B44',
    result: '0-1',
    user_color: 'white',
    time_control: '5+0',
    is_mistake: true,
  },
  {
    game_id: 'mock-6',
    fen: 'rnbqkb1r/ppp2ppp/4pn2/3p4/3PP3/2N5/PPP2PPP/R1BQKBNR w KQkq d6 0 5',
    move_number: 5,
    move_played: 'h4',
    best_move: 'e4d5',
    eval_loss: 90,
    date: '2024-02-18',
    opening_name: 'French Defence',
    opening_eco: 'C11',
    result: '0-1',
    user_color: 'white',
    time_control: '10+0',
    is_mistake: true,
  },
]

interface Instance {
  game_id: string
  fen: string
  move_number: number
  move_played: string
  best_move?: string
  eval_loss: number
  accuracy?: number
  is_mistake?: boolean
  is_blunder?: boolean
  date?: string
  opening_name?: string
  opening_eco?: string
  result?: string
  user_color?: string
  time_control?: string
  motif?: string
}

type DataSource = 'loading' | 'real' | 'mock'

export default function TestInstanceViewer() {
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerInstances, setViewerInstances] = useState<Instance[]>([])
  const [viewerTitle, setViewerTitle] = useState('')

  const [realInstances, setRealInstances] = useState<Instance[]>([])
  const [dataSource, setDataSource] = useState<DataSource>('loading')

  useEffect(() => {
    fetch('/instances.json')
      .then((res) => {
        if (!res.ok) throw new Error('not found')
        return res.json()
      })
      .then((data: Instance[]) => {
        setRealInstances(data)
        setDataSource('real')
      })
      .catch(() => {
        setDataSource('mock')
      })
  }, [])

  const openReal = () => {
    setViewerInstances(realInstances)
    setViewerTitle(`Real Positions — ${realInstances.length} instances`)
    setViewerOpen(true)
  }

  const openMockTactical = () => {
    setViewerInstances(MOCK_TACTICAL)
    setViewerTitle('Mock Tactics — forks, back rank, king safety')
    setViewerOpen(true)
  }

  const openMockOpenings = () => {
    setViewerInstances(MOCK_OPENINGS)
    setViewerTitle('Mock Openings — Sicilian & French')
    setViewerOpen(true)
  }

  const blunders = realInstances.filter((i) => i.is_blunder)
  const mistakes = realInstances.filter((i) => i.is_mistake && !i.is_blunder)

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-1">InstanceViewer Test Page</h1>
        <p className="text-gray-500 text-sm mb-6">
          Arrow keys / swipe to navigate · Escape to close
        </p>

        {/* Data source banner */}
        {dataSource === 'loading' && (
          <div className="mb-6 p-4 bg-gray-100 rounded-lg text-gray-600 text-sm">
            Checking for exported positions…
          </div>
        )}

        {dataSource === 'real' && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-800 font-semibold text-sm">
                  Real data loaded — {realInstances.length} positions from analyzed games
                </p>
                <p className="text-green-600 text-xs mt-1">
                  {blunders.length} blunders · {mistakes.length} mistakes
                </p>
              </div>
              <button
                onClick={openReal}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium transition-colors"
              >
                Open All →
              </button>
            </div>
          </div>
        )}

        {dataSource === 'mock' && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm">
            <p className="text-amber-800 font-semibold">No exported data found — using mock positions</p>
            <p className="text-amber-700 mt-1">
              To use real games, run:
            </p>
            <pre className="mt-2 bg-amber-100 rounded p-2 text-xs text-amber-900 overflow-x-auto">
              python export_instances.py [--job-id &lt;id&gt;] [--username &lt;name&gt;]
            </pre>
          </div>
        )}

        {/* Real data breakdown (when loaded) */}
        {dataSource === 'real' && realInstances.length > 0 && (
          <div className="mb-6 bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Positions by Opening
            </h2>
            <div className="space-y-2">
              {Object.entries(
                realInstances.reduce<Record<string, Instance[]>>((acc, inst) => {
                  const key = inst.opening_name || 'Unknown'
                  acc[key] = acc[key] || []
                  acc[key].push(inst)
                  return acc
                }, {})
              )
                .sort((a, b) => b[1].length - a[1].length)
                .slice(0, 8)
                .map(([opening, group]) => (
                  <div key={opening} className="flex items-center justify-between text-sm">
                    <button
                      className="text-blue-600 hover:underline text-left"
                      onClick={() => {
                        setViewerInstances(group)
                        setViewerTitle(opening)
                        setViewerOpen(true)
                      }}
                    >
                      {opening}
                    </button>
                    <span className="text-gray-400">
                      {group.filter((i) => i.is_blunder).length} blunders ·{' '}
                      {group.filter((i) => i.is_mistake && !i.is_blunder).length} mistakes
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Mock data buttons (always available) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          <button
            onClick={openMockTactical}
            className="p-5 bg-white rounded-xl border-2 border-blue-200 hover:border-blue-500 hover:shadow-md transition-all text-left"
          >
            <div className="text-xl mb-1">♞</div>
            <h2 className="font-semibold text-gray-900">Mock — Tactics</h2>
            <p className="text-sm text-gray-500 mt-1">
              {MOCK_TACTICAL.length} positions · fork, back rank, king safety
            </p>
          </button>

          <button
            onClick={openMockOpenings}
            className="p-5 bg-white rounded-xl border-2 border-purple-200 hover:border-purple-500 hover:shadow-md transition-all text-left"
          >
            <div className="text-xl mb-1">♟</div>
            <h2 className="font-semibold text-gray-900">Mock — Openings</h2>
            <p className="text-sm text-gray-500 mt-1">
              {MOCK_OPENINGS.length} positions · Sicilian, French
            </p>
          </button>
        </div>
      </div>

      <InstanceViewer
        instances={viewerInstances}
        isOpen={viewerOpen}
        onClose={() => {
          setViewerOpen(false)
          setViewerInstances([])
        }}
        title={viewerTitle}
      />
    </div>
  )
}
