import { useMetrics } from './hooks/useMetrics'
import { StatCard } from './components/cards/StatCard'
import { BottleneckAlert } from './components/cards/BottleneckAlert'
import { MetricsChart } from './components/charts/MetricsChart'
import { CpuCoresChart } from './components/charts/CpuCoresChart'
import { ProcessTable } from './components/panels/ProcessTable'
import { BenchmarkPanel } from './components/panels/BenchmarkPanel'
import { ProfilerPanel } from './components/panels/ProfilerPanel'
import { Wifi, WifiOff } from 'lucide-react'
import './App.css'

export default function App() {
  const { latest, history, bottlenecks, connected } = useMetrics()

  const cpu = latest?.cpu
  const mem = latest?.memory
  const disk = latest?.disk
  const load = latest?.load
  const net = latest?.network

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <span className="header-logo">⚡</span>
          <h1>Linux Performance Dashboard</h1>
        </div>
        <div className={`conn-badge ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
          {connected ? 'Live' : 'Reconnecting…'}
        </div>
      </header>

      <main className="app-main">
        <BottleneckAlert bottlenecks={bottlenecks} />

        {/* Stat Cards */}
        <div className="stat-grid">
          <StatCard title="CPU Usage" value={cpu?.percent?.toFixed(1)} unit="%" color="#3b82f6"
            subtitle={`${cpu?.freq_mhz} MHz · ${cpu?.count_logical} cores`} />
          <StatCard title="Memory" value={mem?.percent?.toFixed(1)} unit="%" color="#10b981"
            subtitle={`${mem?.used_gb} / ${mem?.total_gb} GB`} />
          <StatCard title="Swap" value={mem?.swap_percent?.toFixed(1)} unit="%" color="#f59e0b"
            subtitle={`${mem?.swap_used_gb} / ${mem?.swap_total_gb} GB`} />
          <StatCard title="Disk" value={disk?.percent?.toFixed(1)} unit="%" color="#8b5cf6"
            subtitle={`${disk?.used_gb} / ${disk?.total_gb} GB`} />
          <StatCard title="Load Avg" value={load?.avg_1?.toFixed(2)} unit=""
            color="#ec4899" subtitle={`5m: ${load?.avg_5?.toFixed(2)} · 15m: ${load?.avg_15?.toFixed(2)}`} />
          <StatCard title="IO Wait" value={latest?.io_wait?.toFixed(1)} unit="%" color="#ef4444"
            subtitle={`Net ↑${net?.sent_mb} ↓${net?.recv_mb} MB`} />
        </div>

        {/* Charts row */}
        <div className="charts-row">
          <div className="chart-wide">
            <MetricsChart history={history} />
          </div>
          <div className="chart-narrow">
            <CpuCoresChart perCore={cpu?.per_core ?? []} />
          </div>
        </div>

        {/* Bottom panels */}
        <div className="panels-row">
          <ProcessTable processes={latest?.processes ?? []} />
          <BenchmarkPanel />
          <ProfilerPanel />
        </div>
      </main>
    </div>
  )
}
