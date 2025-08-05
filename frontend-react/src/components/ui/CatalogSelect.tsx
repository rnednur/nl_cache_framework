"use client"

import * as React from "react"
import { useState, useEffect, useMemo } from "react"
import { Check, ChevronDown, Plus, Search, Loader2 } from "lucide-react"
import { cn } from "../../lib/utils"
import { Input } from "./input"
import { Button } from "./button"
import api from "../../services/api"

export interface CatalogSelectProps {
  value?: string
  onValueChange?: (value: string | undefined) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  catalogField: 'catalog_type' | 'catalog_subtype' | 'catalog_name'
  label?: string
  allowCustom?: boolean
  maxDisplayItems?: number
}

export function CatalogSelect({
  value,
  onValueChange,
  placeholder = "Select or add new...",
  disabled = false,
  className,
  catalogField,
  label,
  allowCustom = true,
  maxDisplayItems = 100
}: CatalogSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [catalogValues, setCatalogValues] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchValue, setSearchValue] = useState("")
  const [isAddingNew, setIsAddingNew] = useState(false)
  const [newValue, setNewValue] = useState("")

  // Load catalog values on mount
  useEffect(() => {
    const loadCatalogValues = async () => {
      setIsLoading(true)
      try {
        const data = await api.getCatalogValues()
        switch (catalogField) {
          case 'catalog_type':
            setCatalogValues(data.catalog_types || [])
            break
          case 'catalog_subtype':
            setCatalogValues(data.catalog_subtypes || [])
            break
          case 'catalog_name':
            setCatalogValues(data.catalog_names || [])
            break
        }
      } catch (error) {
        console.error('Error loading catalog values:', error)
        setCatalogValues([])
      } finally {
        setIsLoading(false)
      }
    }

    loadCatalogValues()
  }, [catalogField])

  // Filter and sort catalog values based on search
  const filteredValues = useMemo(() => {
    if (!searchValue) {
      return catalogValues.slice(0, maxDisplayItems)
    }
    
    const filtered = catalogValues.filter(item =>
      item.toLowerCase().includes(searchValue.toLowerCase())
    )
    
    return filtered
      .sort((a, b) => {
        // Prioritize exact matches and items starting with search term
        const aLower = a.toLowerCase()
        const bLower = b.toLowerCase()
        const searchLower = searchValue.toLowerCase()
        
        if (aLower === searchLower) return -1
        if (bLower === searchLower) return 1
        if (aLower.startsWith(searchLower) && !bLower.startsWith(searchLower)) return -1
        if (bLower.startsWith(searchLower) && !aLower.startsWith(searchLower)) return 1
        
        return a.localeCompare(b)
      })
      .slice(0, maxDisplayItems)
  }, [catalogValues, searchValue, maxDisplayItems])

  // Handle adding new custom value
  const handleAddNew = () => {
    if (newValue.trim() && !catalogValues.includes(newValue.trim())) {
      const trimmedValue = newValue.trim()
      setCatalogValues(prev => [...prev, trimmedValue])
      onValueChange?.(trimmedValue)
      setNewValue("")
      setIsAddingNew(false)
      setIsOpen(false)
    }
  }

  // Handle selecting existing value
  const handleSelect = (selectedValue: string) => {
    if (selectedValue === value) {
      onValueChange?.(undefined)
    } else {
      onValueChange?.(selectedValue)
    }
    setIsOpen(false)
    setSearchValue("")
  }

  // Check if search value could be a new option
  const canAddNewFromSearch = allowCustom && 
    searchValue.trim() && 
    !catalogValues.some(v => v.toLowerCase() === searchValue.toLowerCase())

  return (
    <div className="space-y-2">
      {label && <label className="text-sm font-medium">{label}</label>}
      
      <div className="relative">
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={isOpen}
          className={cn(
            "w-full justify-between text-left font-normal",
            !value && "text-muted-foreground",
            className
          )}
          disabled={disabled}
          onClick={() => setIsOpen(!isOpen)}
        >
          <span className="truncate">
            {value || placeholder}
          </span>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
        
        {isOpen && (
          <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded-md border bg-background shadow-lg">
            <div className="p-3 border-b">
              <div className="flex items-center border rounded-md px-3">
                <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                <Input
                  placeholder={`Search ${catalogField.replace('catalog_', '')}...`}
                  value={searchValue}
                  onChange={(e) => setSearchValue(e.target.value)}
                  className="border-0 px-0 focus:ring-0"
                />
              </div>
            </div>
            
            <div className="max-h-[200px] overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  {filteredValues.length === 0 && !canAddNewFromSearch && (
                    <div className="py-6 text-center text-sm">No results found.</div>
                  )}
                  
                  {filteredValues.length > 0 && (
                    <div className="p-1">
                      {filteredValues.map((item) => (
                        <div
                          key={item}
                          onClick={() => handleSelect(item)}
                          className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              value === item ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <span className="truncate">{item}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {canAddNewFromSearch && (
                    <div className="p-1 border-t">
                      <div
                        onClick={() => {
                          onValueChange?.(searchValue.trim())
                          setCatalogValues(prev => [...prev, searchValue.trim()])
                          setIsOpen(false)
                          setSearchValue("")
                        }}
                        className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm font-medium text-primary outline-none hover:bg-accent"
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        Add "{searchValue.trim()}"
                      </div>
                    </div>
                  )}
                  
                  {allowCustom && !isAddingNew && !canAddNewFromSearch && (
                    <div className="p-1 border-t">
                      <div
                        onClick={() => setIsAddingNew(true)}
                        className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm font-medium text-primary outline-none hover:bg-accent"
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        Add new option...
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
            
            {isAddingNew && (
              <div className="border-t p-3 space-y-2">
                <Input
                  placeholder={`Enter new ${catalogField.replace('catalog_', '')}`}
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddNew()
                    } else if (e.key === 'Escape') {
                      setIsAddingNew(false)
                      setNewValue("")
                    }
                  }}
                  autoFocus
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleAddNew}
                    disabled={!newValue.trim()}
                  >
                    Add
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setIsAddingNew(false)
                      setNewValue("")
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
        
        {isOpen && (
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
        )}
      </div>
      
      {catalogValues.length > maxDisplayItems && (
        <p className="text-xs text-muted-foreground">
          Showing {Math.min(filteredValues.length, maxDisplayItems)} of {catalogValues.length} options. 
          Use search to find more.
        </p>
      )}
    </div>
  )
} 