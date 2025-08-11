import { Search } from "lucide-react"

export function Header() {
  return (
    <header className="h-14 border-b border-[#2a2a4a] bg-[#1e1e38] px-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-white">Natural Language Cache Framework</h1>
      </div>
      <div className="flex items-center gap-3">
        <div className="relative w-60">
          <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            <Search className="h-4 w-4 text-slate-400" />
          </div>
          <input
            type="search"
            className="w-full py-2 pl-10 pr-4 bg-[#2a2a4a] border border-[#3a3a5e] rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Search..."
            disabled
          />
        </div>
      </div>
    </header>
  )
} 