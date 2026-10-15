/**
 * Thin wrapper around react-plotly.js that applies the platform's dark theme
 * and handles the loading / empty / error states consistently.
 */
import Plot from 'react-plotly.js'

const DARK_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#8892a4', family: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif', size: 12 },
  xaxis: { gridcolor: '#2a2e42', linecolor: '#2a2e42', zerolinecolor: '#2a2e42' },
  yaxis: { gridcolor: '#2a2e42', linecolor: '#2a2e42', zerolinecolor: '#2a2e42' },
  legend: { bgcolor: 'rgba(26,29,39,0.8)', bordercolor: '#2a2e42', borderwidth: 1 },
  margin: { l: 55, r: 20, t: 40, b: 50 },
  colorway: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'],
}

export default function PlotWrapper({
  data,
  layout = {},
  style,
  isLoading,
  isEmpty,
  emptyMessage = 'No data available',
  className = '',
}) {
  if (isLoading) {
    return (
      <div className={`plot-container ${className}`} style={{ ...style, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
        <span className="spinner" />
      </div>
    )
  }

  if (isEmpty || !data || data.length === 0) {
    return (
      <div className={`plot-container ${className}`} style={{ ...style, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={`plot-container ${className}`}>
      <Plot
        data={data}
        layout={{ ...DARK_LAYOUT, ...layout }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '100%', minHeight: style?.minHeight || 280, ...style }}
        useResizeHandler
      />
    </div>
  )
}
