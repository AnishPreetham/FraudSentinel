import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Shield, User, AlertTriangle, RefreshCw } from 'lucide-react'
import { getCase } from '../lib/api'
import { RiskBadge } from '../components/RiskBadge'
import { StatusBadge } from '../components/StatusBadge'
import { InvestigationTrace } from '../components/InvestigationTrace'
import { EvidencePanel } from '../components/EvidencePanel'
import { NetworkGraph } from '../components/NetworkGraph'
import { ActionCard } from '../components/ActionCard'
import type { Case, RiskLevel, Evidence } from '../types'

const PATTERN_LABELS: Record<string, { label: string; color: string }> = {
  ACCOUNT_TAKEOVER: { label: 'Account Takeover', color: 'bg-red-900/50 text-red-300 border-red-700' },
  MONEY_LAUNDERING: { label: 'Money Laundering', color: 'bg-red-900/70 text-red-200 border-red-600' },
  VELOCITY_ABUSE: { label: 'Velocity Abuse', color: 'bg-orange-900/50 text-orange-300 border-orange-700' },
  SYNTHETIC_IDENTITY: { label: 'Synthetic Identity', color: 'bg-purple-900/50 text-purple-300 border-purple-700' },
  FIRST_PARTY_FRAUD: { label: 'First Party Fraud', color: 'bg-yellow-900/50 text-yellow-300 border-yellow-700' },
  CARD_NOT_PRESENT: { label: 'Card Not Present', color: 'bg-blue-900/50 text-blue-300 border-blue-700' },
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-5">
      <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wide mb-4">{title}</h3>
      {children}
    </div>
  )
}

export function CaseView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: caseData, isLoading, refetch } = useQuery<Case>({
    queryKey: ['case', id],
    queryFn: () => getCase(id!),
    refetchInterval: 5000,
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-400">Loading investigation...</p>
        </div>
      </div>
    )
  }

  if (!caseData) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle size={40} className="text-yellow-400 mx-auto mb-3" />
          <p className="text-white font-semibold">Case not found</p>
          <button onClick={() => navigate('/')} className="mt-4 text-blue-400 text-sm">← Back to dashboard</button>
        </div>
      </div>
    )
  }

  const c = caseData
  const allEvidence: Evidence[] = c.evidence || []
  const supporting = allEvidence.filter(e => e.evidence_type === 'supporting')
  const contradicting = allEvidence.filter(e => e.evidence_type === 'contradicting')
  const missing = c.uncertainty?.missing_evidence || []
  const confidence = Math.round((c.confidence || 0) * 100)

  return (
    <div className="min-h-screen bg-[#0f172a] text-[#f1f5f9]">
      {/* Header */}
      <header className="bg-[#1e293b] border-b border-slate-700 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-slate-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-mono font-bold text-white text-lg">{c.case_id}</span>
              <StatusBadge status={c.status} />
              <RiskBadge level={c.risk_level as RiskLevel} />
              {c.fraud_patterns?.map(p => (
                <span key={p} className={`px-2 py-0.5 rounded border text-xs font-medium ${PATTERN_LABELS[p]?.color || 'bg-slate-700 text-slate-300'}`}>
                  {PATTERN_LABELS[p]?.label || p}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
              <span><User size={11} className="inline mr-1" />{c.customer_id}</span>
              <span>Account: {c.account_id}</span>
              <span>Risk Score: {Math.round((c.risk_score || 0) * 100)}%</span>
              <span>Confidence: {confidence}%</span>
            </div>
          </div>
          <button onClick={() => refetch()} className="text-slate-400 hover:text-white transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Error banner */}
        {c.error && (
          <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300 text-sm">
            <strong>Investigation error:</strong> {c.error}
          </div>
        )}

        {/* Confidence meter */}
        <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-slate-300">Investigation Confidence</span>
            <span className="text-sm font-bold text-white">{confidence}%</span>
          </div>
          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${confidence >= 75 ? 'bg-green-500' : confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${confidence}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>LOW</span><span>MEDIUM</span><span>HIGH</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: timeline + action */}
          <div className="space-y-6">
            <Section title="Agent Activity Trace">
              <InvestigationTrace timeline={c.investigation_timeline || []} />
            </Section>
            <Section title="Next Best Action">
              <ActionCard recommendation={c.recommendation} caseId={c.case_id} onApproved={() => refetch()} />
            </Section>
          </div>

          {/* Center: evidence + patterns */}
          <div className="lg:col-span-2 space-y-6">
            <Section title="Evidence Analysis">
              <EvidencePanel supporting={supporting} contradicting={contradicting} missing={missing} />
            </Section>

            {c.fraud_patterns?.length > 0 && (
              <Section title="Fraud Patterns Detected">
                <div className="flex flex-wrap gap-2">
                  {c.fraud_patterns.map(p => (
                    <span key={p} className={`px-3 py-1.5 rounded-lg border text-sm font-semibold ${PATTERN_LABELS[p]?.color || 'bg-slate-700 text-slate-300'}`}>
                      {PATTERN_LABELS[p]?.label || p}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            <Section title="Network Graph">
              <NetworkGraph caseData={c} />
            </Section>

            {c.uncertainty && (
              <Section title="Uncertainty Assessment">
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">{confidence}%</div>
                    <div className="text-xs text-slate-400">Confidence</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${c.uncertainty.uncertainty_level === 'LOW' ? 'text-green-400' : c.uncertainty.uncertainty_level === 'MEDIUM' ? 'text-yellow-400' : 'text-red-400'}`}>
                      {c.uncertainty.uncertainty_level}
                    </div>
                    <div className="text-xs text-slate-400">Uncertainty</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-400">{missing.length}</div>
                    <div className="text-xs text-slate-400">Gaps</div>
                  </div>
                </div>
                {c.uncertainty.fraud_hypotheses?.length > 0 && (
                  <div className="space-y-2">
                    {c.uncertainty.fraud_hypotheses.map((h, i) => (
                      <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded p-2">
                        <span className="text-xs text-slate-300">{h.hypothesis?.replace(/_/g, ' ')}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-1.5 bg-slate-700 rounded-full">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${h.confidence * 100}%` }} />
                          </div>
                          <span className="text-xs text-slate-400 w-12 text-right">{h.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Section>
            )}

            {c.similar_cases?.length > 0 && (
              <Section title="Similar Prior Cases">
                <div className="space-y-3">
                  {c.similar_cases.slice(0, 3).map((sc, i) => (
                    <div key={i} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-mono font-medium text-white">{sc.case_id}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-700 rounded-full">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${sc.similarity * 100}%` }} />
                          </div>
                          <span className="text-xs text-blue-400">{Math.round(sc.similarity * 100)}%</span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-400">{sc.description}</p>
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className={`text-xs px-2 py-0.5 rounded ${sc.outcome === 'FRAUD_CONFIRMED' ? 'bg-red-900/50 text-red-300' : 'bg-green-900/50 text-green-300'}`}>
                          {sc.outcome?.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-slate-500">→ {(sc as any).action_taken?.replace(/_/g, ' ')}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {c.agent_reasoning && (
              <Section title="Agent Reasoning & Case Summary">
                <pre className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-mono bg-slate-800/50 rounded p-4 border border-slate-700">
                  {c.agent_reasoning}
                </pre>
              </Section>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
