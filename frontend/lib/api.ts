/**
 * API utility functions for making requests to the backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ApiResponse<T = any> {
  data?: T
  error?: string
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const token = localStorage.getItem('access_token')

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Request failed' }))
      return { error: errorData.detail || `HTTP ${response.status}` }
    }

    const data = await response.json()
    return { data }
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : 'An unexpected error occurred',
    }
  }
}

/**
 * Auth API calls
 */
export const auth = {
  getChessComAuthUrl: () => apiRequest('/api/auth/chess-com/authorize'),
  getLichessAuthUrl: () => apiRequest('/api/auth/lichess/authorize'),
  getCurrentUser: () => apiRequest('/api/auth/me'),
}

/**
 * Games API calls
 */
export const games = {
  import: (platform: string, limit: number) =>
    apiRequest('/api/games/import', {
      method: 'POST',
      body: JSON.stringify({ platform, limit }),
    }),
  list: (limit = 50, skip = 0, analyzedOnly = false) =>
    apiRequest(`/api/games?limit=${limit}&skip=${skip}&analyzed_only=${analyzedOnly}`),
  get: (gameId: string) => apiRequest(`/api/games/${gameId}`),
  getSummary: () => apiRequest('/api/games/stats/summary'),
}

/**
 * Patterns API calls
 */
export const patterns = {
  list: () => apiRequest('/api/patterns'),
  get: (patternId: string) => apiRequest(`/api/patterns/${patternId}`),
  getProgress: () => apiRequest('/api/patterns/progress/history'),
}

/**
 * Jobs API calls
 */
export const jobs = {
  get: (jobId: string) => apiRequest(`/api/jobs/${jobId}`),
  list: (limit = 50) => apiRequest(`/api/jobs?limit=${limit}`),
}
