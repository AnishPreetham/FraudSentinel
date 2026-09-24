import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Shield, AlertTriangle, Clock, CheckCircle, Plus, Play, TrendingUp } from 'lucide-react'
import { listCases, startInvestigation } from '../lib/api'
import { RiskBadge } from '../components/RiskBadge'
import { StatusBadge } from '../components/StatusBadge'
import type { Case, RiskLevel } from '../types'

function StatCard({ title, value, icon, color }: { title: string; value: number; icon: React.ReactNode; color: string }) {
  return (
    <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-slate-400 text-sm font-medium">{title}</span>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>{icon}</div>
      </div>
      <div className="text-3xl font-bold text-white">{value}</div>
    </div>
  )
}

export function Dashboard() {
  const navigate = useNavigate()
  const [showInvForm, setShowInvForm] = useState(false)
  const [form, setForm] = useState({ customer_id: 'C-999', account_id: 'A-999', trigger_type: 'MANUAL', trigger_details: '{}' })
  const [submitting, setSubmitting] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['cases'],
    queryFn: listCases,
    refetchInterval: 10000,
  })

  const cases: Case[] = data?.cases || []

  const stats = {
    active: cases.filter(c => ['INVESTIGATING', 'AWAITING_EVIDENCE', 'UNDER_REVIEW'].includes(c.status)).length,
    highRisk: cases.filter(c => ['HIGH', 'CRITICAL'].includes(c.risk_level)).length,
    awaitingEvidence: cases.filter(c => c.status === 'AWAITING_EVIDENCE').length,
    awaitingApproval: cases.filter(c => c.status === 'PENDING_APPROVAL').length,
  }

  const chartData = [
    { name: 'LOW', count: cases.filter(c => c.risk_level === 'LOW').length, fill: '#22c55e' },
    { name: 'MEDIUM', count: cases.filter(c => c.risk_level === 'MEDIUM').length, fill: '#f59e0b' },
    { name: 'HIGH', count: cases.filter(c => c.risk_level === 'HIGH').length, fill: '#ef4444' },
    { name: 'CRITICAL', count: cases.filter(c => c.risk_level === 'CRITICAL').length, fill: '#dc2626' },
  ]

  async function handleInvestigate(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      let details = {}
      try { details = JSON.parse(form.trigger_details) } catch {}
      const result = await startInvestigation({ ...form, trigger_details: details })
      navigate(`/cases/${result.case_id}`)
    } catch (err) {
      console.error(err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f172a] text-[#f1f5f9]">
      {/* Header */}
      <header className="bg-[#1e293b] border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Shield size={18} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">FraudSentinel</h1>
              <p className="text-xs text-slate-400">TigerGraph Agentic Investigation · HHGOA</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/demo')}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
            >
              <Play size={14} /> Demo Mode
            </button>
            <button
              onClick={() => setShowInvForm(!showInvForm)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
            >
              <Plus size={14} /> Start Investigation
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Investigation form */}
        {showInvForm && (
          <div className="bg-[#1e293b] border border-blue-700/50 rounded-xl p-6 animate-slide-in">
            <h2 className="text-lg font-bold text-white mb-4">Start New Investigation</h2>
            <form onSubmit={handleInvestigate} className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Customer ID</label>
                <input
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white"
                  value={form.customer_id}
                  onChange={e => setForm(f => ({ ...f, customer_id: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Account ID</label>
                <input
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white"
                  value={form.account_id}
                  onChange={e => setForm(f => ({ ...f, account_id: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Trigger Type</label>
                <input
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-white"
                  value={form.trigger_type}
                  onChange={e => setForm(f => ({ ...f, trigger_type: e.target.value }))}
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2 rounded text-sm transition-colors"
                >
                  {submitting ? 'Running...' : 'Investigate'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard title="Active Investigations" value={stats.active} icon={<TrendingUp size={18} />} color="bg-blue-500/20 text-blue-400" />
          <StatCard title="High Risk Cases" value={stats.highRisk} icon={<AlertTriangle size={18} />} color="bg-red-500/20 text-red-400" />
          <StatCard title="Awaiting Evidence" value={stats.awaitingEvidence} icon={<Clock size={18} />} color="bg-yellow-500/20 text-yellow-400" />
          <StatCard title="Awaiting Approval" value={stats.awaitingApproval} icon={<CheckCircle size={18} />} color="bg-orange-500/20 text-orange-400" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Cases table */}
          <div className="md:col-span-2 bg-[#1e293b] border border-slate-700 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-white">Recent Investigations</h2>
              <button onClick={() => navigate('/cases')} className="text-xs text-blue-400 hover:text-blue-300">
                View all →
              </button>
            </div>
            {isLoading ? (
              <div className="text-slate-400 text-sm text-center py-8">Loading...</div>
            ) : cases.length === 0 ? (
              <div className="text-center py-12">
                <Shield size={32} className="text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm">No investigations yet.</p>
                <p className="text-slate-500 text-xs mt-1">Start one above or run a demo scenario.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {cases.slice(0, 8).map(c => (
                  <div
                    key={c.case_id}
                    onClick={() => navigate(`/cases/${c.case_id}`)}
                    className="flex items-center gap-4 p-3 rounded-lg bg-[#263349] hover:bg-slate-600/40 cursor-pointer transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono font-medium text-white">{c.case_id}</span>
                        <RiskBadge level={c.risk_level as RiskLevel} />
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {c.customer_id} · {c.fraud_patterns?.join(', ') || 'Investigating...'}
                      </p>
                    </div>
                    <StatusBadge status={c.status as any} />
                    <span className="text-xs text-slate-500">{Math.round((c.risk_score || 0) * 100)}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Chart */}
          <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-5">
            <h2 className="text-base font-bold text-white mb-4">Cases by Risk Level</h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartData}>
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#f1f5f9' }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <rect key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              {chartData.map(d => (
                <div key={d.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: d.fill }} />
                    <span className="text-slate-400">{d.name}</span>
                  </div>
                  <span className="font-bold text-white">{d.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
