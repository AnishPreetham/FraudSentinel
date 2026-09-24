import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Shield } from 'lucide-react'
import { listCases } from '../lib/api'
import { RiskBadge } from '../components/RiskBadge'
import { StatusBadge } from '../components/StatusBadge'
import type { Case, RiskLevel } from '../types'

export function CaseList() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({ queryKey: ['cases'], queryFn: listCases, refetchInterval: 10000 })
  const cases: Case[] = data?.cases || []

  return (
    <div className="min-h-screen bg-[#0f172a] text-[#f1f5f9]">
      <header className="bg-[#1e293b] border-b border-slate-700 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-slate-400 hover:text-white"><ArrowLeft size={20} /></button>
          <h1 className="text-lg font-bold text-white">All Cases</h1>
          <span className="text-slate-400 text-sm">({cases.length} total)</span>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">
        {isLoading ? (
          <div className="text-slate-400 text-center py-16">Loading...</div>
        ) : cases.length === 0 ? (
          <div className="text-center py-20">
            <Shield size={40} className="text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">No cases yet. Start an investigation or run a demo scenario.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {cases.map(c => (
              <div
                key={c.case_id}
                onClick={() => navigate(`/cases/${c.case_id}`)}
                className="bg-[#1e293b] border border-slate-700 rounded-xl p-4 hover:border-slate-500 cursor-pointer transition-all grid grid-cols-6 gap-4 items-center"
              >
                <span className="font-mono font-bold text-white text-sm col-span-1">{c.case_id}</span>
                <div className="flex gap-2"><RiskBadge level={c.risk_level as RiskLevel} /></div>
                <StatusBadge status={c.status as any} />
                <span className="text-sm text-slate-400">{c.customer_id}</span>
                <span className="text-xs text-slate-500">{c.fraud_patterns?.join(', ') || '—'}</span>
                <span className="text-xs text-slate-400 text-right">{Math.round((c.risk_score || 0) * 100)}% risk</span>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
