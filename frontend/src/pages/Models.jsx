import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getEvaluationsSummary, getGenerationForecasts, trainSolarModels, getSources } from '../services/api'
import PageHeader from '../components/PageHeader'
import PlotWrapper from '../components/PlotWrapper'

function fmt(v, d = 4) { return v != null ? Number(v).toFixed(d) : '—' }

export default function Models() {
  const qc = useQueryClient()
  const [sourceId, setSourceId] = useState('')
  const [trainMsg, setTrainMsg] = useState(null)

  const { data: evals = [], isLoading: evalsLoading } = useQuery({
    queryKey: ['evals-summary'],
    queryFn: () => getEvaluationsSummary({ split_name: 'test' }),
  })

  const { data: forecasts = [] } = useQuery({
    queryKey: ['gen-forecasts'],
    queryFn: () => getGenerationForecasts({ forecast_mode: 'test_evaluation', limit: 2000 }),
  })

  const { data: sources = [] } = useQuery({
    queryKey: ['sources'],
    queryFn: getSources,
  })

  const trainMut = useMutation({
    mutationFn: (payload) => trainSolarModels(payload),
    onSuccess: (data) => {
      setTrainMsg({
        ok: true,
        text: `Training complete. ${data.rows_used} rows used. Anomalies detected: ${data.anomalies_detected}.`,
      })
      // TanStack Query v5: invalidateQueries requires { queryKey } object
      qc.invalidateQueries({ queryKey: ['evals-summary'] })
      qc.invalidateQueries({ queryKey: ['gen-forecasts'] })
      qc.invalidateQueries({ queryKey: ['overview'] })
    },
    onError: (err) => setTrainMsg({ ok: false, text: err.message }),
  })

  const withActual = forecasts.filter(f => f.actual_value != null)

  const plotData = []
  if (withActual.length > 0) {
    plotData.push({
      type: 'scatter', mode: 'lines', name: 'Actual',
      x: withActual.map(f => f.forecast_for),
      y: withActual.map(f => f.actual_value),
      line: { color: '#10b981', width: 1.5 },
    })
    plotData.push({
      type: 'scatter', mode: 'lines', name: 'Predicted',
      x: withActual.map(f => f.forecast_for),
      y: withActual.map(f => f.predicted_value),
      line: { color: '#3b82f6', width: 1.5, dash: 'dot' },
    })
  }

  return (
    <div>
      <PageHeader title="Model Evaluation" subtitle="Chronological test-set results for all trained solar generation models" />

      {/* Train panel */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="section-label">Train Solar Forecasting Models</div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Trains linear regression, random forest, and XGBoost on loaded generation data with leakage-safe chronological splits (70 / 15 / 15).
        </p>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <div className="section-label">Data source</div>
            <select value={sourceId} onChange={e => setSourceId(e.target.value)} style={{ minWidth: 200 }}>
              <option value="">Select source…</option>
              {sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <button
            className="btn btn-primary"
            disabled={!sourceId || trainMut.isPending}
            onClick={() => { setTrainMsg(null); trainMut.mutate({ source_id: Number(sourceId), include_weather: true }) }}
          >
            {trainMut.isPending
              ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Training…</>
              : 'Train models'}
          </button>
        </div>
        {trainMsg && (
          <div style={{ marginTop: '0.75rem' }} className={trainMsg.ok ? '' : 'error-state'}>
            {trainMsg.ok
              ? <span style={{ color: 'var(--success)', fontSize: '0.875rem' }}>✓ {trainMsg.text}</span>
              : trainMsg.text}
          </div>
        )}
      </div>

      {/* Comparison table */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="section-label">Test-Set Comparison (lower MAE = better)</div>
        {evalsLoading
          ? <div><span className="spinner" /></div>
          : evals.length === 0
            ? <div className="empty-state" style={{ padding: '1rem 0' }}>No model evaluations yet. Train models above.</div>
            : (
              <table>
                <thead>
                  <tr>
                    <th>Model</th><th>MAE (kWh)</th><th>RMSE (kWh)</th><th>R²</th>
                    <th>Baseline MAE</th><th>vs Baseline</th><th>N samples</th>
                  </tr>
                </thead>
                <tbody>
                  {evals.map((e, i) => (
                    <tr key={i} style={i === 0 ? { background: 'rgba(59,130,246,0.06)' } : {}}>
                      <td style={{ textTransform: 'capitalize', fontWeight: i === 0 ? 600 : 400 }}>
                        {i === 0 ? '🏆 ' : ''}{e.model_type?.replace(/_/g, ' ')}
                      </td>
                      <td style={{ color: i === 0 ? 'var(--success)' : 'inherit' }}>{fmt(e.mae)}</td>
                      <td>{fmt(e.rmse)}</td>
                      <td>{fmt(e.r2)}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{fmt(e.baseline_mae)}</td>
                      <td style={{ color: (e.mae_vs_baseline_pct ?? 0) > 0 ? 'var(--success)' : 'var(--warning)' }}>
                        {e.mae_vs_baseline_pct != null
                          ? `${e.mae_vs_baseline_pct > 0 ? '+' : ''}${e.mae_vs_baseline_pct}%`
                          : '—'}
                      </td>
                      <td>{e.n_samples?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
      </div>

      {/* Feature importances for best model */}
      {evals[0]?.feature_importances && (() => {
        const fi = evals[0].feature_importances
        const sorted = Object.entries(fi).sort((a, b) => b[1] - a[1]).slice(0, 15)
        return (
          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div className="section-label">
              Top Feature Importances — {evals[0].model_type?.replace(/_/g, ' ')}
            </div>
            <PlotWrapper
              data={[{
                type: 'bar', orientation: 'h',
                x: sorted.map(([, v]) => v),
                y: sorted.map(([k]) => k),
                marker: { color: '#3b82f6' },
              }]}
              layout={{ yaxis: { autorange: 'reversed' }, margin: { l: 200, r: 20, t: 10, b: 40 } }}
              style={{ minHeight: 340 }}
            />
          </div>
        )
      })()}

      {/* Actual vs predicted */}
      <PlotWrapper
        data={plotData}
        isLoading={false}
        isEmpty={plotData.length === 0}
        emptyMessage="No test-period forecasts stored yet. Train a model to see results."
        layout={{
          title: { text: 'Actual vs Predicted — Test Period', font: { color: '#e2e8f0' } },
          xaxis: { title: 'Date / Time (UTC)' },
          yaxis: { title: 'Generation (kWh)' },
        }}
        style={{ minHeight: 320 }}
      />

      <p style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        All metrics are from the chronological held-out test set (last 15% of data by time).
        Compared against a seasonal-naïve baseline. Positive "vs Baseline" = MAE improvement.
      </p>
    </div>
  )
}
