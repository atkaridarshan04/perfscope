import { AlertTriangle, AlertCircle } from 'lucide-react'

export function BottleneckAlert({ bottlenecks }) {
  if (!bottlenecks?.length) return null

  return (
    <div className="bottleneck-container">
      {bottlenecks.map((b, i) => (
        <div key={i} className={`bottleneck-alert ${b.severity}`}>
          {b.severity === 'critical'
            ? <AlertCircle size={16} />
            : <AlertTriangle size={16} />}
          <span>{b.message}</span>
        </div>
      ))}
    </div>
  )
}
