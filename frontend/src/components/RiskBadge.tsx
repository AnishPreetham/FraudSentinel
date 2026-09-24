import React from 'react'
import type { RiskLevel } from '../types'
import clsx from 'clsx'

const colors: Record<RiskLevel, string> = {
  LOW: 'bg-green-900/50 text-green-300 border border-green-700',
  MEDIUM: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700',
  HIGH: 'bg-red-900/50 text-red-300 border border-red-700',
  CRITICAL: 'bg-red-700 text-white border border-red-500 animate-pulse',
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span className={clsx('px-2 py-1 rounded text-xs font-bold uppercase tracking-wide', colors[level])}>
      {level}
    </span>
  )
}
