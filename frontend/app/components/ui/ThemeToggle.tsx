"use client"

import { Moon, Sun } from "lucide-react"
import { Switch } from "./switch"
import { useState, useEffect } from "react"

interface ThemeToggleProps {
  showLabel?: boolean
  variant?: 'switch' | 'button'
  size?: 'sm' | 'md' | 'lg'
}

export function ThemeToggle({ showLabel = true, variant = 'switch', size = 'md' }: ThemeToggleProps) {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark')
  const [mounted, setMounted] = useState(false)
  
  // Load theme from localStorage and detect changes
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark'
    if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
      setTheme(savedTheme)
    } else {
      const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      setTheme(systemPrefersDark ? 'dark' : 'light')
    }
    setMounted(true)
  }, [])

  // Apply theme to document and save to localStorage
  useEffect(() => {
    if (!mounted) return
    
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    
    localStorage.setItem('theme', theme)
  }, [theme, mounted])

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light')
  }

  // Prevent hydration mismatch
  if (!mounted) {
    return null
  }

  const isDark = theme === 'dark'

  if (variant === 'button') {
    const buttonSize = {
      sm: 'h-8 w-8',
      md: 'h-9 w-9',
      lg: 'h-10 w-10'
    }[size]

    const iconSize = {
      sm: 'h-4 w-4',
      md: 'h-4 w-4',
      lg: 'h-5 w-5'
    }[size]

    return (
      <button
        onClick={toggleTheme}
        className={`${buttonSize} rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors flex items-center justify-center`}
        title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      >
        {isDark ? (
          <Sun className={iconSize} />
        ) : (
          <Moon className={iconSize} />
        )}
      </button>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <Sun className="h-4 w-4 text-muted-foreground" />
        <Switch
          checked={isDark}
          onCheckedChange={toggleTheme}
          aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
        />
        <Moon className="h-4 w-4 text-muted-foreground" />
      </div>
      {showLabel && (
        <span className="text-sm text-muted-foreground">
          {isDark ? 'Dark' : 'Light'} mode
        </span>
      )}
    </div>
  )
}
