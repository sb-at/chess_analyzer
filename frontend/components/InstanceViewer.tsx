'use client'

import { useState, useEffect, useMemo } from 'react'
import { Chess } from 'chess.js'
import { Chessboard } from 'react-chessboard'

interface Instance {
  game_id: string
  fen: string
  move_number: number
  move_played: string
  best_move?: string
  eval_loss: number
  date?: string
  opening_name?: string
  opening_eco?: string
  result?: string
  user_color?: string
  time_control?: string
  motif?: string
  accuracy?: number
  is_mistake?: boolean
  is_blunder?: boolean
}

interface InstanceViewerProps {
  instances: Instance[]
  isOpen: boolean
  onClose: () => void
  title: string
}

export default function InstanceViewer({
  instances,
  isOpen,
  onClose,
  title,
}: InstanceViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [game, setGame] = useState<Chess | null>(null)
  const [showBestMove, setShowBestMove] = useState(false)
  // Stores green/red highlights after a move, or yellow/arrow for best move display
  const [moveResultStyles, setMoveResultStyles] = useState<Record<string, React.CSSProperties>>({})
  const [customArrows, setCustomArrows] = useState<Array<[any, any]>>([])
  const [userTryMode, setUserTryMode] = useState(false)
  const [userMadeMove, setUserMadeMove] = useState(false)
  const [moveWasBest, setMoveWasBest] = useState(false)
  const [touchStart, setTouchStart] = useState<number | null>(null)
  // Click-to-select state
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null)
  const [legalMoveSquares, setLegalMoveSquares] = useState<string[]>([])

  const currentInstance = instances[currentIndex]

  // Merge move-result/best-move highlights with selection highlights
  const customSquareStyles = useMemo(() => {
    const styles: Record<string, React.CSSProperties> = { ...moveResultStyles }

    if (selectedSquare) {
      styles[selectedSquare] = {
        backgroundColor: 'rgba(255, 200, 0, 0.7)',
      }

      legalMoveSquares.forEach((sq) => {
        if (!styles[sq]) {
          const piece = game?.get(sq as any)
          if (piece) {
            // Capture square — ring
            styles[sq] = {
              background: 'radial-gradient(circle, transparent 60%, rgba(0,0,0,0.25) 60%)',
            }
          } else {
            // Empty square — dot
            styles[sq] = {
              background: 'radial-gradient(circle, rgba(0,0,0,0.18) 25%, transparent 25%)',
            }
          }
        }
      })
    }

    return styles
  }, [moveResultStyles, selectedSquare, legalMoveSquares, game])

  const clearSelection = () => {
    setSelectedSquare(null)
    setLegalMoveSquares([])
  }

  // Initialize chess game when instance changes
  useEffect(() => {
    if (!currentInstance) return

    try {
      const chess = new Chess(currentInstance.fen)
      setGame(chess)
      setShowBestMove(false)
      setMoveResultStyles({})
      setCustomArrows([])
      setUserTryMode(false)
      setUserMadeMove(false)
      setMoveWasBest(false)
      clearSelection()
    } catch (error) {
      console.error('Error loading position:', error)
    }
  }, [currentInstance])

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        handlePrevious()
      } else if (e.key === 'ArrowRight') {
        handleNext()
      } else if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, currentIndex, instances.length])

  // Touch swipe handling
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStart(e.touches[0].clientX)
  }

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStart) return

    const touchEnd = e.changedTouches[0].clientX
    const diff = touchStart - touchEnd

    if (Math.abs(diff) > 50) {
      if (diff > 0) {
        handleNext()
      } else {
        handlePrevious()
      }
    }

    setTouchStart(null)
  }

  if (!isOpen || !currentInstance || !game) return null

  const handleNext = () => {
    if (currentIndex < instances.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleShowBestMove = () => {
    if (!currentInstance.best_move) return

    setShowBestMove(true)
    setUserTryMode(false)
    clearSelection()

    const from = currentInstance.best_move.substring(0, 2)
    const to = currentInstance.best_move.substring(2, 4)

    setMoveResultStyles({
      [from]: {
        backgroundColor: 'rgba(255, 170, 0, 0.6)',
        borderRadius: '50%',
      },
      [to]: {
        backgroundColor: 'rgba(255, 170, 0, 0.4)',
      },
    })

    setCustomArrows([[from, to]])
  }

  const handleTryYourself = () => {
    setUserTryMode(true)
    setShowBestMove(false)
    setMoveResultStyles({})
    setCustomArrows([])
    setUserMadeMove(false)
    setMoveWasBest(false)
    clearSelection()
  }

  // Shared move logic used by both drag-and-drop and click-to-move
  const applyMove = (sourceSquare: string, targetSquare: string): boolean => {
    if (!game) return false

    try {
      const move = game.move({
        from: sourceSquare,
        to: targetSquare,
        promotion: 'q',
      })

      if (move) {
        const isBestMove = currentInstance.best_move === `${sourceSquare}${targetSquare}`
        setUserMadeMove(true)
        setMoveWasBest(isBestMove)

        if (isBestMove) {
          setMoveResultStyles({
            [sourceSquare]: { backgroundColor: 'rgba(0, 255, 0, 0.6)' },
            [targetSquare]: { backgroundColor: 'rgba(0, 255, 0, 0.4)' },
          })
        } else {
          setMoveResultStyles({
            [sourceSquare]: { backgroundColor: 'rgba(255, 0, 0, 0.6)' },
            [targetSquare]: { backgroundColor: 'rgba(255, 0, 0, 0.4)' },
          })
        }

        return true
      }

      return false
    } catch {
      return false
    }
  }

  // Drag-and-drop handler
  const onDrop = (sourceSquare: string, targetSquare: string) => {
    if (!userTryMode || userMadeMove || !game) return false
    clearSelection()
    return applyMove(sourceSquare, targetSquare)
  }

  // Click-to-select and click-to-move handler
  const onSquareClick = (square: string) => {
    if (!game || userMadeMove) return

    // A piece is already selected
    if (selectedSquare) {
      // Clicked a legal destination — move
      if (legalMoveSquares.includes(square)) {
        if (userTryMode) {
          applyMove(selectedSquare, square)
        }
        clearSelection()
        return
      }

      // Re-clicked the selected square — deselect
      if (square === selectedSquare) {
        clearSelection()
        return
      }

      // Clicked another piece of the same color — switch selection
      const piece = game.get(square as any)
      if (piece && piece.color === game.turn()) {
        setSelectedSquare(square)
        const moves = game.moves({ square: square as any, verbose: true })
        setLegalMoveSquares(moves.map((m: any) => m.to))
        return
      }

      // Clicked anything else — deselect
      clearSelection()
      return
    }

    // Nothing selected yet — select a piece of the current turn
    const piece = game.get(square as any)
    if (piece && piece.color === game.turn()) {
      setSelectedSquare(square)
      const moves = game.moves({ square: square as any, verbose: true })
      setLegalMoveSquares(moves.map((m: any) => m.to))
    }
  }

  const boardOrientation = currentInstance.user_color === 'black' ? 'black' : 'white'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
            <p className="text-sm text-gray-600 mt-1">
              Instance {currentIndex + 1} of {instances.length}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-3xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chess Board */}
            <div>
              <Chessboard
                position={game.fen()}
                boardOrientation={boardOrientation}
                onPieceDrop={onDrop}
                onSquareClick={onSquareClick}
                customSquareStyles={customSquareStyles}
                customArrows={customArrows}
                arePiecesDraggable={userTryMode && !userMadeMove}
                customBoardStyle={{
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                }}
              />

              {/* Action Buttons */}
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleTryYourself}
                  disabled={userTryMode && !userMadeMove}
                  className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  {userTryMode && !userMadeMove ? 'Make your move...' : 'Try Yourself'}
                </button>
                <button
                  onClick={handleShowBestMove}
                  disabled={!currentInstance.best_move}
                  className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  Show Best Move
                </button>
              </div>
            </div>

            {/* Position Details */}
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Position Info</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Move:</span>
                    <span className="font-medium text-gray-900">{currentInstance.move_number}</span>
                  </div>
                  {currentInstance.opening_name && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Opening:</span>
                      <span className="font-medium text-gray-900">
                        {currentInstance.opening_name}
                        {currentInstance.opening_eco && ` (${currentInstance.opening_eco})`}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-600">You played:</span>
                    <span className="font-mono text-gray-900 font-bold">
                      {currentInstance.move_played}
                    </span>
                  </div>
                  {currentInstance.best_move && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Best move:</span>
                      <span className="font-mono text-green-700 font-bold">
                        {currentInstance.best_move}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-600">Eval Loss:</span>
                    <span
                      className={`font-semibold ${
                        currentInstance.eval_loss > 200
                          ? 'text-red-600'
                          : currentInstance.eval_loss > 100
                          ? 'text-orange-600'
                          : 'text-yellow-600'
                      }`}
                    >
                      {currentInstance.eval_loss} cp
                    </span>
                  </div>
                  {currentInstance.accuracy !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Accuracy:</span>
                      <span className="font-medium text-gray-900">
                        {currentInstance.accuracy.toFixed(1)}%
                      </span>
                    </div>
                  )}
                  {currentInstance.motif && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Tactic:</span>
                      <span className="font-medium text-purple-700 capitalize">
                        {currentInstance.motif.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Game Context */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Game Context</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Color:</span>
                    <span className="font-medium text-gray-900 capitalize">
                      {currentInstance.user_color}
                    </span>
                  </div>
                  {currentInstance.result && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Result:</span>
                      <span className="font-medium text-gray-900">{currentInstance.result}</span>
                    </div>
                  )}
                  {currentInstance.time_control && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Time Control:</span>
                      <span className="font-medium text-gray-900">
                        {currentInstance.time_control}
                      </span>
                    </div>
                  )}
                  {currentInstance.date && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Date:</span>
                      <span className="font-medium text-gray-900">
                        {new Date(currentInstance.date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Feedback Messages */}
              {showBestMove && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-green-800 text-sm">
                    The best move is highlighted with an arrow. Study the position and understand
                    why this move is superior.
                  </p>
                </div>
              )}

              {userMadeMove && (
                <div
                  className={`border rounded-lg p-4 ${
                    moveWasBest ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                  }`}
                >
                  <p className={`text-sm ${moveWasBest ? 'text-green-800' : 'text-red-800'}`}>
                    {moveWasBest
                      ? 'Excellent! You found the best move.'
                      : 'Not quite. Click "Show Best Move" to see the optimal move.'}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between items-center mt-6 pt-6 border-t">
            <button
              onClick={handlePrevious}
              disabled={currentIndex === 0}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              ← Previous
            </button>
            <div className="text-sm text-gray-600">Swipe or use arrow keys to navigate</div>
            <button
              onClick={handleNext}
              disabled={currentIndex === instances.length - 1}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
