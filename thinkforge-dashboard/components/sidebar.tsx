"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Database, TestTube, Upload, Menu, Settings, BarChart3, Users } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import { Logo } from "@/components/logo"
import { ThemeToggle } from "@/components/theme-toggle"

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  const toggleSidebar = () => {
    setCollapsed(!collapsed)
  }

  return (
    <div
      className={cn(
        "border-r bg-[#1e1e38] transition-all duration-300 h-screen flex flex-col",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="p-4 border-b border-[#2a2a4a] flex items-center justify-between">
        <Link href="/" className="flex items-center">
          <Logo collapsed={collapsed} />
        </Link>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn("h-8 w-8 text-slate-400 hover:text-white hover:bg-[#2a2a4a]", collapsed && "mx-auto")}
        >
          <Menu className="h-4 w-4" />
        </Button>
      </div>
      <nav className="flex-1 p-2">
        <div className={cn("mb-4", collapsed ? "px-2" : "px-3")}>
          {!collapsed && <p className="text-xs font-semibold text-slate-500 mb-2">MAIN</p>}
          <ul className="space-y-1">
            <NavItem
              href="/"
              icon={<LayoutDashboard className="h-4 w-4" />}
              label="Dashboard"
              active={pathname === "/"}
              collapsed={collapsed}
            />
            <NavItem
              href="/cache-entries"
              icon={<Database className="h-4 w-4" />}
              label="Cache Entries"
              active={pathname === "/cache-entries"}
              collapsed={collapsed}
            />
            <NavItem
              href="/test-completion"
              icon={<TestTube className="h-4 w-4" />}
              label="Test Completion"
              active={pathname === "/test-completion"}
              collapsed={collapsed}
            />
            <NavItem
              href="/data-upload"
              icon={<Upload className="h-4 w-4" />}
              label="Data Upload"
              active={pathname === "/data-upload"}
              collapsed={collapsed}
            />
          </ul>
        </div>

        <div className={cn("mb-4", collapsed ? "px-2" : "px-3")}>
          {!collapsed && <p className="text-xs font-semibold text-slate-500 mb-2">ANALYTICS</p>}
          <ul className="space-y-1">
            <NavItem
              href="/analytics"
              icon={<BarChart3 className="h-4 w-4" />}
              label="Analytics"
              active={pathname === "/analytics"}
              collapsed={collapsed}
            />
            <NavItem
              href="/users"
              icon={<Users className="h-4 w-4" />}
              label="Users"
              active={pathname === "/users"}
              collapsed={collapsed}
            />
          </ul>
        </div>
      </nav>
      <div className="p-4 border-t border-[#2a2a4a] flex items-center justify-between">
        {!collapsed && <ThemeToggle />}
        <NavItem
          href="/settings"
          icon={<Settings className="h-4 w-4" />}
          label="Settings"
          active={pathname === "/settings"}
          collapsed={collapsed}
          className="w-full"
        />
      </div>
    </div>
  )
}

function NavItem({ href, icon, label, active, collapsed, className }) {
  return (
    <li className={className}>
      <Link
        href={href}
        className={cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
          active ? "bg-[#3a3a5e] text-white" : "text-slate-400 hover:bg-[#2a2a4a] hover:text-white",
          collapsed && "justify-center px-2",
        )}
      >
        {icon}
        {!collapsed && <span>{label}</span>}
      </Link>
    </li>
  )
}
