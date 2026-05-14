export function ProcessTable({ processes = [] }) {
  return (
    <div className="chart-card">
      <h3>Top Processes by CPU</h3>
      <div className="table-wrapper">
        <table className="proc-table">
          <thead>
            <tr>
              <th>PID</th>
              <th>Name</th>
              <th>CPU %</th>
              <th>Mem %</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {processes.map(p => (
              <tr key={p.pid}>
                <td>{p.pid}</td>
                <td className="proc-name">{p.name}</td>
                <td style={{ color: p.cpu_percent > 50 ? '#ef4444' : '#10b981' }}>
                  {(p.cpu_percent ?? 0).toFixed(1)}%
                </td>
                <td>{(p.memory_percent ?? 0).toFixed(1)}%</td>
                <td><span className={`status-badge ${p.status}`}>{p.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
