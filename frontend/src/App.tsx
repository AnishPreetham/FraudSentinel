import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { CaseView } from './pages/CaseView'
import { CaseList } from './pages/CaseList'
import { Demo } from './pages/Demo'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/cases" element={<CaseList />} />
      <Route path="/cases/:id" element={<CaseView />} />
      <Route path="/demo" element={<Demo />} />
    </Routes>
  )
}
