import { useQuery } from '@tanstack/react-query'
import { getOverview } from '../services/api'
import KpiCard from '../components/KpiCard'
import PageHeader from '../components/PageHeader'
import StatusBadge from '../components/StatusBadge'
import { format } from 'date-fns'

function fmt(val, digits = 0) {
  if (val == null) return '—'
  return Number(val).toLocaleString(undefined, { maximumFractionDigits: digits })
}

function fmtDate(d) {
  if (!d) return '—'
  try { return format(new Date(d), 'dd MMM yyyy HH:mm') } catch { return d }
}

export default function Overview() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: getOverview,
    refetchInterval: 60_000,
  })

  if (isLoading) return (
    <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '4rem' }}>
      <span className="spinner" />
    </div>
  )

  if (error) return (
    <div className="error-state">
      Failed to load overview: {error.message}
    </div>
  )

  const gen   = data?.generation_data   || {}
  const run   = data?.latest_pipeline_run || {}
  const qual  = data?.data_quality      || {}
  const anom  = data?.anomalies         || {}
  const model = data?.best_model        || {}

  return (
    <div>
      <PageHeader
        title="Platform Overview"
        subtitle="Current state of data pipelines, quality, forecasts and alerts"
      />

      <div className="kpi-grid">
        <KpiCard
          label="Generation Records"
          value={fmt(gen.total_rows)}
          sub={gen.latest ? `Latest: ${fmtDate(gen.latest)}` : 'No data loaded'}
          accent="primary"
        />
        <KpiCard
          label="Data Quality Score"
          value={qual.quality_score != null ? `${qual.quality_score}%` : '—'}
          sub={<StatusBadge value={qual.readiness_status} />}
          accent={qual.readiness_status === 'good' ? 'success' : qual.readiness_status === 'warning' ? 'warning' : 'danger'}
        />
        <KpiCard
          label="Open Alerts"
          value={fmt(anom.open_count)}
          sub={anom.high_severity_count > 0 ? `${anom.high_severity_count} high severity` : 'None high severity'}
          accent={anom.open_count > 0 ? 'warning' : 'success'}
        />
        <KpiCard
          label="Best Model MAE"
          value={model.test_mae != null ? fmt(model.test_mae, 3) : '—'}
          sub={model.model_type ? `${model.model_type} (test set)` : 'No models trained'}
          accent="purple"
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        {/* Pipeline status */}
        <div className="card">
          <div className="section-label">Latest Pipeline Run</div>
          {run.id ? (
            <table>
              <tbody>
                <tr><td style={{ color: 'var(--text-muted)' }}>Status</td><td><StatusBadge value={run.status} /></td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>Completed</td><td>{fmtDate(run.completed_at)}</td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>Rows written</td><td>{fmt(run.rows_written)}</td></tr>
              </tbody>
            </table>
          ) : (
            <div className="empty-state" style={{ padding: '1rem 0' }}>No pipeline runs yet. Load a dataset to begin.</div>
          )}
        </div>

        {/* Generation coverage */}
        <div className="card">
          <div className="section-label">Generation Data Coverage</div>
          {gen.total_rows > 0 ? (
            <table>
              <tbody>
                <tr><td style={{ color: 'var(--text-muted)' }}>Earliest record</td><td>{fmtDate(gen.earliest)}</td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>Latest record</td><td>{fmtDate(gen.latest)}</td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>Total rows</td><td>{fmt(gen.total_rows)}</td></tr>
              </tbody>
            </table>
          ) : (
            <div className="empty-state" style={{ padding: '1rem 0' }}>
              No generation data. Use the Pipeline page to ingest a CSV or fetch Open-Meteo weather data.
            </div>
          )}
        </div>

        {/* Model summary */}
        <div className="card">
          <div className="section-label">Best Forecast Model (Test Set)</div>
          {model.model_type ? (
            <table>
              <tbody>
                <tr><td style={{ color: 'var(--text-muted)' }}>Model type</td><td style={{ textTransform: 'capitalize' }}>{model.model_type?.replace('_', ' ')}</td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>Version</td><td style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{model.version_tag}</td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>Test MAE</td><td>{fmt(model.test_mae, 4)} kWh</td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>Test RMSE</td><td>{fmt(model.test_rmse, 4)} kWh</td></tr>
              </tbody>
            </table>
          ) : (
            <div className="empty-state" style={{ padding: '1rem 0' }}>No models trained. Ingest data and use the Models page.</div>
          )}
        </div>

        {/* Anomaly summary */}
        <div className="card">
          <div className="section-label">Anomaly Alert Summary</div>
          {anom.open_count != null ? (
            <table>
              <tbody>
                <tr><td style={{ color: 'var(--text-muted)' }}>Open alerts</td><td>{fmt(anom.open_count)}</td></tr>
                <tr><td style={{ color: 'var(--text-muted)' }}>High severity</td><td style={{ color: anom.high_severity_count > 0 ? 'var(--danger)' : 'inherit' }}>{fmt(anom.high_severity_count)}</td></tr>
              </tbody>
            </table>
          ) : (
            <div className="empty-state" style={{ padding: '1rem 0' }}>Run anomaly detection after training models.</div>
          )}
        </div>
      </div>

      <p style={{ marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        ⚠ This platform is an academic prototype using historical data. All forecasts and recommendations are advisory only and must not be used for operational grid decisions.
      </p>
    </div>
  )
}
