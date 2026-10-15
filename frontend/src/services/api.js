import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Error interceptor ────────────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      'Unknown error'
    return Promise.reject(new Error(msg))
  },
)

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/health').then(r => r.data)

// ── Overview ──────────────────────────────────────────────────────────────────
export const getOverview = () => api.get('/overview').then(r => r.data)

// ── Data sources ──────────────────────────────────────────────────────────────
export const getSources = () => api.get('/sources').then(r => r.data)
export const createSource = (payload) => api.post('/sources', payload).then(r => r.data)

// ── Pipelines ─────────────────────────────────────────────────────────────────
export const getPipelineRuns = (params) => api.get('/pipelines/runs', { params }).then(r => r.data)
export const ingestSolarCSV = (payload) => api.post('/pipelines/ingest/solar-csv', payload).then(r => r.data)
export const ingestOpenMeteo = (payload) => api.post('/pipelines/ingest/open-meteo', payload).then(r => r.data)

// ── Data quality ──────────────────────────────────────────────────────────────
export const getLatestQuality = (params) => api.get('/data-quality/latest', { params }).then(r => r.data)
export const getQualityReports = (params) => api.get('/data-quality', { params }).then(r => r.data)
export const getQualityDetail = (id) => api.get(`/data-quality/${id}/detail`).then(r => r.data)

// ── Analytics ─────────────────────────────────────────────────────────────────
export const getGenerationSeries = (params) => api.get('/analytics/generation', { params }).then(r => r.data)
export const getGenerationSummary = (params) => api.get('/analytics/generation/summary', { params }).then(r => r.data)
export const getWeatherSeries = (params) => api.get('/analytics/weather', { params }).then(r => r.data)
export const getWeatherSummary = (params) => api.get('/analytics/weather/summary', { params }).then(r => r.data)

// ── Forecasts ─────────────────────────────────────────────────────────────────
export const getGenerationForecasts = (params) => api.get('/forecasts/generation', { params }).then(r => r.data)
export const getModelVersions = (params) => api.get('/forecasts/models', { params }).then(r => r.data)
export const getModelEvaluations = (params) => api.get('/forecasts/models/evaluations', { params }).then(r => r.data)
export const getEvaluationsSummary = (params) => api.get('/forecasts/models/evaluations/summary', { params }).then(r => r.data)

// ── ML training ───────────────────────────────────────────────────────────────
export const trainSolarModels = (payload) => api.post('/ml/train/solar', payload).then(r => r.data)

// ── Anomalies ─────────────────────────────────────────────────────────────────
export const getAnomalies = (params) => api.get('/anomalies', { params }).then(r => r.data)
export const getAnomalySummary = () => api.get('/anomalies/summary').then(r => r.data)
export const updateAlertStatus = (id, payload) => api.patch(`/anomalies/${id}/status`, payload).then(r => r.data)

// ── Scenarios ─────────────────────────────────────────────────────────────────
export const getScenarios = (params) => api.get('/scenarios', { params }).then(r => r.data)
export const createScenario = (payload) => api.post('/scenarios', payload).then(r => r.data)
export const getScenario = (id) => api.get(`/scenarios/${id}`).then(r => r.data)
