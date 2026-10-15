import { useQuery } from '@tanstack/react-query'
import { getQualityReports } from '../services/api'
import PageHeader from '../components/PageHeader'
import KpiCard from '../components/KpiCard'
import StatusBadge from '../components/StatusBadge'
import { format } from 'date-fns'

function fmt(v) { return v != null ? Number(v).toLocaleString() : '—' }

function parseJSON(s, fallback = {}) {
  if (!s) return fallback
  try { return JSON.parse(s) } catch { return fallback }
}

export default function DataQuality() {
  const { data: reports = [], isLoading, error } = useQuery({
    queryKey: ['quality-reports'],
    queryFn: () => getQualityReports({ limit: 10 }),
  })

  const latest = reports[0]
  const missingness = parseJSON(latest?.column_missingness, {})
  const issuesObj = parseJSON(latest?.validation_issues, {})
  const issues = issuesObj.issues || []
  const warnings = issuesObj.warnings || []

  if (isLoading) return <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '4rem' }}><span className="spinner" /></div>
  if (error) return <div className="error-state">Failed to load quality reports: {error.message}</div>

  return (
    <div>
      <PageHeader title="Data Quality" subtitle="Validation results from the most recent pipeline runs" />

      {!latest ? (
        <div className="empty-state">
          No data quality reports yet. Ingest a dataset using the Pipeline page.
        </div>
      ) : (
        <>
          <div className="kpi-grid">
            <KpiCard label="Quality Score" value={`${latest.quality_score ?? '—'}%`}
              accent={latest.readiness_status === 'good' ? 'success' : latest.readiness_status === 'warning' ? 'warning' : 'danger'}
              sub={<StatusBadge value={latest.readiness_status} />} />
            <KpiCard label="Total Rows" value={fmt(latest.total_rows)} />
            <KpiCard label="Missing Rows" value={fmt(latest.missing_rows)}
              accent={latest.missing_rows > 0 ? 'warning' : 'success'} />
            <KpiCard label="Duplicates" value={fmt(latest.duplicate_rows)}
              accent={latest.duplicate_rows > 0 ? 'warning' : 'success'} />
            <KpiCard label="Out-of-range" value={fmt(latest.out_of_range_values)}
              accent={latest.out_of_range_values > 0 ? 'warning' : 'success'} />
            <KpiCard label="Time Gaps" value={fmt(latest.time_gap_count)}
              accent={latest.time_gap_count > 0 ? 'warning' : 'success'} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            {/* Column missingness */}
            <div className="card">
              <div className="section-label">Column Missingness</div>
              {Object.keys(missingness).length > 0 ? (
                <table>
                  <thead><tr><th>Column</th><th>Missing rows</th><th>% Missing</th></tr></thead>
                  <tbody>
                    {Object.entries(missingness).map(([col, count]) => (
                      <tr key={col}>
                        <td style={{ fontFamily: 'monospace' }}>{col}</td>
                        <td>{fmt(count)}</td>
                        <td style={{ color: 'var(--warning)' }}>
                          {latest.total_rows > 0 ? `${((count / latest.total_rows) * 100).toFixed(1)}%` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ color: 'var(--success)', fontSize: '0.875rem' }}>No column missingness detected.</p>
              )}
            </div>

            {/* Issues & warnings */}
            <div className="card">
              <div className="section-label">Validation Issues</div>
              {issues.length === 0 && warnings.length === 0 ? (
                <p style={{ color: 'var(--success)', fontSize: '0.875rem' }}>No issues or warnings.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {issues.map((msg, i) => (
                    <div key={i} className="error-state" style={{ padding: '6px 10px', fontSize: '0.8rem' }}>⛔ {msg}</div>
                  ))}
                  {warnings.map((msg, i) => (
                    <div key={i} style={{ padding: '6px 10px', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 'var(--radius)', fontSize: '0.8rem', color: 'var(--warning)' }}>
                      ⚠ {msg}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Run history */}
          <div className="card">
            <div className="section-label">Quality Report History</div>
            <table>
              <thead>
                <tr><th>Date</th><th>Score</th><th>Status</th><th>Rows</th><th>Missing</th><th>Duplicates</th><th>Gaps</th></tr>
              </thead>
              <tbody>
                {reports.map(r => (
                  <tr key={r.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                      {r.created_at ? format(new Date(r.created_at), 'dd MMM HH:mm') : '—'}
                    </td>
                    <td>{r.quality_score != null ? `${r.quality_score}%` : '—'}</td>
                    <td><StatusBadge value={r.readiness_status} /></td>
                    <td>{fmt(r.total_rows)}</td>
                    <td>{fmt(r.missing_rows)}</td>
                    <td>{fmt(r.duplicate_rows)}</td>
                    <td>{fmt(r.time_gap_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
