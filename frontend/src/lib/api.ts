import axios from 'axios'
import type { Case } from '../types'

const BASE = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: BASE,
  timeout: 60000,
})

export async function startInvestigation(data: {
  customer_id: string
  account_id: string
  trigger_type: string
  trigger_details: Record<string, unknown>
}): Promise<{ case_id: string; status: string }> {
  const res = await api.post('/cases/investigate', data)
  return res.data
}

export async function getCase(caseId: string): Promise<Case> {
  const res = await api.get(`/cases/${caseId}`)
  return res.data
}

export async function listCases(): Promise<{ cases: Case[] }> {
  const res = await api.get('/cases')
  return res.data
}

export async function submitEvidence(caseId: string, data: {
  evidence_type: string
  source: string
  content: string
  reliability: number
}) {
  const res = await api.post(`/cases/${caseId}/evidence`, data)
  return res.data
}

export async function approveAction(caseId: string, data: {
  approved: boolean
  reason?: string
  approver_id?: string
}) {
  const res = await api.post(`/cases/${caseId}/approve`, data)
  return res.data
}

export async function runDemoScenario(scenarioId: string) {
  const res = await api.post(`/demo/scenario/${scenarioId}`)
  return res.data
}

export async function getDemoScenarios() {
  const res = await api.get('/demo/scenarios')
  return res.data
}

export async function getHealth() {
  const res = await axios.get('/health')
  return res.data
}
