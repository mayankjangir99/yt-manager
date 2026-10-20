import axios from 'axios'
const apiBase = import.meta.env.VITE_API_BASE

if (!apiBase) {
  throw new Error('VITE_API_BASE is required. Add it to frontend/.env and restart Vite.')
}

export const api = axios.create({ baseURL: apiBase })
export const errText = e => e?.response?.data?.detail || e?.message || 'Something went wrong'
