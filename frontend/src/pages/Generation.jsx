import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getGenerationSeries, getGenerationSummary } from '../services/api'
import PageHeader from '../components/PageHeader'
import KpiCard from '../components/KpiCard'
import PlotWrapper from '../components/PlotWrapper'

function fmt(v, d = 2) { return v != null ? Number(v).toLocaleString(undefined, { maximumFractionDigits: d }) : '—' }

export default function Generation() {
  const [start, setStart] = useState('2022-01-01')
  const [end, setEnd]     = useState('2022-03-31')
  const [limit, setLimit] = useState(2000)

  const params = { start, end, limit }

  const { data: series = [], isLoading } = useQuery({
    queryKey: ['generation-series', params],
    queryFn: () => getGenerationSeries(params),
  })

  const { data: summary } = useQuery({
    queryKey: ['generation-summary'],
    queryFn: () => getGenerationSummary({}),
  })

  const plotData = [{
    type: 'scatter',
    mode: 'lines',
    name: 'Generation (kWh)',
    x: series.map(r => r.observed_at),
    y: series.map(r => r.generation_kwh),
    line: { color: '#3b82f6', width: 1.5 },
    fill: 'tozeroy',
    fillcolor: 'rgba(59,130,246,0.08)',
  }]

  const ghiData = series.filter(r => r.ghi != null)
  if (ghiData.length > 0) {
    plotData.push({
      type: 'scatter',
      mode: 'lines',
      name: 'GHI (W/m²)',
      x: ghiData.map(r => r.observed_at),
      y: ghiData.map(r => r.ghi),
      yaxis: 'y2',
      line: { color: '#f59e0b', width: 1, dash: 'dot' },
    })
  }

  return (
    <div>
      <PageHeader
        title="Solar Generation"
        subtitle="Historical generation observations from ingested data"
      />

      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(175px,1fr))' }}>
        <KpiCard label="Total Records" value={fmt(summary?.total_rows, 0)} accent="primary" />
        <KpiCard label="Total Generation" value={summary?.total_generation_kwh != null ? `${fmt(summary.total_generation_kwh, 0)} kWh` : '—'} accent="success" />
        <KpiCard label="Mean per Hour" value={summary?.mean_generation_kwh != null ? `${fmt(summary.mean_generation_kwh, 3)} kWh` : '—'} />
        <KpiCard label="Peak Hour" value={summary?.max_generation_kwh != null ? `${fmt(summary.max_generation_kwh, 3)} kWh` : '—'} accent="warning" />
      </div>

      {/* Date filter */}
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
          <div className="section-label">Max rows</div>
          <select value={limit} onChange={e => setLimit(Number(e.target.value))}>
            {[500, 1000, 2000, 5000].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
      </div>

      <PlotWrapper
        data={plotData}
        isLoading={isLoading}
        isEmpty={series.length === 0}
        emptyMessage="No generation data found for this date range. Ingest a solar CSV first."
        layout={{
          title: { text: 'Hourly Solar Generation', font: { color: '#e2e8f0' } },
          xaxis: { title: 'Date / Time (UTC)' },
          yaxis: { title: 'Generation (kWh)' },
          yaxis2: { title: 'GHI (W/m²)', overlaying: 'y', side: 'right', showgrid: false },
        }}
        style={{ minHeight: 340 }}
      />

      {/* Data table */}
      {series.length > 0 && (
        <div className="card" style={{ marginTop: '1rem', overflowX: 'auto' }}>
          <div className="section-label" style={{ marginBottom: '0.5rem' }}>
            Showing {series.length} rows (most recent first)
          </div>
          <table>
            <thead>
              <tr>
                <th>Timestamp (UTC)</th>
                <th>Generation (kWh)</th>
                <th>GHI (W/m²)</th>
                <th>Temperature (°C)</th>
                <th>Site</th>
              </tr>
            </thead>
            <tbody>
              {[...series].reverse().slice(0, 50).map((r, i) => (
                <tr key={i}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.observed_at?.slice(0, 19)}</td>
                  <td>{fmt(r.generation_kwh, 4)}</td>
                  <td>{fmt(r.ghi, 1)}</td>
                  <td>{fmt(r.temperature_c, 1)}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{r.site_id || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {series.length > 50 && (
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              Showing latest 50 of {series.length} rows. Narrow the date range to see more.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
