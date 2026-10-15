import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getWeatherSeries, getWeatherSummary } from '../services/api'
import PageHeader from '../components/PageHeader'
import KpiCard from '../components/KpiCard'
import PlotWrapper from '../components/PlotWrapper'

function fmt(v, d = 1) { return v != null ? Number(v).toLocaleString(undefined, { maximumFractionDigits: d }) : '—' }

export default function Weather() {
  const [start, setStart] = useState('2022-01-01')
  const [end, setEnd] = useState('2022-03-31')
  const [variable, setVariable] = useState('temperature_c')

  const params = { start, end, limit: 2000 }

  const { data: series = [], isLoading } = useQuery({
    queryKey: ['weather-series', params],
    queryFn: () => getWeatherSeries(params),
  })
  const { data: summary } = useQuery({
    queryKey: ['weather-summary'],
    queryFn: () => getWeatherSummary({}),
  })

  const VAR_CONFIG = {
    temperature_c:            { label: 'Temperature (°C)', color: '#ef4444' },
    cloud_cover_pct:          { label: 'Cloud Cover (%)', color: '#8b5cf6' },
    shortwave_radiation_wm2:  { label: 'Shortwave Radiation (W/m²)', color: '#f59e0b' },
    precipitation_mm:         { label: 'Precipitation (mm)', color: '#06b6d4' },
    wind_speed_ms:            { label: 'Wind Speed (m/s)', color: '#10b981' },
    relative_humidity_pct:    { label: 'Relative Humidity (%)', color: '#3b82f6' },
  }

  const cfg = VAR_CONFIG[variable]
  const plotData = [{
    type: 'scatter', mode: 'lines',
    name: cfg.label,
    x: series.map(r => r.observed_at),
    y: series.map(r => r[variable]),
    line: { color: cfg.color, width: 1.5 },
  }]

  return (
    <div>
      <PageHeader title="Weather & Historical Analytics" subtitle="Hourly weather observations aligned with generation data" />

      <div className="kpi-grid">
        <KpiCard label="Weather Records" value={fmt(summary?.total_rows, 0)} accent="primary" />
        <KpiCard label="Mean Temperature" value={summary?.mean_temperature_c != null ? `${fmt(summary.mean_temperature_c)}°C` : '—'} accent="warning" />
        <KpiCard label="Mean Cloud Cover" value={summary?.mean_cloud_cover_pct != null ? `${fmt(summary.mean_cloud_cover_pct)}%` : '—'} />
        <KpiCard label="Mean Radiation" value={summary?.mean_shortwave_radiation_wm2 != null ? `${fmt(summary.mean_shortwave_radiation_wm2)} W/m²` : '—'} accent="success" />
      </div>

      <div className="card" style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <div className="section-label">Start date</div>
          <input type="date" value={start} onChange={e => setStart(e.target.value)} />
        </div>
        <div>
          <div className="section-label">End date</div>
          <input type="date" value={end} onChange={e => setEnd(e.target.value)} />
        </div>
        <div>
          <div className="section-label">Variable</div>
          <select value={variable} onChange={e => setVariable(e.target.value)}>
            {Object.entries(VAR_CONFIG).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
        </div>
      </div>

      <PlotWrapper
        data={plotData}
        isLoading={isLoading}
        isEmpty={series.length === 0}
        emptyMessage="No weather data found. Ingest a weather CSV or fetch from Open-Meteo via the Pipeline page."
        layout={{
          title: { text: cfg.label, font: { color: '#e2e8f0' } },
          xaxis: { title: 'Date / Time (UTC)' },
          yaxis: { title: cfg.label },
        }}
        style={{ minHeight: 320 }}
      />
    </div>
  )
}
