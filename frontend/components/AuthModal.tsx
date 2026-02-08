import { useState } from 'react'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleOAuthLogin = async (platform: 'chess.com' | 'lichess') => {
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/auth/${platform}/authorize`)
      const data = await response.json()

      // Redirect to OAuth provider
      window.location.href = data.auth_url
    } catch (error) {
      console.error('OAuth error:', error)
      alert('Failed to initiate authentication. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">Connect Your Account</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              &times;
            </button>
          </div>

          <p className="text-gray-600 mb-6">
            Choose your chess platform to get started
          </p>

          <div className="space-y-4">
            <button
              onClick={() => handleOAuthLogin('chess.com')}
              disabled={loading}
              className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 transition font-semibold disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <span>Loading...</span>
              ) : (
                <>
                  <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a8 8 0 100 16 8 8 0 000-16zM8 9a1 1 0 112 0v4a1 1 0 11-2 0V9zm1-3a1 1 0 100 2 1 1 0 000-2z" />
                  </svg>
                  Connect Chess.com
                </>
              )}
            </button>

            <button
              onClick={() => handleOAuthLogin('lichess')}
              disabled={loading}
              className="w-full bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition font-semibold disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <span>Loading...</span>
              ) : (
                <>
                  <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a8 8 0 100 16 8 8 0 000-16zM8 9a1 1 0 112 0v4a1 1 0 11-2 0V9zm1-3a1 1 0 100 2 1 1 0 000-2z" />
                  </svg>
                  Connect Lichess
                </>
              )}
            </button>
          </div>

          <p className="text-sm text-gray-500 mt-6 text-center">
            We'll never post on your behalf or share your data
          </p>
        </div>
      </div>
    </div>
  )
}
