import React from 'react'
import { CheckCircle, Circle, AlertCircle, Clock, Database, Search, Shield, Zap, FileText, GitBranch } from 'lucide-react'
import type { TimelineStep } from '../types'

const STEP_ICONS: Record<string, React.ReactNode> = {
  create_case: <FileText size={14} />,
  graph_investigation: <Database size={14} />,
  collect_evidence: <Search size={14} />,
  retrieve_history: <Clock size={14} />,
  detect_patterns: <Zap size={14} />,
  assess_risk: <Shield size={14} />,
  assess_uncertainty: <AlertCircle size={14} />,
  request_additional_evidence: <Search size={14} />,
  recommend_action: <GitBranch size={14} />,
  check_approval: <Shield size={14} />,
  execute_action: <CheckCircle size={14} />,
  explain_decision: <FileText size={14} />,
  update_case: <CheckCircle size={14} />,
  write_memory: <Database size={14} />,
  approval_received: <CheckCircle size={14} />,
  approval_rejected: <AlertCircle size={14} />,
}

const STEP_LABELS: Record<string, string> = {
  create_case: 'Case Created',
  graph_investigation: 'Graph Investigation',
  collect_evidence: 'Evidence Collection',
  retrieve_history: 'Historical Lookup',
  detect_patterns: 'Pattern Detection',
  assess_risk: 'Risk Assessment',
  assess_uncertainty: 'Uncertainty Analysis',
  request_additional_evidence: 'Evidence Request',
  recommend_action: 'Action Recommendation',
  check_approval: 'Approval Check',
  execute_action: 'Action Execution',
  explain_decision: 'Reasoning Generated',
  update_case: 'Case Updated',
  write_memory: 'Memory Stored',
  approval_received: 'Approval Received',
  approval_rejected: 'Approval Rejected',
}

export function InvestigationTrace({ timeline }: { timeline: TimelineStep[] }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm">
        <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
        Investigation in progress...
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {timeline.map((step, i) => {
        const isLast = i === timeline.length - 1
        return (
          <div key={i} className="flex gap-3 animate-slide-in">
            <div className="flex flex-col items-center">
              <div className="w-7 h-7 rounded-full bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-400 flex-shrink-0">
                {STEP_ICONS[step.step] || <Circle size={12} />}
              </div>
              {!isLast && <div className="w-px h-3 bg-slate-600 mt-1" />}
            </div>
            <div className="pb-3 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-blue-300">
                  {STEP_LABELS[step.step] || step.step.replace(/_/g, ' ')}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(step.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">{step.description}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
