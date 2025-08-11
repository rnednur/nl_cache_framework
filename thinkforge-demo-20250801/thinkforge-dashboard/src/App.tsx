import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import { ThemeProvider } from "./components/theme-provider"
import { Layout } from "./components/layout"
import { Dashboard } from "./pages/dashboard"
import { CacheEntries } from "./pages/cache-entries"
import { TestCompletion } from "./pages/test-completion"
import { DataUpload } from "./pages/data-upload"
import { Analytics } from "./pages/analytics"
import { Users } from "./pages/users"
import { Settings } from "./pages/settings"
import "./App.css"

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cache-entries" element={<CacheEntries />} />
            <Route path="/test-completion" element={<TestCompletion />} />
            <Route path="/data-upload" element={<DataUpload />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/users" element={<Users />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  )
}

export default App
