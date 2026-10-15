import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSources, createSource, getPipelineRuns, ingestSolarCSV, ingestOpenMeteo } from '../services/api'
import PageHeader from '../components/PageHeader'
import StatusBadge from '../components/StatusBadge'
import { format } from 'date-fns'

const SAMPLE_SOLAR = 'data/samples/solar_generation_sample.csv'

export default function Pipeline() {
  const qc = useQueryClient()
  const [tab, setTab] = useState('sources')
  const [msg, setMsg] = useState(null)

  // Sources
  const { data: sources = [] } = useQuery({ queryKey: ['sources'], queryFn: getSources })
  const [srcForm, setSrcForm] = useState({ name: '', source_type: 'csv', data_category: 'solar_generation', description: '', local_file_path: SAMPLE_SOLAR, units: 'kWh', temporal_resolution: 'hourly', geographic_scope: 'Pune, India' })
  const createSrcMut = useMutation({
    mutationFn: createSource,
    onSuccess: () => { qc.invalidateQueries(['sources']); setMsg({ ok: true, text: 'Source registered.' }) },
    onError: e => setMsg({ ok: false, text: e.message }),
  })

  // Runs
  const { data: runs = [] } = useQuery({ queryKey: ['pipeline-runs'], queryFn: () => getPipelineRuns({ limit: 20 }) })

  // Ingest solar CSV
  const [ingestForm, setIngestForm] = useState({ source_id: '', file_path: SAMPLE_SOLAR, timestamp_col: 'timestamp', generation_col: 'generation_kwh', ghi_col: 'ghi', temperature_col: 'temperature_c', site_id: 'pune_rooftop_100kwp', unit: 'kWh' })
  const ingestMut = useMutation({
    mutationFn: ingestSolarCSV,
    onSuccess: d => { qc.invalidateQueries(['pipeline-runs']); qc.invalidateQueries(['overview']); setMsg({ ok: true, text: `Ingested. ${d.rows_written} rows written. Quality: ${d.quality_score}%` }) },
    onError: e => setMsg({ ok: false, text: e.message }),
  })

  // Open-Meteo
  const [meteoForm, setMeteoForm] = useState({ source_id: '', latitude: 18.52, longitude: 73.86, start_date: '2022-01-01', end_date: '2022-12-31', location_id: 'pune_india' })
  const meteoMut = useMutation({
    mutationFn: ingestOpenMeteo,
    onSuccess: d => { qc.invalidateQueries(['pipeline-runs']); setMsg({ ok: true, text: `Open-Meteo: ${d.rows_written} rows written.` }) },
    onError: e => setMsg({ ok: false, text: e.message }),
  })

  const TABS = [{ k: 'sources', l: 'Data Sources' }, { k: 'ingest', l: 'Ingest Solar CSV' }, { k: 'meteo', l: 'Open-Meteo Weather' }, { k: 'runs', l: 'Run History' }]

  return (
    <div>
      <PageHeader title="Pipeline & Ingestion" subtitle="Register sources, run ETL, and view pipeline logs" />

      {msg && (
        <div style={{ marginBottom: '1rem' }} className={msg.ok ? '' : 'error-state'}>
          {msg.ok ? <span style={{ color: 'var(--success)', fontSize: '0.875rem' }}>✓ {msg.text}</span> : msg.text}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: '1.25rem', borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {TABS.map(t => (
          <button key={t.k} onClick={() => setTab(t.k)}
            className="btn"
            style={{ borderRadius: 'var(--radius) var(--radius) 0 0', borderBottom: tab === t.k ? '2px solid var(--primary)' : '2px solid transparent', color: tab === t.k ? 'var(--primary)' : 'var(--text-muted)', background: 'transparent', padding: '0.4rem 0.9rem' }}>
            {t.l}
          </button>
        ))}
      </div>

      {/* Sources tab */}
      {tab === 'sources' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="card">
            <div className="section-label">Register New Source</div>
            {[['name','Name'],['description','Description'],['local_file_path','Local file path'],['geographic_scope','Geographic scope'],['units','Units'],['temporal_resolution','Resolution']].map(([k,l]) => (
              <div key={k} style={{ marginBottom: '0.75rem' }}>
                <div className="section-label">{l}</div>
                <input value={srcForm[k]} onChange={e => setSrcForm(f => ({ ...f, [k]: e.target.value }))} style={{ width: '100%' }} />
              </div>
            ))}
            <div style={{ marginBottom: '0.75rem' }}>
              <div className="section-label">Category</div>
              <select value={srcForm.data_category} onChange={e => setSrcForm(f => ({ ...f, data_category: e.target.value }))} style={{ width: '100%' }}>
                {['solar_generation','weather','demand'].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" disabled={!srcForm.name || createSrcMut.isPending}
              onClick={() => createSrcMut.mutate(srcForm)}>Register source</button>
          </div>

          <div className="card">
            <div className="section-label">Registered Sources ({sources.length})</div>
            {sources.length === 0
              ? <div className="empty-state" style={{ padding: '1rem 0' }}>No sources yet.</div>
              : <table>
                  <thead><tr><th>ID</th><th>Name</th><th>Category</th><th>Resolution</th></tr></thead>
                  <tbody>
                    {sources.map(s => (
                      <tr key={s.id}>
                        <td style={{ color: 'var(--text-muted)' }}>{s.id}</td>
                        <td>{s.name}</td>
                        <td style={{ fontSize: '0.8rem' }}>{s.data_category}</td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{s.temporal_resolution}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
            }
          </div>
        </div>
      )}

      {/* Ingest solar CSV tab */}
      {tab === 'ingest' && (
        <div className="card" style={{ maxWidth: 600 }}>
          <div className="section-label">Ingest Solar Generation CSV</div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Default path points to the synthetic sample dataset. Replace with a real dataset path once available.
          </p>
          {[['source_id','Source ID (number)'],['file_path','CSV file path'],['timestamp_col','Timestamp column'],['generation_col','Generation column'],['ghi_col','GHI column (optional)'],['temperature_col','Temperature column (optional)'],['site_id','Site ID (optional)']].map(([k,l]) => (
            <div key={k} style={{ marginBottom: '0.75rem' }}>
              <div className="section-label">{l}</div>
              <input value={ingestForm[k]} onChange={e => setIngestForm(f => ({ ...f, [k]: e.target.value }))} style={{ width: '100%' }} />
            </div>
          ))}
          <button className="btn btn-primary" disabled={!ingestForm.source_id || ingestMut.isPending}
            onClick={() => { setMsg(null); ingestMut.mutate({ ...ingestForm, source_id: Number(ingestForm.source_id) }) }}>
            {ingestMut.isPending ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Ingesting…</> : 'Run ingestion'}
          </button>
        </div>
      )}

      {/* Open-Meteo tab */}
      {tab === 'meteo' && (
        <div className="card" style={{ maxWidth: 600 }}>
          <div className="section-label">Fetch Historical Weather — Open-Meteo API</div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Free, no API key required. Fetches hourly weather for a lat/lon from the Open-Meteo archive.
            Default coordinates: Pune, India (18.52°N, 73.86°E).
          </p>
          {[['source_id','Source ID (number)'],['latitude','Latitude'],['longitude','Longitude'],['start_date','Start date (YYYY-MM-DD)'],['end_date','End date (YYYY-MM-DD)'],['location_id','Location ID']].map(([k,l]) => (
            <div key={k} style={{ marginBottom: '0.75rem' }}>
              <div className="section-label">{l}</div>
              <input value={meteoForm[k]} onChange={e => setMeteoForm(f => ({ ...f, [k]: e.target.value }))} style={{ width: '100%' }} />
            </div>
          ))}
          <button className="btn btn-primary" disabled={!meteoForm.source_id || meteoMut.isPending}
            onClick={() => { setMsg(null); meteoMut.mutate({ ...meteoForm, source_id: Number(meteoForm.source_id), latitude: Number(meteoForm.latitude), longitude: Number(meteoForm.longitude) }) }}>
            {meteoMut.isPending ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Fetching…</> : 'Fetch & ingest'}
          </button>
        </div>
      )}

      {/* Runs tab */}
      {tab === 'runs' && (
        <div className="card" style={{ overflowX: 'auto' }}>
          <div className="section-label">Pipeline Run History</div>
          {runs.length === 0
            ? <div className="empty-state" style={{ padding: '1rem 0' }}>No runs yet.</div>
            : <table>
                <thead><tr><th>ID</th><th>Source</th><th>Stage</th><th>Status</th><th>Rows read</th><th>Written</th><th>Rejected</th><th>Completed</th></tr></thead>
                <tbody>
                  {runs.map(r => (
                    <tr key={r.id}>
                      <td style={{ color: 'var(--text-muted)' }}>{r.id}</td>
                      <td>{r.source_id ?? '—'}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{r.pipeline_stage}</td>
                      <td><StatusBadge value={r.status} /></td>
                      <td>{r.rows_read?.toLocaleString()}</td>
                      <td style={{ color: 'var(--success)' }}>{r.rows_written?.toLocaleString()}</td>
                      <td style={{ color: r.rows_rejected > 0 ? 'var(--warning)' : 'inherit' }}>{r.rows_rejected}</td>
                      <td style={{ fontSize: '0.78rem' }}>{r.completed_at ? format(new Date(r.completed_at), 'dd MMM HH:mm') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
          }
        </div>
      )}
    </div>
  )
}
