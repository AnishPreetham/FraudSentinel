import React, { useState } from 'react'
import { Shield, CheckCircle, Clock, AlertTriangle, Zap, ChevronRight } from 'lucide-react'
import type { Recommendation, RiskLevel } from '../types'
import { approveAction } from '../lib/api'

const ACTION_ICONS: Record<string, React.ReactNode> = {
  block_account: <Shield size={20} className="text-red-400" />,
  block_transaction: <Shield size={20} className="text-orange-400" />,
  escalate_to_analyst: <AlertTriangle size={20} className="text-yellow-400" />,
  monitor_account: <Clock size={20} className="text-blue-400" />,
  step_up_authentication: <Zap size={20} className="text-purple-400" />,
  warn_customer: <AlertTriangle size={20} className="text-yellow-400" />,
  allow_transaction: <CheckCircle size={20} className="text-green-400" />,
  file_sar_report: <Shield size={20} className="text-red-400" />,
}

const ACTION_LABELS: Record<string, string> = {
  block_account: 'Block Account',
  block_transaction: 'Block Transaction',
  escalate_to_analyst: 'Escalate to Analyst',
  monitor_account: 'Enhanced Monitoring',
  step_up_authentication: 'Step-Up Authentication',
  warn_customer: 'Warn Customer',
  allow_transaction: 'Allow Transaction',
  file_sar_report: 'File SAR Report',
  freeze_and_investigate: 'Freeze & Investigate',
}

interface ActionCardProps {
  recommendation: Recommendation
  caseId: string
  onApproved?: () => void
}

export function ActionCard({ recommendation: rec, caseId, onApproved }: ActionCardProps) {
  const [loading, setLoading] = useState(false)
  const [localStatus, setLocalStatus] = useState(rec.execution_status)

  const actionLabel = ACTION_LABELS[rec.action] || rec.action?.replace(/_/g, ' ') || 'Review'
  const icon = ACTION_ICONS[rec.action] || <Shield size={20} />

  const confidence = Math.round((rec.confidence || 0) * 100)
  const riskColor = {
    LOW: 'text-green-400', MEDIUM: 'text-yellow-400', HIGH: 'text-red-400', CRITICAL: 'text-red-500'
  }[rec.risk_level as RiskLevel] || 'text-slate-300'

  async function handleApprove(approved: boolean) {
    setLoading(true)
    try {
      await approveAction(caseId, { approved, reason: approved ? 'Analyst approved' : 'Analyst rejected', approver_id: 'analyst' })
      setLocalStatus(approved ? 'EXECUTED' : 'REJECTED')
      onApproved?.()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (!rec.action) {
    return (
      <div className="bg-slate-700/30 rounded-xl p-4 text-center text-slate-400 text-sm">
        No recommendation yet — investigation in progress
      </div>
    )
  }

  return (
    <div className="bg-slate-800/50 border border-slate-600 rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-slate-700 flex items-center justify-center">
          {icon}
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">{actionLabel}</h3>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`text-xs font-medium ${riskColor}`}>{rec.risk_level} RISK</span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs text-slate-400">{confidence}% confidence</span>
          </div>
        </div>

        {/* Status indicator */}
        <div className="ml-auto">
          {localStatus === 'AUTO_EXECUTED' || localStatus === 'EXECUTED' ? (
            <span className="px-3 py-1 bg-green-900/50 text-green-300 border border-green-700 rounded-full text-xs font-bold">
              ✓ Executed
            </span>
          ) : localStatus === 'PENDING_APPROVAL' ? (
            <span className="px-3 py-1 bg-orange-900/50 text-orange-300 border border-orange-700 rounded-full text-xs font-bold animate-pulse">
              Awaiting Approval
            </span>
          ) : localStatus === 'REJECTED' ? (
            <span className="px-3 py-1 bg-red-900/50 text-red-300 border border-red-700 rounded-full text-xs font-bold">
              Rejected
            </span>
          ) : (
            <span className="px-3 py-1 bg-blue-900/50 text-blue-300 border border-blue-700 rounded-full text-xs font-bold">
              Recommended
            </span>
          )}
        </div>
      </div>

      {/* Reason */}
      <p className="text-sm text-slate-300 leading-relaxed">{rec.reason}</p>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Confidence</span>
          <span>{confidence}%</span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${confidence >= 80 ? 'bg-green-500' : confidence >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>

      {/* Evidence list */}
      {rec.supporting_evidence?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Evidence</h4>
          <ul className="space-y-1">
            {rec.supporting_evidence.slice(0, 4).map((e, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                <ChevronRight size={12} className="text-blue-400 mt-0.5 flex-shrink-0" />
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Policy basis */}
      {rec.policy_basis && (
        <div className="bg-slate-700/30 rounded p-2 border border-slate-600">
          <p className="text-xs text-slate-400">
            <span className="font-medium text-slate-300">Policy: </span>{rec.policy_basis}
          </p>
        </div>
      )}

      {/* Approval buttons */}
      {rec.requires_approval && localStatus === 'PENDING_APPROVAL' && (
        <div className="flex gap-3 pt-2">
          <button
            onClick={() => handleApprove(true)}
            disabled={loading}
            className="flex-1 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white font-semibold py-2 rounded-lg text-sm transition-colors"
          >
            {loading ? '...' : '✓ Approve & Execute'}
          </button>
          <button
            onClick={() => handleApprove(false)}
            disabled={loading}
            className="flex-1 bg-slate-600 hover:bg-slate-500 disabled:opacity-50 text-white font-semibold py-2 rounded-lg text-sm transition-colors"
          >
            Reject
          </button>
        </div>
      )}

      {rec.requires_approval && localStatus === 'RECOMMENDED' && (
        <div className="flex gap-3 pt-2">
          <button
            onClick={() => handleApprove(true)}
            disabled={loading}
            className="flex-1 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white font-semibold py-2 rounded-lg text-sm transition-colors"
          >
            {loading ? '...' : `Approve (requires ${rec.approver_role || 'analyst'})`}
          </button>
        </div>
      )}
    </div>
  )
}
