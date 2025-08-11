import type { ReactNode } from "react"
import { Sidebar } from "./sidebar"
import { Header } from "./header"

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex min-h-screen bg-[#121225]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="p-6 flex-1 overflow-auto">
          <div className="space-y-6 max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  )
}
