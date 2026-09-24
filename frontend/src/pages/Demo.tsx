import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, AlertTriangle, Shield, Zap, ArrowLeft, CheckCircle } from 'lucide-react'
import { runDemoScenario } from '../lib/api'

const SCENARIOS = [
  {
    id: 'scenario_a',
    title: 'Connected Fraud Ring',
    subtitle: 'Money Laundering',
    badge: 'HIGH RISK',
    badgeColor: 'bg-red-700 text-white',
    icon: <Shield size={24} className="text-red-400" />,
    description: 'Customer C-001 initiates structured wire transfers of $4,800–$4,900 (below $5,000 reporting threshold) to 3 connected accounts — all sharing the same device fingerprint D-001. Classic money laundering ring with layering pattern.',
    expectedAction: 'block_account',
    expectedPatterns: ['MONEY_LAUNDERING', 'VELOCITY_ABUSE'],
    bgGradient: 'from-red-900/20 to-transparent',
  },
  {
    id: 'scenario_b',
    title: 'Ambiguous New Customer',
    subtitle: 'Step-Up Auth Required',
    badge: 'MEDIUM RISK',
    badgeColor: 'bg-yellow-600 text-white',
    icon: <AlertTriangle size={24} className="text-yellow-400" />,
    description: 'Customer C-002 (12 days old, KYC pending) attempts first large transaction of $8,500 at a jewelry store. Agent has insufficient evidence — requests step-up authentication. Customer passes → transaction cleared.',
    expectedAction: 'step_up_authentication',
    expectedPatterns: [],
    bgGradient: 'from-yellow-900/20 to-transparent',
  },
  {
    id: 'scenario_c',
    title: 'Account Takeover',
    subtitle: 'Requires Analyst Approval',
    badge: 'CRITICAL',
    badgeColor: 'bg-red-600 text-white animate-pulse',
    icon: <Zap size={24} className="text-red-300" />,
    description: 'Customer C-003 (verified, 720-day account, good standing) suddenly logs in from a new device in Eastern Europe. Immediately initiates $12,500 and $8,900 transfers. Classic ATO — agent recommends immediate block pending analyst approval.',
    expectedAction: 'block_account',
    expectedPatterns: ['ACCOUNT_TAKEOVER'],
    bgGradient: 'from-red-900/30 to-transparent',
  },
]

export function Demo() {
  const navigate = useNavigate()
  const [running, setRunning] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, { case_id: string; status: string; risk_level: string }>>({})

  async function launchScenario(scenarioId: string) {
    setRunning(scenarioId)
    try {
      const result = await runDemoScenario(scenarioId)
      setResults(r => ({ ...r, [scenarioId]: result }))
      if (result.case_id) {
        setTimeout(() => navigate(`/cases/${result.case_id}`), 800)
      }
    } catch (e) {
      console.error(e)
      setRunning(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#0f172a] text-[#f1f5f9]">
      {/* Header */}
      <header className="bg-[#1e293b] border-b border-slate-700 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-slate-400 hover:text-white">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-lg font-bold text-white">Demo Mode</h1>
            <p className="text-xs text-slate-400">Pre-built scenarios with synthetic data</p>
          </div>
        </div>
      </header>

      {/* Demo banner */}
      <div className="bg-yellow-900/30 border-b border-yellow-700/50 px-6 py-2 text-center">
        <span className="text-yellow-300 text-sm font-semibold">
          ⚠ DEMO MODE — Using synthetic data. No real accounts affected.
        </span>
      </div>

      <main className="max-w-5xl mx-auto px-6 py-10 space-y-6">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Choose a Demo Scenario</h2>
          <p className="text-slate-400 text-sm">Each scenario runs the full LangGraph agentic investigation workflow end-to-end</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SCENARIOS.map(s => {
            const result = results[s.id]
            const isRunning = running === s.id

            return (
              <div
                key={s.id}
                className={`bg-gradient-to-b ${s.bgGradient} bg-[#1e293b] border border-slate-700 rounded-2xl p-6 space-y-4 hover:border-slate-500 transition-all`}
              >
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 rounded-xl bg-slate-700 flex items-center justify-center">
                    {s.icon}
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${s.badgeColor}`}>{s.badge}</span>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-white">{s.title}</h3>
                  <p className="text-xs text-slate-400 font-medium mt-0.5">{s.subtitle}</p>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed">{s.description}</p>

                <div className="space-y-1.5">
                  <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Expected outcome</p>
                  <div className="flex items-center gap-2">
                    <CheckCircle size={12} className="text-blue-400" />
                    <span className="text-xs text-blue-300">{s.expectedAction.replace(/_/g, ' ')}</span>
                  </div>
                  {s.expectedPatterns.map(p => (
                    <div key={p} className="flex items-center gap-2">
                      <div className="w-3 h-1 bg-red-500 rounded" />
                      <span className="text-xs text-slate-400">{p.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>

                {result ? (
                  <div className="bg-green-900/30 border border-green-700 rounded-lg p-3 text-center">
                    <CheckCircle size={16} className="text-green-400 mx-auto mb-1" />
                    <p className="text-xs text-green-300 font-semibold">Redirecting to case...</p>
                    <p className="text-xs text-green-400 font-mono mt-0.5">{result.case_id}</p>
                  </div>
                ) : (
                  <button
                    onClick={() => launchScenario(s.id)}
                    disabled={!!running}
                    className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 disabled:opacity-60 text-white font-semibold py-3 rounded-xl text-sm transition-colors"
                  >
                    {isRunning ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Investigating...
                      </>
                    ) : (
                      <>
                        <Play size={14} />
                        Launch Scenario
                      </>
                    )}
                  </button>
                )}
              </div>
            )
          })}
        </div>

        <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-6">
          <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wide mb-3">How it works</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            {[
              { step: '1', label: 'TigerGraph\nTraversal', desc: 'Graph neighborhood exploration' },
              { step: '2', label: 'Evidence\nCollection', desc: 'Multi-source evidence gathering' },
              { step: '3', label: 'Pattern\nDetection', desc: 'Deterministic fraud pattern matching' },
              { step: '4', label: 'Policy-Validated\nAction', desc: 'Next-best-action with approval workflow' },
            ].map(s => (
              <div key={s.step} className="space-y-1">
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white text-sm font-bold flex items-center justify-center mx-auto">
                  {s.step}
                </div>
                <p className="text-xs font-semibold text-white whitespace-pre-line">{s.label}</p>
                <p className="text-xs text-slate-400">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
