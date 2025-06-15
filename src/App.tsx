import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from '@/components/Layout'
import CacheEntries from '@/pages/CacheEntries'
import CacheEntryDetail from '@/pages/CacheEntryDetail'
import CreateEntry from '@/pages/CreateEntry'
import Statistics from '@/pages/Statistics'
import CompleteTest from '@/pages/CompleteTest'
import UsageLogs from '@/pages/UsageLogs'

function App() {
  return (
    <>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/cache-entries" replace />} />
            <Route path="/cache-entries" element={<CacheEntries />} />
            <Route path="/cache-entries/:id" element={<CacheEntryDetail />} />
            <Route path="/create-entry" element={<CreateEntry />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/complete-test" element={<CompleteTest />} />
            <Route path="/usage-logs" element={<UsageLogs />} />
          </Routes>
        </Layout>
      </Router>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'hsl(var(--background))',
            color: 'hsl(var(--foreground))',
            border: '1px solid hsl(var(--border))',
          },
        }}
      />
    </>
  )
}

export default App 