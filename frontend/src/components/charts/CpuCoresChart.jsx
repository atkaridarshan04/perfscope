import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'

export function CpuCoresChart({ perCore = [] }) {
  const data = perCore.map((v, i) => ({ core: `C${i}`, usage: v }))
  return (
    <div className="chart-card">
      <h3>Per-Core CPU Usage</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d2d2d" />
          <XAxis dataKey="core" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ background: '#1e1e1e', border: '1px solid #333' }}
            formatter={(v) => [`${v}%`, 'Usage']}
          />
          <Bar dataKey="usage" fill="#3b82f6" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
