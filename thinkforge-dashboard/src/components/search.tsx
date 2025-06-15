"use client"

import { SearchIcon } from "lucide-react"
import { Input } from "@/components/ui/input"

export function Search() {
  return (
    <div className="relative w-full max-w-sm">
      <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
      <Input
        type="search"
        placeholder="Search cache entries..."
        className="w-full pl-9 bg-[#2a2a4a] border-[#3a3a5e] text-white placeholder:text-slate-400 focus-visible:ring-blue-500"
      />
    </div>
  )
}
