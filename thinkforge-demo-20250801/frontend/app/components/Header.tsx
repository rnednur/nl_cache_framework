"use client"

import React from "react"
import { usePathname } from "next/navigation"
import { Search, Home, ChevronRight } from "lucide-react"
import { Input } from "./ui/input"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "./ui/breadcrumb"

interface BreadcrumbItem {
  name: string
  href: string
  icon?: React.ReactNode
}

export default function Header({ searchPlaceholder = "Search..." }: { searchPlaceholder?: string }) {
  const pathname = usePathname()
  
  const getBreadcrumbs = (): BreadcrumbItem[] => {
    const paths = pathname?.split('/').filter(Boolean) || []
    const breadcrumbs: BreadcrumbItem[] = [
      { name: "Home", href: "/", icon: <Home className="h-4 w-4 mr-1" /> }
    ]
    
    let currentPath = ""
    
    paths.forEach((path, i) => {
      currentPath += `/${path}`
      
      // Convert path to readable name (e.g., cache-entries -> Cache Entries)
      const name = path
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
      
      breadcrumbs.push({
        name,
        href: currentPath
      })
    })
    
    return breadcrumbs
  }
  
  const breadcrumbs = getBreadcrumbs()
  
  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbs.map((item, index) => (
            <React.Fragment key={item.href}>
              <BreadcrumbItem>
                <BreadcrumbLink href={item.href}>
                  {item.icon}
                  {item.name}
                </BreadcrumbLink>
              </BreadcrumbItem>
              {index < breadcrumbs.length - 1 && (
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
              )}
            </React.Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>

      <div className="relative w-64">
        <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
        <Input placeholder={searchPlaceholder} className="pl-8" />
      </div>
    </header>
  )
} 