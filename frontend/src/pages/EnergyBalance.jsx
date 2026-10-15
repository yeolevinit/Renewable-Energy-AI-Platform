import { useQuery } from '@tanstack/react-query'
import { getGenerationSeries } from '../services/api'
import PageHeader from '../components/PageHeader'
import KpiCard from '../components/KpiCard'
import PlotWrapper from '../components/PlotWrapper'

function fmt(v, d = 1) { return v != null ? Number(v).toLocaleString(undefined, { maximumFractionDigits: d }) : '—' }

export default function EnergyBalance() {
  // Load generation data for a representative month
  const params = { start: '2022-06-01', end: '2022-06-30', limit: 2000 }

  const { data: genSeries = [], isLoading } = useQuery({
    queryKey: ['gen-balance', params],
    queryFn: () => getGenerationSeries(params),
  })

  const totalGen = genSeries.reduce((s, r) => s + (r.generation_kwh || 0), 0)

  // Build hourly average profile (aggregated by hour-of-day)
  const byHour = Array(24).fill(0).map(() => ({ sum: 0, count: 0 }))
  genSeries.forEach(r => {
    const h = new Date(r.observed_at).getUTCHours()
    byHour[h].sum += r.generation_kwh || 0
    byHour[h].count += 1
  })
  const hourlyAvg = byHour.map(b => b.count > 0 ? b.sum / b.count : 0)

  const plotData = [
    {
      type: 'bar', name: 'Avg Generation (kWh/h)',
      x: Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`),
      y: hourlyAvg,
      marker: { color: '#3b82f6' },
    },
  ]

  const timeSeries = [{
    type: 'scatter', mode: 'lines', name: 'Generation (kWh)',
    x: genSeries.map(r => r.observed_at),
    y: genSeries.map(r => r.generation_kwh),
    line: { color: '#10b981', width: 1 },
    fill: 'tozeroy', fillcolor: 'rgba(16,185,129,0.07)',
  }]

  return (
    <div>
      <PageHeader
        title="Energy Balance"
        subtitle="Generation profile and analysis for the selected period"
      />

      <div style={{ padding: '0.75rem 1rem', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 'var(--radius)', marginBottom: '1.25rem', fontSize: '0.82rem', color: 'var(--warning)' }}>
        ⚠ Demand data is not loaded in this prototype. Generation-demand gap analysis requires compatible demand data with matching time intervals, units, and system boundaries. Use the <strong>Scenario Lab</strong> to simulate gap estimates with user-defined assumptions.
      </div>

      <div className="kpi-grid">
        <KpiCard label="Total Generation (June)" value={`${fmt(totalGen, 0)} kWh`} accent="success" />
        <KpiCard label="Daily Average" value={genSeries.length > 0 ? `${fmt(totalGen / 30, 0)} kWh/day` : '—'} accent="primary" />
        <KpiCard label="Peak Hour Generation" value={`${fmt(Math.max(...genSeries.map(r => r.generation_kwh || 0)), 3)} kWh`} accent="warning" />
        <KpiCard label="Zero-generation Hours" value={fmt(genSeries.filter(r => (r.generation_kwh || 0) < 0.01).length)} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <PlotWrapper
          data={plotData}
          isLoading={isLoading}
          isEmpty={genSeries.length === 0}
          emptyMessage="No generation data for June 2022. Ingest data first."
          layout={{ title: { text: 'Average Hourly Generation Profile', font: { color: '#e2e8f0' } }, xaxis: { title: 'Hour of Day (UTC)' }, yaxis: { title: 'Avg kWh/hour' } }}
          style={{ minHeight: 280 }}
        />
        <PlotWrapper
          data={timeSeries}
          isLoading={isLoading}
          isEmpty={genSeries.length === 0}
          emptyMessage="No data available."
          layout={{ title: { text: 'Generation Time Series', font: { color: '#e2e8f0' } }, xaxis: { title: 'Date' }, yaxis: { title: 'kWh' } }}
          style={{ minHeight: 280 }}
        />
      </div>

      <div className="card">
        <div className="section-label">About Energy Balance Analysis</div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
          A meaningful generation-demand gap calculation requires both series to share compatible time intervals, energy units (kWh), and geographic/system boundaries. Comparing a single rooftop solar installation with national grid demand, for example, would not produce a valid supply-deficit figure without a defensible scope definition.
        </p>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.75rem', lineHeight: 1.7 }}>
          Once a compatible demand dataset is ingested, the <strong>Scenario Lab</strong> page will allow you to model generation-demand gaps with user-adjustable assumptions and compare baseline versus adjusted scenarios.
        </p>
      </div>
    </div>
  )
}
