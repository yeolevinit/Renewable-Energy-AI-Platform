export default function KpiCard({ label, value, sub, accent }) {
  const color = accent === 'success' ? 'var(--success)'
              : accent === 'warning' ? 'var(--warning)'
              : accent === 'danger'  ? 'var(--danger)'
              : accent === 'purple'  ? 'var(--purple)'
              : 'var(--primary)'

  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color }}>{value ?? '—'}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}
