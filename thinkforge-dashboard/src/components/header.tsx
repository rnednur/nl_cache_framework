import { Button } from "@/components/ui/button"
import { Search } from "./search"
import { PlusCircle, Bell, User } from "lucide-react"

export function Header() {
  return (
    <header className="flex items-center justify-between p-4 border-b border-[#2a2a4a] bg-[#1e1e38]">
      <h1 className="text-xl font-semibold text-white">Dashboard</h1>
      <div className="flex items-center gap-4">
        <Search />
        <Button size="icon" variant="ghost" className="relative text-slate-400 hover:text-white hover:bg-[#2a2a4a]">
          <Bell className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-orange-500 text-[10px] font-medium flex items-center justify-center text-white">
            3
          </span>
        </Button>
        <Button size="icon" variant="ghost" className="text-slate-400 hover:text-white hover:bg-[#2a2a4a]">
          <User className="h-5 w-5" />
        </Button>
        <Button size="sm" className="gap-2 bg-blue-600 hover:bg-blue-700 text-white">
          <PlusCircle className="h-4 w-4" />
          Create Cache Entry
        </Button>
      </div>
    </header>
  )
}
