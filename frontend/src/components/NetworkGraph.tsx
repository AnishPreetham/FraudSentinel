import React, { useMemo, useRef, useCallback } from 'react'
import type { Case, GraphNode, GraphLink } from '../types'

const NODE_COLORS: Record<string, string> = {
  customer: '#3b82f6',
  account: '#8b5cf6',
  transaction: '#f59e0b',
  device: '#22c55e',
  ip: '#06b6d4',
  merchant: '#f97316',
}

function buildGraphData(c: Case): { nodes: GraphNode[]; links: GraphLink[] } {
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []

  nodes.push({ id: c.customer_id, type: 'customer', label: c.customer_id })

  const graphData = c.graph_data || {}
  const connectedAccounts = (graphData.connected_accounts as Array<{ account_id: string; suspicious?: boolean }>) || []
  const sharedDevices = (graphData.shared_devices as Array<{ device_id: string; suspicious?: boolean }>) || []
  const sharedIps = (graphData.entities as { shared_ips?: Array<{ ip: string; suspicious?: boolean }> })?.shared_ips || []

  connectedAccounts.forEach((acc) => {
    nodes.push({ id: acc.account_id, type: 'account', label: acc.account_id, suspicious: acc.suspicious })
    links.push({ source: c.customer_id, target: acc.account_id, suspicious: acc.suspicious })
  })

  if (!connectedAccounts.find(a => a.account_id === c.account_id)) {
    nodes.push({ id: c.account_id, type: 'account', label: c.account_id })
    links.push({ source: c.customer_id, target: c.account_id })
  }

  sharedDevices.forEach((dev) => {
    nodes.push({ id: dev.device_id, type: 'device', label: dev.device_id, suspicious: dev.suspicious })
    connectedAccounts.forEach(acc => {
      links.push({ source: acc.account_id, target: dev.device_id, suspicious: dev.suspicious })
    })
  })

  sharedIps.forEach((ip) => {
    nodes.push({ id: ip.ip, type: 'ip', label: ip.ip, suspicious: ip.suspicious })
    links.push({ source: c.account_id, target: ip.ip, suspicious: ip.suspicious })
  })

  return { nodes, links }
}

export function NetworkGraph({ caseData }: { caseData: Case }) {
  const { nodes, links } = useMemo(() => buildGraphData(caseData), [caseData])

  // Simple SVG force-like static layout
  const layout = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {}
    const center = { x: 250, y: 200 }
    const customer = nodes.find(n => n.type === 'customer')
    if (customer) positions[customer.id] = center

    const accounts = nodes.filter(n => n.type === 'account')
    accounts.forEach((n, i) => {
      const angle = (i * 2 * Math.PI) / accounts.length
      positions[n.id] = { x: center.x + 130 * Math.cos(angle), y: center.y + 100 * Math.sin(angle) }
    })

    const devices = nodes.filter(n => n.type === 'device')
    devices.forEach((n, i) => {
      positions[n.id] = { x: 80 + i * 40, y: 50 }
    })

    const ips = nodes.filter(n => n.type === 'ip')
    ips.forEach((n, i) => {
      positions[n.id] = { x: 400 + i * 40, y: 50 }
    })

    nodes.filter(n => !positions[n.id]).forEach((n, i) => {
      positions[n.id] = { x: 100 + i * 60, y: 350 }
    })

    return positions
  }, [nodes])

  const LEGEND = [
    { color: '#3b82f6', label: 'Customer' },
    { color: '#8b5cf6', label: 'Account' },
    { color: '#22c55e', label: 'Device' },
    { color: '#06b6d4', label: 'IP Address' },
  ]

  return (
    <div className="relative w-full" style={{ minHeight: 420 }}>
      <svg width="100%" viewBox="0 0 500 420" className="w-full">
        <defs>
          <marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#475569" />
          </marker>
        </defs>

        {/* Links */}
        {links.map((link, i) => {
          const s = layout[link.source as string]
          const t = layout[link.target as string]
          if (!s || !t) return null
          return (
            <line
              key={i}
              x1={s.x} y1={s.y} x2={t.x} y2={t.y}
              stroke={link.suspicious ? '#ef4444' : '#334155'}
              strokeWidth={link.suspicious ? 2 : 1}
              strokeDasharray={link.suspicious ? '4,2' : undefined}
              opacity={0.8}
            />
          )
        })}

        {/* Nodes */}
        {nodes.map(node => {
          const pos = layout[node.id]
          if (!pos) return null
          const color = node.suspicious ? '#ef4444' : NODE_COLORS[node.type] || '#94a3b8'
          const size = node.type === 'customer' ? 22 : 14
          return (
            <g key={node.id}>
              {node.suspicious && (
                <circle cx={pos.x} cy={pos.y} r={size + 6} fill={color} opacity={0.15} />
              )}
              <circle cx={pos.x} cy={pos.y} r={size} fill={color} fillOpacity={0.85} stroke={color} strokeWidth={2} />
              <text x={pos.x} y={pos.y + size + 12} textAnchor="middle" fontSize={9} fill="#94a3b8">
                {node.label.length > 10 ? node.label.slice(0, 10) + '…' : node.label}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-2 right-2 bg-slate-800/80 rounded p-2 space-y-1">
        {LEGEND.map(l => (
          <div key={l.label} className="flex items-center gap-1.5 text-xs text-slate-300">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: l.color }} />
            {l.label}
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs text-red-400">
          <div className="w-2.5 h-1 bg-red-500" style={{ borderTop: '2px dashed #ef4444' }} />
          Suspicious
        </div>
      </div>
    </div>
  )
}
