import { getApiErrorMessage } from '../utils/apiError.js'

const viteEnv = import.meta.env || {}
const API_URL = viteEnv.VITE_API_BASE_URL || viteEnv.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'

let tokenProvider = async () => null
let unauthorizedHandler = async () => {}
export const setTokenProvider = (provider) => { tokenProvider = provider }
export const setUnauthorizedHandler = (handler) => { unauthorizedHandler = handler }

async function fetchWithToken(path, options, token) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(`${API_URL}${path}`, { ...options, headers })
}

async function request(path, options = {}) {
  let token = await tokenProvider(false)
  let response
  try {
    response = await fetchWithToken(path, options, token)
    if (response.status === 401 && token) {
      token = await tokenProvider(true)
      response = await fetchWithToken(path, options, token)
      if (response.status === 401) await unauthorizedHandler()
    }
  } catch (error) {
    throw new Error(getApiErrorMessage(error))
  }
  const text = await response.text()
  let body = null
  try { body = text ? JSON.parse(text) : null } catch { body = { detail: text } }
  if (!response.ok) {
    const error = new Error(getApiErrorMessage(body, `Request failed (${response.status})`))
    error.status = response.status
    error.body = body
    throw error
  }
  return body
}

export { getApiErrorMessage }

export const api = {
  get: (path) => request(path),
  post: (path, data) => request(path, { method: 'POST', body: JSON.stringify(data ?? {}) }),
  patch: (path, data) => request(path, { method: 'PATCH', body: JSON.stringify(data ?? {}) }),
  delete: (path) => request(path, { method: 'DELETE' }),
}
