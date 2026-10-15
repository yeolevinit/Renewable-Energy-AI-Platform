import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAnomalies, getAnomalySummary, updateAlertStatus } from '../services/api'
import PageHeader from '../components/PageHeader'
import KpiCard from '../components/KpiCard'
import StatusBadge from '../components/StatusBadge'
import PlotWrapper from '../components/PlotWrapper'
import { format } from 'date-fns'

export default function Anomalies() {
  const qc = useQueryClient()
  const [severity, setSeverity] = useState('')
  const [reviewStatus, setReviewStatus] = useState('open')
  const [updatingId, setUpdatingId] = useState(null)

  const params = { severity: severity || undefined, review_status: reviewStatus || undefined, limit: 200 }

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ['anomalies', params],
    queryFn: () => getAnomalies(params),
  })

  const { data: summary } = useQuery({
    queryKey: ['anomaly-summary'],
    queryFn: getAnomalySummary,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, status }) => updateAlertStatus(id, { review_status: status }),
    onSuccess: () => {
      setUpdatingId(null)
      qc.invalidateQueries({ queryKey: ['anomalies'] })
      qc.invalidateQueries({ queryKey: ['anomaly-summary'] })
      qc.invalidateQueries({ queryKey: ['overview'] })
    },
  })

  const bySeverity = summary?.by_severity || {}
  const byStatus = summary?.by_status || {}

  // Scatter plot of alerts over time
  const alertSeries = ['high', 'medium', 'low'].map(sev => {
    const sub = alerts.filter(a => a.severity === sev)
    return {
      type: 'scatter', mode: 'markers',
      name: sev.charAt(0).toUpperCase() + sev.slice(1),
      x: sub.map(a => a.observed_at),
      y: sub.map(a => a.observed_value ?? 0),
      marker: {
        color: sev === 'high' ? '#ef4444' : sev === 'medium' ? '#f59e0b' : '#10b981',
        size: 8,
        symbol: 'circle',
      },
    }
  }).filter(s => s.x.length > 0)

  return (
    <div>
      <PageHeader
        title="Anomaly Monitoring"
        subtitle="Unusual patterns flagged in generation data. An alert indicates investigation is recommended — it does not confirm a fault."
      />

      <div className="kpi-grid">
        <KpiCard label="Total Alerts" value={summary?.total ?? '—'} accent="primary" />
        <KpiCard label="High Severity" value={bySeverity.high ?? 0} accent="danger" />
        <KpiCard label="Medium Severity" value={bySeverity.medium ?? 0} accent="warning" />
        <KpiCard label="Open" value={byStatus.open ?? 0}
          accent={(byStatus.open ?? 0) > 0 ? 'warning' : 'success'} />
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <div className="section-label">Severity</div>
          <select value={severity} onChange={e => setSeverity(e.target.value)}>
            <option value="">All severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div>
          <div className="section-label">Review status</div>
          <select value={reviewStatus} onChange={e => setReviewStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="reviewed">Reviewed</option>
            <option value="resolved">Resolved</option>
            <option value="false_positive">False positive</option>
          </select>
        </div>
      </div>

      <PlotWrapper
        data={alertSeries}
        isLoading={isLoading}
        isEmpty={alertSeries.length === 0}
        emptyMessage="No anomaly alerts match the current filters."
        layout={{
          title: { text: 'Anomaly Alerts Over Time', font: { color: '#e2e8f0' } },
          xaxis: { title: 'Timestamp (UTC)' },
          yaxis: { title: 'Observed Value (kWh)' },
        }}
        style={{ minHeight: 280 }}
      />

      {/* Alert table */}
      <div className="card" style={{ marginTop: '1rem', overflowX: 'auto' }}>
        {isLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}><span className="spinner" /></div>
        ) : alerts.length === 0 ? (
          <div className="empty-state">No alerts match the current filters.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Timestamp</th><th>Severity</th><th>Observed</th><th>Expected</th>
                <th>Score</th><th>Method</th><th>Status</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map(a => (
                <tr key={a.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}>{a.observed_at?.slice(0, 19)}</td>
                  <td><StatusBadge value={a.severity} /></td>
                  <td>{a.observed_value?.toFixed(3) ?? '—'}</td>
                  <td>{a.expected_value?.toFixed(3) ?? '—'}</td>
                  <td>{a.anomaly_score?.toFixed(2) ?? '—'}</td>
                  <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{a.detection_method?.replace(/_/g, ' ')}</td>
                  <td><StatusBadge value={a.review_status} /></td>
                  <td>
                    {a.review_status === 'open' && (
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                          disabled={updatingId === a.id}
                          onClick={() => { setUpdatingId(a.id); updateMut.mutate({ id: a.id, status: 'reviewed' }) }}
                        >Review</button>
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                          disabled={updatingId === a.id}
                          onClick={() => { setUpdatingId(a.id); updateMut.mutate({ id: a.id, status: 'false_positive' }) }}
                        >FP</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {alerts.length > 0 && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="section-label">Explanation — first alert</div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
            {alerts[0].explanation || 'No explanation recorded.'}
          </p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            ⚠ An anomaly alert indicates an unusual observation that may warrant investigation. It does not confirm equipment failure or a physical fault.
          </p>
        </div>
      )}
    </div>
  )
}
