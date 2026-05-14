const BASE = '/api'

export async function runBenchmark(type, params = {}) {
  const query = new URLSearchParams(params).toString()
  const res = await fetch(`${BASE}/benchmark/${type}?${query}`, { method: 'POST' })
  return res.json()
}

export async function getBenchmarkHistory() {
  const res = await fetch(`${BASE}/benchmark/history`)
  return res.json()
}

export async function runPerfStat(pid = null, duration = 5) {
  const params = new URLSearchParams({ duration })
  if (pid) params.set('pid', pid)
  const res = await fetch(`${BASE}/profiler/perf-stat?${params}`, { method: 'POST' })
  return res.json()
}

export async function generateFlamegraph(pid = null, duration = 10) {
  const params = new URLSearchParams({ duration })
  if (pid) params.set('pid', pid)
  const res = await fetch(`${BASE}/profiler/flamegraph?${params}`, { method: 'POST' })
  return res.json()
}
