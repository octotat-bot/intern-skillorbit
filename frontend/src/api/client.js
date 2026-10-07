// Thin Axios wrapper around the Flask API. All network calls live here.
import axios from 'axios'

const baseURL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000').replace(/\/$/, '')

export const api = axios.create({ baseURL: `${baseURL}/api`, timeout: 60000 })

/** Upload a resume file; reports 0-100 upload progress. */
export async function uploadResume(file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/resumes', form, {
    onUploadProgress: (event) => {
      if (event.total && onProgress) onProgress(Math.round((event.loaded / event.total) * 100))
    },
  })
  return data
}

export async function fetchRoles() {
  const { data } = await api.get('/roles')
  return data.roles
}

export async function fetchAnalysis(resumeId, role, mode = 'rules') {
  const { data } = await api.get(`/resumes/${resumeId}/analysis`, { params: { role, mode } })
  return data
}

/** Human-readable message for any API or network error. */
export function errorMessage(error) {
  const body = error?.response?.data
  if (body?.message) return body.message
  if (error?.code === 'ECONNABORTED') return 'The server took too long to respond. Please try again.'
  if (error?.request && !error?.response) {
    return `Can't reach the analysis server at ${baseURL}. Is the backend running?`
  }
  return 'Something went wrong. Please try again.'
}
