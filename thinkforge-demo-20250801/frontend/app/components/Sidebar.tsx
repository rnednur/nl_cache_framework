"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  BarChart2, 
  Code, 
  Database, 
  FileText, 
  Grid, 
  Settings,
  Sparkles
} from "lucide-react"
import { cn } from "../lib/utils"

const navItems = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: <Grid className="h-5 w-5" />
  },
  {
    name: "Cache Entries",
    href: "/cache-entries",
    icon: <Database className="h-5 w-5" />
  },
  {
    name: "Templates",
    href: "/templates",
    icon: <Code className="h-5 w-5" />
  },
  {
    name: "Complete Test",
    href: "/complete-test",
    icon: <Sparkles className="h-5 w-5" />
  },
  {
    name: "Documentation",
    href: "/documentation",
    icon: <FileText className="h-5 w-5" />
  },
  {
    name: "Statistics",
    href: "/statistics",
    icon: <BarChart2 className="h-5 w-5" />
  },
  {
    name: "Settings",
    href: "/settings",
    icon: <Settings className="h-5 w-5" />
  }
]

export default function Sidebar() {
  const pathname = usePathname()
  
  return (
    <div className="hidden md:flex w-64 flex-col bg-white border-r border-slate-200 h-screen">
      <div className="p-6">
        <div className="flex flex-col">
          <h1 className="text-2xl font-bold text-slate-900">ThinkForge</h1>
          <span className="text-xs text-slate-500">Natural Language Cache Framework</span>
        </div>
      </div>
      <nav className="flex-1 px-4 py-2 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || 
            (item.href !== "/dashboard" && pathname?.startsWith(item.href))
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center px-4 py-3 text-slate-600 rounded-md group transition-colors",
                isActive ? "bg-slate-100 text-slate-900" : "hover:bg-slate-100"
              )}
            >
              <span className={cn(
                "mr-3 text-slate-500", 
                isActive && "text-slate-700"
              )}>
                {item.icon}
              </span>
              <span className="font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
} 