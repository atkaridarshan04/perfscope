import { useState } from 'react'
import { runPerfStat, generateFlamegraph } from '../../api/client'
import { Cpu, Flame, Loader } from 'lucide-react'

export function ProfilerPanel() {
  const [pid, setPid] = useState('')
  const [duration, setDuration] = useState(5)
  const [loading, setLoading] = useState(null)
  const [perfResult, setPerfResult] = useState(null)
  const [flamegraphUrl, setFlamegraphUrl] = useState(null)
  const [error, setError] = useState(null)

  async function handlePerfStat() {
    setLoading('perf')
    setError(null)
    try {
      const res = await runPerfStat(pid || null, duration)
      if (res.error) setError(res.error)
      else setPerfResult(res)
    } catch (e) { setError(e.message) }
    finally { setLoading(null) }
  }

  async function handleFlamegraph() {
    setLoading('flame')
    setError(null)
    try {
      const res = await generateFlamegraph(pid || null, duration)
      if (res.error) setError(res.error)
      else setFlamegraphUrl(res.svg_url)
    } catch (e) { setError(e.message) }
    finally { setLoading(null) }
  }

  return (
    <div className="chart-card">
      <h3>Profiler</h3>
      <div className="profiler-controls">
        <input
          className="profiler-input"
          type="number"
          placeholder="PID (optional, blank = system-wide)"
          value={pid}
          onChange={e => setPid(e.target.value)}
        />
        <input
          className="profiler-input small"
          type="number"
          min={2} max={30}
          value={duration}
          onChange={e => setDuration(Number(e.target.value))}
        />
        <span className="profiler-label">sec</span>
        <button className="bench-btn" onClick={handlePerfStat} disabled={!!loading}>
          {loading === 'perf' ? <><Loader size={14} className="spin" /> Running…</> : <><Cpu size={14} /> perf stat</>}
        </button>
        <button className="bench-btn flame" onClick={handleFlamegraph} disabled={!!loading}>
          {loading === 'flame' ? <><Loader size={14} className="spin" /> Recording…</> : <><Flame size={14} /> FlameGraph</>}
        </button>
      </div>

      {error && <div className="bench-error">{error}</div>}

      {perfResult?.parsed && (
        <div className="perf-stat-grid">
          {Object.entries(perfResult.parsed).map(([k, v]) => (
            <div key={k} className="perf-stat-item">
              <span className="perf-stat-key">{k.replace(/_/g, ' ')}</span>
              <span className="perf-stat-val">{v.toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      {flamegraphUrl && (
        <div className="flamegraph-container">
          <h4>FlameGraph</h4>
          <iframe
            src={flamegraphUrl}
            title="FlameGraph"
            className="flamegraph-frame"
            sandbox="allow-scripts"
          />
        </div>
      )}
    </div>
  )
}
