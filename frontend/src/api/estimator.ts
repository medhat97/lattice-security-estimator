import axios from 'axios'
import type { EstimateRequest, EstimateResponse, FindParamRequest, FindParamResponse, Preset } from '../types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE,
  timeout: 300_000,
  headers: { 'ngrok-skip-browser-warning': 'true' },
})

export const getPresets = (): Promise<Preset[]> =>
  api.get<Preset[]>('/presets').then(r => r.data)

export const postEstimate = (body: EstimateRequest): Promise<EstimateResponse> =>
  api.post<EstimateResponse>('/estimate', body).then(r => r.data)

export const postFindParam = (body: FindParamRequest): Promise<FindParamResponse> =>
  api.post<FindParamResponse>('/find-parameter', body).then(r => r.data)
