/**
 * API utility functions for making requests to the backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ApiResponse<T = any> {
  data?: T
  error?: string
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
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
 * Analysis API calls
 */
export const analysis = {
  getPatternInstances: (patternId: string) =>
    apiRequest(`/api/analysis/patterns/${patternId}/instances`),
}

/**
 * Openings API calls
 */
export const openings = {
  getInstances: (params: {
    opening_name?: string
    opening_eco?: string
    user_color?: string
    job_id?: string
  }) => {
    const queryParams = new URLSearchParams()
    if (params.opening_name) queryParams.append('opening_name', params.opening_name)
    if (params.opening_eco) queryParams.append('opening_eco', params.opening_eco)
    if (params.user_color) queryParams.append('user_color', params.user_color)
    if (params.job_id) queryParams.append('job_id', params.job_id)
    return apiRequest(`/api/openings/instances?${queryParams.toString()}`)
  },
}
