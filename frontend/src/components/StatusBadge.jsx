export default function StatusBadge({ value }) {
  if (!value) return null
  const cls = `badge badge-${value.toLowerCase().replace(' ', '-')}`
  return <span className={cls}>{value}</span>
}
