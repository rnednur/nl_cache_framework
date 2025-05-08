"use client"

import { useState } from "react"
import Link from "next/link"
import { Home, Database, Search, Upload } from "lucide-react"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <div className={`border-r bg-white ${isSidebarOpen ? 'w-64' : 'w-0'} transition-all duration-200 overflow-hidden`}>
        <div className="p-6">
          <h2 className="text-xl font-bold">NL Cache</h2>
        </div>
        <nav className="px-3 py-2">
          <ul className="space-y-2">
            <li>
              <Link 
                href="/dashboard"
                className="py-1.5 px-3 rounded hover:bg-slate-100 flex items-center gap-2"
              >
                <Home className="h-4 w-4" />
                Dashboard
              </Link>
            </li>
            <li>
              <Link 
                href="/cache-entries"
                className="py-1.5 px-3 rounded hover:bg-slate-100 flex items-center gap-2"
              >
                <Database className="h-4 w-4" />
                Cache Entries
              </Link>
            </li>
            <li>
              <Link 
                href="/complete-test"
                className="py-1.5 px-3 rounded hover:bg-slate-100 flex items-center gap-2"
              >
                <Search className="h-4 w-4" />
                Test Completion
              </Link>
            </li>
            <li>
              <Link 
                href="/data-upload"
                className="py-1.5 px-3 rounded hover:bg-slate-100 flex items-center gap-2"
              >
                <Upload className="h-4 w-4" />
                Data Upload
              </Link>
            </li>
          </ul>
        </nav>
      </div>
      
      {/* Main content */}
      <div className="flex-1 bg-slate-50">
        {/* Header */}
        <header className="h-16 border-b bg-white px-6 flex items-center justify-between">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 rounded hover:bg-slate-100"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="4" x2="20" y1="12" y2="12" />
              <line x1="4" x2="20" y1="6" y2="6" />
              <line x1="4" x2="20" y1="18" y2="18" />
            </svg>
          </button>
          <div>NL Cache Framework</div>
        </header>
        
        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
} 