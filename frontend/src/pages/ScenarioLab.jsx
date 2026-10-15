import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { createScenario, getScenarios } from '../services/api'
import PageHeader from '../components/PageHeader'
import PlotWrapper from '../components/PlotWrapper'

function fmt(v, d = 1) { return v != null ? Number(v).toLocaleString(undefined, { maximumFractionDigits: d }) : '—' }

export default function ScenarioLab() {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    name: 'Scenario 1', description: '',
    analysis_start: '2022-06-01', analysis_end: '2022-06-30',
    generation_adjustment_pct: 0, demand_adjustment_pct: 0,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const { data: history = [] } = useQuery({
    queryKey: ['scenarios'],
    queryFn: () => getScenarios({ limit: 10 }),
  })

  const mut = useMutation({
    mutationFn: createScenario,
    onSuccess: (data) => { setResult(data); setError(null); qc.invalidateQueries(['scenarios']) },
    onError: (err) => { setError(err.message); setResult(null) },
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const plotData = result?.result_series?.length > 0 ? [
    { type: 'bar', name: 'Generation (kWh)', x: result.result_series.map(r => r.observed_at), y: result.result_series.map(r => r.gen_kwh), marker: { color: '#10b981' } },
    result.total_demand_kwh > 0 && { type: 'bar', name: 'Demand (kWh)', x: result.result_series.map(r => r.observed_at), y: result.result_series.map(r => r.dem_kwh), marker: { color: '#f59e0b' } },
  ].filter(Boolean) : []

  const statusColor = result?.balance_status === 'surplus' ? 'var(--success)'
    : result?.balance_status === 'deficit' ? 'var(--danger)' : 'var(--text-muted)'

  return (
    <div>
      <PageHeader title="Scenario Lab" subtitle="What-if simulation with adjustable generation and demand assumptions" />

      <div style={{ background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 'var(--radius)', padding: '0.75rem 1rem', marginBottom: '1.25rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        All outputs are simulated estimates based on user-defined assumptions and stored forecasts or historical observations. They are not real measurements or operational decisions.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '1.25rem', alignItems: 'start' }}>
        {/* Controls */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="section-label">Scenario Parameters</div>
          {[
            ['Name', 'name', 'text'],
            ['Analysis start', 'analysis_start', 'date'],
            ['Analysis end', 'analysis_end', 'date'],
          ].map(([label, key, type]) => (
            <div key={key}>
              <div className="section-label">{label}</div>
              <input type={type} value={form[key]} onChange={e => set(key, e.target.value)} style={{ width: '100%' }} />
            </div>
          ))}

          <div>
            <div className="section-label">Generation adjustment (%)</div>
            <input type="number" min={-100} max={200} value={form.generation_adjustment_pct}
              onChange={e => set('generation_adjustment_pct', Number(e.target.value))} style={{ width: '100%' }} />
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 3 }}>
              e.g. −20 = 20% reduction in generation
            </div>
          </div>

          <div>
            <div className="section-label">Demand adjustment (%)</div>
            <input type="number" min={-100} max={200} value={form.demand_adjustment_pct}
              onChange={e => set('demand_adjustment_pct', Number(e.target.value))} style={{ width: '100%' }} />
          </div>

          <button className="btn btn-primary" disabled={mut.isPending}
            onClick={() => mut.mutate(form)} style={{ width: '100%', justifyContent: 'center' }}>
            {mut.isPending ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Running…</> : 'Run scenario'}
          </button>

          {error && <div className="error-state">{error}</div>}
        </div>

        {/* Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {result ? (
            <>
              <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
                <div className="kpi-card">
                  <div className="kpi-label">Total Generation</div>
                  <div className="kpi-value" style={{ color: 'var(--success)' }}>{fmt(result.total_generation_kwh, 0)} kWh</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Total Demand</div>
                  <div className="kpi-value" style={{ color: 'var(--warning)' }}>{result.total_demand_kwh > 0 ? `${fmt(result.total_demand_kwh, 0)} kWh` : 'N/A'}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Net Balance</div>
                  <div className="kpi-value" style={{ color: statusColor }}>{fmt(result.net_balance_kwh, 0)} kWh</div>
                  <div className="kpi-sub" style={{ textTransform: 'capitalize' }}>{result.balance_status}</div>
                </div>
              </div>

              <div className="card">
                <div className="section-label">Recommendation</div>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>{result.recommendation}</p>
                <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                  Gen adj: {form.generation_adjustment_pct}% · Demand adj: {form.demand_adjustment_pct}% · Period: {form.analysis_start} → {form.analysis_end}
                </p>
              </div>

              {plotData.length > 0 && (
                <PlotWrapper data={plotData}
                  layout={{ barmode: 'group', title: { text: 'Generation vs Demand', font: { color: '#e2e8f0' } }, xaxis: { title: 'Date' }, yaxis: { title: 'kWh' } }}
                  style={{ minHeight: 280 }} />
              )}
            </>
          ) : (
            <div className="card empty-state">
              Configure parameters and click "Run scenario" to see results.
            </div>
          )}
        </div>
      </div>

      {/* History */}
      {history.length > 0 && (
        <div className="card" style={{ marginTop: '1.25rem' }}>
          <div className="section-label">Scenario History</div>
          <table>
            <thead><tr><th>Name</th><th>Period</th><th>Gen (kWh)</th><th>Demand (kWh)</th><th>Net (kWh)</th><th>Status</th></tr></thead>
            <tbody>
              {history.map(s => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{s.analysis_start} → {s.analysis_end}</td>
                  <td>{fmt(s.total_generation_kwh, 0)}</td>
                  <td>{s.total_demand_kwh > 0 ? fmt(s.total_demand_kwh, 0) : '—'}</td>
                  <td style={{ color: s.net_balance_kwh >= 0 ? 'var(--success)' : 'var(--danger)' }}>{fmt(s.net_balance_kwh, 0)}</td>
                  <td style={{ textTransform: 'capitalize', fontSize: '0.8rem' }}>{s.balance_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
