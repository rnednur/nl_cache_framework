import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import { ThemeProvider } from "@/components/theme-provider"
import { SearchProvider } from "@/contexts/SearchContext"
import { Layout } from "@/components/layout"
import { Toaster } from "react-hot-toast"
import Dashboard from "@/pages/Dashboard"
import CacheEntriesRoutes from "@/pages/CacheEntries"
import DataUpload from "@/pages/DataUpload"
import TestCompletion from "@/pages/TestCompletion"
import UsageLogs from "@/pages/UsageLogs"

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-3xl font-bold text-white">{title}</h1>
}

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      <SearchProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/*" element={<CacheEntriesRoutes />} />
              <Route path="/test-completion" element={<TestCompletion />} />
              <Route path="/data-upload" element={<DataUpload />} />
              <Route path="/usage-logs" element={<UsageLogs />} />
              <Route path="/analytics" element={<Placeholder title="Analytics" />} />
              <Route path="/settings" element={<Placeholder title="Settings" />} />
              {/* 404 fallthrough can go here */}
            </Routes>
          </Layout>
        </Router>
      </SearchProvider>
      <Toaster position="top-right" />
    </ThemeProvider>
  )
}

export default App
