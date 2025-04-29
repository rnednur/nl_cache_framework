"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { PlusCircle, Edit, Trash2, Search, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "../../components/ui/button"
import { Input } from "../../components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card"
import { Switch } from "../../components/ui/switch"
import { Label } from "../../components/ui/label"
import api, { CacheItem } from "../../services/api"

export default function CacheEntries() {
  const [entries, setEntries] = useState<CacheItem[]>([])
  const [loading, setLoading] = useState(true)
  const [totalEntries, setTotalEntries] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [templateType, setTemplateType] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [searchInputValue, setSearchInputValue] = useState("")
  const [useSimilaritySearch, setUseSimilaritySearch] = useState(false)
  
  useEffect(() => {
    const fetchEntries = async () => {
      setLoading(true)
      try {
        if (useSimilaritySearch && searchQuery) {
          // Use similarity search
          const results = await api.searchCacheEntries(
            searchQuery,
            templateType === "all" ? undefined : templateType
          )
          setEntries(results)
          setTotalEntries(results.length)
        } else {
          // Use regular search
          const data = await api.getCacheEntries(
            currentPage, 
            pageSize,
            templateType === "all" ? undefined : templateType,
            searchQuery || undefined
          )
          setEntries(data.items)
          setTotalEntries(data.total)
        }
      } catch (error) {
        console.error("Failed to fetch cache entries:", error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchEntries()
  }, [currentPage, pageSize, templateType, searchQuery, useSimilaritySearch])
  
  const totalPages = Math.ceil(totalEntries / pageSize)
  
  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }
  
  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(searchInputValue)
    setCurrentPage(1) // Reset to first page on new search
  }
  
  const handleDeleteEntry = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this cache entry?")) {
      try {
        await api.deleteCacheEntry(id)
        // Refresh the list
        const data = await api.getCacheEntries(
          currentPage,
          pageSize,
          templateType === "all" ? undefined : templateType,
          searchQuery || undefined
        )
        setEntries(data.items)
        setTotalEntries(data.total)
      } catch (error) {
        console.error(`Failed to delete cache entry with ID ${id}:`, error)
      }
    }
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Cache Entries</h1>
        <Button asChild>
          <Link href="/cache-entries/create">
            <PlusCircle className="mr-2 h-4 w-4" />
            Create Entry
          </Link>
        </Button>
      </div>
      
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Filter cache entries by template type or search for specific queries
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="w-full sm:w-1/3">
              <Select
                value={templateType}
                onValueChange={(value) => {
                  setTemplateType(value)
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All template types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All template types</SelectItem>
                  <SelectItem value="sql">SQL</SelectItem>
                  <SelectItem value="api">API</SelectItem>
                  <SelectItem value="url">URL</SelectItem>
                  <SelectItem value="workflow">Workflow</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <form onSubmit={handleSearch} className="flex w-full sm:w-2/3 gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search queries..."
                  className="pl-8"
                  value={searchInputValue}
                  onChange={(e) => setSearchInputValue(e.target.value)}
                />
              </div>
              <Button type="submit">Search</Button>
            </form>
          </div>
          
          <div className="flex items-center space-x-2 mt-4">
            <Switch
              id="similarity-search"
              checked={useSimilaritySearch}
              onCheckedChange={setUseSimilaritySearch}
            />
            <Label htmlFor="similarity-search">Use similarity search</Label>
          </div>
        </CardContent>
      </Card>
      
      <div className="rounded-md border">
        <div className="relative w-full overflow-auto">
          <table className="w-full caption-bottom text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="h-10 px-4 text-left font-medium">Query</th>
                <th className="h-10 px-4 text-left font-medium">Template Type</th>
                <th className="h-10 px-4 text-left font-medium">Visualization</th>
                <th className="h-10 px-4 text-left font-medium">Tags</th>
                <th className="h-10 px-4 text-left font-medium">Usage Count</th>
                <th className="h-10 px-4 text-left font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="h-24 text-center">
                    Loading cache entries...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={6} className="h-24 text-center">
                    No cache entries found.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.id} className="border-b transition-colors hover:bg-muted/50">
                    <td className="p-4 align-middle max-w-[300px]">
                      <div className="truncate font-medium">
                        <Link 
                          href={`/cache-entries/${entry.id}`}
                          className="hover:underline"
                        >
                          {entry.nl_query}
                        </Link>
                      </div>
                    </td>
                    <td className="p-4 align-middle">
                      <span className="capitalize">{entry.template_type}</span>
                    </td>
                    <td className="p-4 align-middle">
                      {entry.suggested_visualization ? (
                        <span className="capitalize">{entry.suggested_visualization}</span>
                      ) : (
                        <span className="text-muted-foreground text-xs">None</span>
                      )}
                    </td>
                    <td className="p-4 align-middle">
                      <div className="flex flex-wrap gap-1">
                        {entry.tags && entry.tags.length > 0 ? (
                          entry.tags.map((tag) => (
                            <span 
                              key={tag} 
                              className="inline-flex items-center rounded-full bg-muted px-2 py-1 text-xs"
                            >
                              {tag}
                            </span>
                          ))
                        ) : (
                          <span className="text-muted-foreground text-xs">No tags</span>
                        )}
                      </div>
                    </td>
                    <td className="p-4 align-middle">
                      {entry.usage_count}
                    </td>
                    <td className="p-4 align-middle">
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/cache-entries/${entry.id}/edit`}>
                            <Edit className="h-4 w-4" />
                            <span className="sr-only">Edit</span>
                          </Link>
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon"
                          onClick={() => handleDeleteEntry(entry.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                          <span className="sr-only">Delete</span>
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        <div className="flex items-center justify-between px-4 py-4 border-t">
          <div className="text-sm text-muted-foreground">
            Showing <span className="font-medium">{entries.length}</span> of{" "}
            <span className="font-medium">{totalEntries}</span> entries
          </div>
          
          <div className="flex items-center space-x-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handlePreviousPage}
              disabled={currentPage === 1}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <div className="text-sm">
              Page <span className="font-medium">{currentPage}</span> of{" "}
              <span className="font-medium">{totalPages || 1}</span>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
} 