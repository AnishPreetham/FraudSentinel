import React from 'react'
import { CheckCircle, XCircle, HelpCircle } from 'lucide-react'
import type { Evidence } from '../types'

function EvidenceItem({ e, type }: { e: Evidence; type: string }) {
  const Icon = type === 'supporting' ? CheckCircle : type === 'contradicting' ? XCircle : HelpCircle
  const colors = {
    supporting: 'border-green-700/50 bg-green-900/10',
    contradicting: 'border-red-700/50 bg-red-900/10',
    missing: 'border-slate-600 bg-slate-800/30',
  }[type] || 'border-slate-600'

  const iconColors = {
    supporting: 'text-green-400',
    contradicting: 'text-red-400',
    missing: 'text-slate-400',
  }[type] || 'text-slate-400'

  return (
    <div className={`border rounded-lg p-3 ${colors}`}>
      <div className="flex items-start gap-2">
        <Icon size={14} className={`${iconColors} mt-0.5 flex-shrink-0`} />
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-slate-300">
              {e.source?.replace(/_/g, ' ') || 'Unknown'}
            </span>
            <span className="text-xs text-slate-500">
              {Math.round((e.reliability || 0) * 100)}% reliable
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">{e.content}</p>
        </div>
      </div>
    </div>
  )
}

function MissingItem({ text }: { text: string }) {
  return (
    <div className="border border-slate-600 bg-slate-800/30 rounded-lg p-3">
      <div className="flex items-start gap-2">
        <HelpCircle size={14} className="text-slate-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-slate-400">{text}</p>
      </div>
    </div>
  )
}

interface EvidencePanelProps {
  supporting: Evidence[]
  contradicting: Evidence[]
  missing: string[]
}

export function EvidencePanel({ supporting, contradicting, missing }: EvidencePanelProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <h4 className="text-xs font-bold text-green-400 uppercase tracking-wide mb-2 flex items-center gap-1">
          <CheckCircle size={12} /> Supporting ({supporting.length})
        </h4>
        <div className="space-y-2">
          {supporting.length === 0 && <p className="text-xs text-slate-500">No supporting evidence</p>}
          {supporting.map(e => <EvidenceItem key={e.evidence_id} e={e} type="supporting" />)}
        </div>
      </div>
      <div>
        <h4 className="text-xs font-bold text-red-400 uppercase tracking-wide mb-2 flex items-center gap-1">
          <XCircle size={12} /> Contradicting ({contradicting.length})
        </h4>
        <div className="space-y-2">
          {contradicting.length === 0 && <p className="text-xs text-slate-500">No contradicting evidence</p>}
          {contradicting.map(e => <EvidenceItem key={e.evidence_id} e={e} type="contradicting" />)}
        </div>
      </div>
      <div>
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1">
          <HelpCircle size={12} /> Missing ({missing.length})
        </h4>
        <div className="space-y-2">
          {missing.length === 0 && <p className="text-xs text-slate-500">No missing evidence</p>}
          {missing.map((m, i) => <MissingItem key={i} text={m} />)}
        </div>
      </div>
    </div>
  )
}
