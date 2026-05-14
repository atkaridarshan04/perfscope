import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = 'ws://localhost:8000/ws/metrics'
const MAX_HISTORY = 60 // keep 60 data points (~2 min at 2s interval)

export function useMetrics() {
  const [latest, setLatest] = useState(null)
  const [history, setHistory] = useState([])
  const [bottlenecks, setBottlenecks] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      setTimeout(connect, 3000) // auto-reconnect
    }
    ws.onerror = () => ws.close()

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      const { metrics, bottlenecks } = data
      setLatest(metrics)
      setBottlenecks(bottlenecks)
      setHistory(prev => {
        const point = {
          time: new Date(metrics.timestamp * 1000).toLocaleTimeString(),
          cpu: metrics.cpu.percent,
          memory: metrics.memory.percent,
          swap: metrics.memory.swap_percent,
          io_wait: metrics.io_wait ?? 0,
          load: metrics.load.avg_1,
        }
        return [...prev.slice(-(MAX_HISTORY - 1)), point]
      })
    }
  }, [])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return { latest, history, bottlenecks, connected }
}
