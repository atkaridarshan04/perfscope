import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'

const LINES = [
  { key: 'cpu',     color: '#3b82f6', label: 'CPU %' },
  { key: 'memory',  color: '#10b981', label: 'Memory %' },
  { key: 'swap',    color: '#f59e0b', label: 'Swap %' },
  { key: 'io_wait', color: '#ef4444', label: 'IO Wait %' },
]

export function MetricsChart({ history }) {
  return (
    <div className="chart-card">
      <h3>Real-time Metrics</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={history} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d2d2d" />
          <XAxis dataKey="time" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ background: '#1e1e1e', border: '1px solid #333' }}
            labelStyle={{ color: '#aaa' }}
          />
          <Legend />
          {LINES.map(l => (
            <Line key={l.key} type="monotone" dataKey={l.key} name={l.label}
              stroke={l.color} dot={false} strokeWidth={2} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
