export function StatCard({ title, value, unit, subtitle, color = '#3b82f6', icon }) {
  return (
    <div className="stat-card">
      <div className="stat-card-header">
        <span className="stat-card-title">{title}</span>
        {icon && <span className="stat-card-icon">{icon}</span>}
      </div>
      <div className="stat-card-value" style={{ color }}>
        {value ?? '—'}<span className="stat-card-unit">{unit}</span>
      </div>
      {subtitle && <div className="stat-card-subtitle">{subtitle}</div>}
    </div>
  )
}
