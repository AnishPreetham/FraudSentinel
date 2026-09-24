import React from 'react'
import type { CaseStatus } from '../types'
import clsx from 'clsx'

const styles: Record<CaseStatus, string> = {
  NEW: 'bg-slate-700 text-slate-300',
  INVESTIGATING: 'bg-blue-900/60 text-blue-300 animate-pulse',
  AWAITING_EVIDENCE: 'bg-yellow-900/60 text-yellow-300',
  UNDER_REVIEW: 'bg-purple-900/60 text-purple-300',
  ACTION_RECOMMENDED: 'bg-orange-900/60 text-orange-300',
  PENDING_APPROVAL: 'bg-orange-700 text-white',
  ACTION_EXECUTED: 'bg-green-900/60 text-green-300',
  ESCALATED: 'bg-red-900/60 text-red-300',
  RESOLVED: 'bg-green-700 text-white',
  CLEARED: 'bg-slate-600 text-slate-200',
}

const labels: Record<CaseStatus, string> = {
  NEW: 'New',
  INVESTIGATING: 'Investigating',
  AWAITING_EVIDENCE: 'Awaiting Evidence',
  UNDER_REVIEW: 'Under Review',
  ACTION_RECOMMENDED: 'Action Recommended',
  PENDING_APPROVAL: 'Pending Approval',
  ACTION_EXECUTED: 'Action Executed',
  ESCALATED: 'Escalated',
  RESOLVED: 'Resolved',
  CLEARED: 'Cleared',
}

export function StatusBadge({ status }: { status: CaseStatus }) {
  return (
    <span className={clsx('px-2 py-1 rounded text-xs font-medium', styles[status])}>
      {labels[status] || status}
    </span>
  )
}
