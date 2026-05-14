import { useState } from 'react'
import { runBenchmark, getBenchmarkHistory } from '../../api/client'
import { Play, Loader } from 'lucide-react'

export function BenchmarkPanel() {
  const [loading, setLoading] = useState(null) // 'cpu' | 'memory' | 'disk'
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)

  async function run(type) {
    setLoading(type)
    setError(null)
    try {
      const res = await runBenchmark(type, { duration: 10 })
      if (res.error) {
        setError(res.error)
      } else {
        setResults(prev => [{ ...res, id: Date.now() }, ...prev.slice(0, 9)])
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="chart-card">
      <h3>Benchmarks</h3>
      <div className="bench-buttons">
        {['cpu', 'memory', 'disk'].map(type => (
          <button
            key={type}
            className="bench-btn"
            onClick={() => run(type)}
            disabled={!!loading}
          >
            {loading === type
              ? <><Loader size={14} className="spin" /> Running…</>
              : <><Play size={14} /> {type.toUpperCase()}</>}
          </button>
        ))}
      </div>

      {error && <div className="bench-error">{error}</div>}

      <div className="bench-results">
        {results.map(r => (
          <div key={r.id} className="bench-result-row">
            <span className="bench-type">{r.type?.toUpperCase()}</span>
            <span className="bench-tool">{r.tool}</span>
            <span className="bench-summary">{r.summary}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
