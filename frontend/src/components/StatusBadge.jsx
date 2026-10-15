export default function StatusBadge({ value }) {
  if (!value) return null
  // Replace all underscores and spaces with dashes for CSS class
  const cls = `badge badge-${value.toLowerCase().replace(/[\s_]+/g, '-')}`
  return <span className={cls}>{value.replace(/_/g, ' ')}</span>
}
