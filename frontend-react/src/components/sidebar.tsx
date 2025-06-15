import { Link, useLocation } from "react-router-dom"
import { LayoutDashboard, Database, TestTube, Upload, Menu, Settings, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import { Logo } from "./logo"
import { ThemeToggle } from "./theme-toggle"

export function Sidebar() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const toggleSidebar = () => {
    setCollapsed(!collapsed)
  }

  return (
    <div
      className={cn(
        "border-r bg-[#1e1e38] transition-all duration-300 h-screen flex flex-col",
        collapsed ? "w-16" : "w-52",
      )}
    >
      <div className="p-4 border-b border-[#2a2a4a] flex items-center justify-between">
        {!collapsed && (
          <Link to="/" className="flex items-center">
            <Logo collapsed={collapsed} />
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn(
            "h-8 w-8 text-slate-400 hover:text-white hover:bg-[#2a2a4a]", 
            collapsed && "mx-auto"
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <Menu className="h-4 w-4" />
        </Button>
      </div>
      <nav className="flex-1 p-2">
        <div className={cn("mb-3", collapsed ? "px-2" : "px-3")}>
          <ul className="space-y-0.5">
            <NavItem
              to="/"
              icon={<LayoutDashboard className="h-4 w-4" />}
              label="Dashboard"
              active={location.pathname === "/"}
              collapsed={collapsed}
            />
            <NavItem
              to="/cache-entries"
              icon={<Database className="h-4 w-4" />}
              label="Cache Entries"
              active={location.pathname === "/cache-entries"}
              collapsed={collapsed}
            />
            <NavItem
              to="/test-completion"
              icon={<TestTube className="h-4 w-4" />}
              label="Test Completion"
              active={location.pathname === "/test-completion"}
              collapsed={collapsed}
            />
            <NavItem
              to="/data-upload"
              icon={<Upload className="h-4 w-4" />}
              label="Data Upload"
              active={location.pathname === "/data-upload"}
              collapsed={collapsed}
            />
          </ul>
        </div>

        <div className={cn("mb-3", collapsed ? "px-2" : "px-3")}>
          <ul className="space-y-0.5">
            <NavItem
              to="/usage-logs"
              icon={<Clock className="h-4 w-4" />}
              label="Usage Logs"
              active={location.pathname === "/usage-logs"}
              collapsed={collapsed}
            />
          </ul>
        </div>
      </nav>
      <div className="p-4 border-t border-[#2a2a4a] flex items-center justify-between">
        {!collapsed && <ThemeToggle />}
        <NavItem
          to="/settings"
          icon={<Settings className="h-4 w-4" />}
          label="Settings"
          active={location.pathname === "/settings"}
          collapsed={collapsed}
          className="w-full"
        />
      </div>
    </div>
  )
}

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
  collapsed: boolean;
  className?: string;
}

function NavItem({ to, icon, label, active, collapsed, className }: NavItemProps) {
  return (
    <li className={className}>
      <Link
        to={to}
        className={cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
          active ? "bg-[#3a3a5e] text-white" : "text-slate-400 hover:bg-[#2a2a4a] hover:text-white",
          collapsed && "justify-center px-2",
        )}
        title={collapsed ? label : undefined}
      >
        {icon}
        {!collapsed && <span>{label}</span>}
      </Link>
    </li>
  )
} 