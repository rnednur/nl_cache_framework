"use client"

import * as React from "react"
import { useState, useEffect, useMemo } from "react"
import { Check, ChevronDown, Plus, Search, Loader2 } from "lucide-react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { cn } from "../../lib/utils"
import { Input } from "./input"
import { Button } from "./button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "./command"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"
import api from "@/app/services/api"

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
  // For hierarchical filtering
  catalogType?: string
  catalogSubtype?: string
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
  maxDisplayItems = 100,
  catalogType,
  catalogSubtype
}: CatalogSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [catalogValues, setCatalogValues] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchValue, setSearchValue] = useState("")
  const [isAddingNew, setIsAddingNew] = useState(false)
  const [newValue, setNewValue] = useState("")

  // Load catalog values on mount and when parent values change
  useEffect(() => {
    const loadCatalogValues = async () => {
      setIsLoading(true)
      try {
        // Build filters for hierarchical filtering
        const filters: { catalog_type?: string; catalog_subtype?: string } = {}
        if (catalogType) filters.catalog_type = catalogType
        if (catalogSubtype) filters.catalog_subtype = catalogSubtype
        
        const data = await api.getCatalogValues(Object.keys(filters).length > 0 ? filters : undefined)
        
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
  }, [catalogField, catalogType, catalogSubtype])

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
      
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
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
          >
            <span className="truncate">
              {value || placeholder}
            </span>
            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        
        <PopoverContent className="w-full p-0" align="start">
          <Command>
            <CommandInput
              placeholder={`Search ${catalogField.replace('catalog_', '')}...`}
              value={searchValue}
              onValueChange={setSearchValue}
              className="h-9"
            />
            
            <CommandList className="max-h-[200px]">
              {isLoading ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  {filteredValues.length === 0 && !canAddNewFromSearch && (
                    <CommandEmpty>No results found.</CommandEmpty>
                  )}
                  
                  {filteredValues.length > 0 && (
                    <CommandGroup>
                      {filteredValues.map((item) => (
                        <CommandItem
                          key={item}
                          value={item}
                          onSelect={() => handleSelect(item)}
                          className="cursor-pointer"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              value === item ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <span className="truncate">{item}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  )}
                  
                  {canAddNewFromSearch && (
                    <CommandGroup>
                      <CommandItem
                        onSelect={() => {
                          onValueChange?.(searchValue.trim())
                          setCatalogValues(prev => [...prev, searchValue.trim()])
                          setIsOpen(false)
                          setSearchValue("")
                        }}
                        className="cursor-pointer font-medium text-primary"
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        Add "{searchValue.trim()}"
                      </CommandItem>
                    </CommandGroup>
                  )}
                  
                  {allowCustom && !isAddingNew && !canAddNewFromSearch && (
                    <CommandGroup>
                      <CommandItem
                        onSelect={() => setIsAddingNew(true)}
                        className="cursor-pointer font-medium text-primary"
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        Add new option...
                      </CommandItem>
                    </CommandGroup>
                  )}
                </>
              )}
            </CommandList>
          </Command>
          
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
        </PopoverContent>
      </Popover>
      
      {catalogValues.length > maxDisplayItems && (
        <p className="text-xs text-muted-foreground">
          Showing {Math.min(filteredValues.length, maxDisplayItems)} of {catalogValues.length} options. 
          Use search to find more.
        </p>
      )}
    </div>
  )
} 