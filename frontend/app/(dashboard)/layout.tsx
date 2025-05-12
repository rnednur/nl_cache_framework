"use client"

import { useState } from "react"
import Link from "next/link"
import { Home, Database, Search, Upload, Menu, ChevronLeft, Brain, Zap, FileText, Settings, BarChart2, ClipboardList } from "lucide-react"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  
  return (
    <div className="flex min-h-screen bg-neutral-800">
      {/* Sidebar */}
      <div className={`fixed h-full z-30 border-r border-neutral-700 bg-neutral-900 transition-all duration-300 ease-in-out ${isSidebarOpen ? 'w-64' : 'w-0 sm:w-16'}`}>
        <div className={`p-6 flex items-center justify-between ${isSidebarOpen ? '' : 'p-4'}`}>
          <div className="flex items-center gap-2">
            <div className={`transition-all duration-200 relative ${isSidebarOpen ? '' : 'mx-auto'}`}>
              <Brain className="h-9 w-9 text-[#3B4BF6]" />
              <Zap className="h-5 w-5 text-[#F97316] absolute -bottom-0.5 -right-1" strokeWidth={2.5} />
            </div>
            {isSidebarOpen && (
              <div className="flex flex-col">
                <span className="font-bold text-2xl ml-1">
                  <span className="text-[#3B4BF6]">Think</span>
                  <span className="text-[#F97316]">Forge</span>
                </span>
                <span className="text-xs text-[#94A3B8] ml-1">Natural Language Cache Framework</span>
              </div>
            )}
          </div>
          <button 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)} 
            className={`rounded-full p-1.5 bg-neutral-800 hover:bg-neutral-700 transition-all duration-300 ${isSidebarOpen ? 'ml-auto' : 'mx-auto'}`}
          >
            <ChevronLeft className={`h-4 w-4 text-neutral-400 transition-transform duration-300 ${isSidebarOpen ? 'rotate-0' : 'rotate-180'}`} />
          </button>
        </div>
        <nav className={`px-3 py-2 ${isSidebarOpen ? '' : 'px-2'}`}>
          <ul className="space-y-2">
            <li>
              <Link 
                href="/dashboard"
                className={`py-1.5 rounded hover:bg-neutral-800 flex items-center ${isSidebarOpen ? 'px-3 gap-2' : 'justify-center px-2'}`}
                title="Dashboard"
              >
                <Home className="h-4 w-4 text-neutral-400" />
                <span className={`text-neutral-300 transition-opacity duration-200 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 hidden sm:hidden'}`}>
                  Dashboard
                </span>
              </Link>
            </li>
            <li>
              <Link 
                href="/cache-entries"
                className={`py-1.5 rounded hover:bg-neutral-800 flex items-center ${isSidebarOpen ? 'px-3 gap-2' : 'justify-center px-2'}`}
                title="Cache Entries"
              >
                <Database className="h-4 w-4 text-neutral-400" />
                <span className={`text-neutral-300 transition-opacity duration-200 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 hidden sm:hidden'}`}>
                  Cache Entries
                </span>
              </Link>
            </li>
            <li>
              <Link 
                href="/complete-test"
                className={`py-1.5 rounded hover:bg-neutral-800 flex items-center ${isSidebarOpen ? 'px-3 gap-2' : 'justify-center px-2'}`}
                title="Test Completion"
              >
                <Search className="h-4 w-4 text-neutral-400" />
                <span className={`text-neutral-300 transition-opacity duration-200 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 hidden sm:hidden'}`}>
                  Test Completion
                </span>
              </Link>
            </li>
            <li>
              <Link 
                href="/data-upload"
                className={`py-1.5 rounded hover:bg-neutral-800 flex items-center ${isSidebarOpen ? 'px-3 gap-2' : 'justify-center px-2'}`}
                title="Data Upload"
              >
                <Upload className="h-4 w-4 text-neutral-400" />
                <span className={`text-neutral-300 transition-opacity duration-200 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 hidden sm:hidden'}`}>
                  Data Upload
                </span>
              </Link>
            </li>
            <li>
              <Link 
                href="/statistics"
                className={`py-1.5 rounded hover:bg-neutral-800 flex items-center ${isSidebarOpen ? 'px-3 gap-2' : 'justify-center px-2'}`}
                title="Statistics"
              >
                <BarChart2 className="h-4 w-4 text-neutral-400" />
                <span className={`text-neutral-300 transition-opacity duration-200 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 hidden sm:hidden'}`}>
                  Statistics
                </span>
              </Link>
            </li>
            <li>
              <Link 
                href="/usage-logs"
                className={`py-1.5 rounded hover:bg-neutral-800 flex items-center ${isSidebarOpen ? 'px-3 gap-2' : 'justify-center px-2'}`}
                title="Usage Logs"
              >
                <ClipboardList className="h-4 w-4 text-neutral-400" />
                <span className={`text-neutral-300 transition-opacity duration-200 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 hidden sm:hidden'}`}>
                  Usage Logs
                </span>
              </Link>
            </li>
          </ul>
          
          {/* Settings at the bottom */}
          <div className="absolute bottom-8 w-full left-0 px-3">
            <ul>
              <li>
                <Link 
                  href="/settings"
                  className={`py-1.5 rounded hover:bg-neutral-800 flex items-center ${isSidebarOpen ? 'px-3 gap-2' : 'justify-center px-2'}`}
                  title="Settings"
                >
                  <Settings className="h-4 w-4 text-neutral-400" />
                  <span className={`text-neutral-300 transition-opacity duration-200 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 hidden sm:hidden'}`}>
                    Settings
                  </span>
                </Link>
              </li>
            </ul>
          </div>
        </nav>
      </div>
      
      {/* Main content */}
      <div className={`flex-1 transition-all duration-300 ${isSidebarOpen ? 'ml-64' : 'ml-0 sm:ml-16'}`}>
        {/* Header */}
        <header className="h-16 border-b border-neutral-700 bg-neutral-900 px-6 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 rounded hover:bg-neutral-800 sm:hidden"
            >
              <Menu className="h-5 w-5 text-neutral-400" />
            </button>
            <div className="flex items-center gap-2">
              <div className="relative hidden sm:block md:hidden">
                <Brain className="h-7 w-7 text-[#3B4BF6]" />
                <Zap className="h-4 w-4 text-[#F97316] absolute -bottom-0.5 -right-1" strokeWidth={2.5} />
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="relative w-64">
              <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <Search className="h-4 w-4 text-neutral-400" />
              </div>
              <input
                type="search"
                className="w-full py-2 pl-10 pr-4 bg-neutral-700 border border-neutral-600 rounded-md text-neutral-200 placeholder-neutral-400 focus:outline-none focus:ring-1 focus:ring-[#3B4BF6] focus:border-[#3B4BF6]"
                placeholder="Search entries..."
              />
            </div>
          </div>
        </header>
        
        {/* Page content */}
        <main className="p-6 bg-neutral-800 text-slate-200 min-h-screen">
          {children}
        </main>
      </div>
    </div>
  )
} 