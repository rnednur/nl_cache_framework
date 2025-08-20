"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { PlusCircle, Edit, Trash2, Search, ChevronLeft, ChevronRight, Database, Plus } from "lucide-react"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/app/components/ui/card"
import { PageHeader } from "@/app/components/ui/PageHeader"
import { Switch } from "@/app/components/ui/switch"
import { Label } from "@/app/components/ui/label"
import api, { CacheItem, CatalogValues } from "@/app/services/api"
import { toast } from "react-hot-toast"

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
  const [catalogType, setCatalogType] = useState("all")
  const [catalogSubtype, setCatalogSubtype] = useState("all")
  const [catalogName, setCatalogName] = useState("all")
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({ catalog_types: [], catalog_subtypes: [], catalog_names: [] })
  const [loadingCatalogs, setLoadingCatalogs] = useState(false)
  const tableRef = useRef<HTMLTableElement>(null)
  const thRefs = useRef<(HTMLTableCellElement | null)[]>(new Array(7).fill(null))
  const [columnWidths, setColumnWidths] = useState([50, 10, 10, 10, 5, 5, 10])
  
  useEffect(() => {
    /*
    const fetchCatalogValues = async () => {
      setLoadingCatalogs(true)
      try {
        const values = await api.getCatalogValues()
        console.log('Catalog Values from API:', values)
        setCatalogValues(values)
      } catch (err) {
        console.error("Failed to fetch catalog values", err)
      } finally {
        setLoadingCatalogs(false)
      }
    }
    fetchCatalogValues()
    */
  }, [])
  
  useEffect(() => {
    // Uncomment this to fetch catalog values
    const fetchCatalogValues = async () => {
      setLoadingCatalogs(true)
      try {
        const values = await api.getCatalogValues()
        setCatalogValues(values)
      } catch (err) {
        console.error("Failed to fetch catalog values", err)
      } finally {
        setLoadingCatalogs(false)
      }
    }
    fetchCatalogValues()
  }, [])
  
  useEffect(() => {
    const fetchEntries = async () => {
      setLoading(true)
      try {
        if (useSimilaritySearch && searchQuery) {
          // Use similarity search
          const results = await api.searchCacheEntries(
            searchQuery,
            templateType === "all" ? undefined : templateType,
            0.7,
            10,
            catalogType === "all" ? undefined : catalogType,
            catalogSubtype === "all" ? undefined : catalogSubtype,
            catalogName === "all" ? undefined : catalogName
          )
          setEntries(results)
          setTotalEntries(results.length)
        } else {
          // Use regular search
          const data = await api.getCacheEntries(
            currentPage, 
            pageSize,
            templateType === "all" ? undefined : templateType,
            searchQuery || undefined,
            catalogType === "all" ? undefined : catalogType,
            catalogSubtype === "all" ? undefined : catalogSubtype,
            catalogName === "all" ? undefined : catalogName
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
  }, [currentPage, pageSize, templateType, searchQuery, useSimilaritySearch, catalogType, catalogSubtype, catalogName])
  
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
          searchQuery || undefined,
          catalogType === "all" ? undefined : catalogType,
          catalogSubtype === "all" ? undefined : catalogSubtype,
          catalogName === "all" ? undefined : catalogName
        )
        setEntries(data.items)
        setTotalEntries(data.total)

        // If the current page is now empty and we're not on the first page,
        // go to the previous page
        if (data.items.length === 0 && currentPage > 1) {
          setCurrentPage(currentPage - 1)
        }

        // Show success message
        toast.success("Cache entry deleted successfully")
      } catch (error) {
        console.error(`Failed to delete cache entry with ID ${id}:`, error)
        // Show error message
        toast.error("Failed to delete cache entry")
      }
    }
  }
  
  useEffect(() => {
    const handleMouseDown = (e: MouseEvent, index: number) => {
      const startX = e.pageX;
      const startWidth = thRefs.current[index]?.offsetWidth || 0;
      const handleMouseMove = (moveEvent: MouseEvent) => {
        const newWidth = startWidth + (moveEvent.pageX - startX);
        const totalWidth = thRefs.current.reduce((sum, ref) => sum + (ref?.offsetWidth || 0), 0);
        const newWidths = [...columnWidths];
        newWidths[index] = (newWidth / totalWidth) * 100;
        setColumnWidths(newWidths);
      };
      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    };
    thRefs.current.forEach((th, index) => {
      if (th) {
        th.addEventListener('mousedown', (e) => {
          if (e.offsetX > th.offsetWidth - 10) {
            handleMouseDown(e, index);
          }
        });
      }
    });
    return () => {
      thRefs.current.forEach((th) => {
        if (th) {
          th.removeEventListener('mousedown', () => {});
        }
      });
    };
  }, [columnWidths]);
  
  return (
    <div className="space-y-6">
      <PageHeader
        title="Cache Entries"
        description="Manage your cached queries and templates"
        icon={Database}
        actions={
          <Button asChild className="gap-2">
            <Link href="/cache-entries/create">
              <Plus className="h-4 w-4" />
              Add Cache
            </Link>
          </Button>
        }
      />
      
      <Card className="workflow-card bg-card border-2 border-card-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground">Filters</CardTitle>
          <CardDescription className="text-muted-foreground">
            Filter cache entries by template type or search for specific queries
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="w-full sm:w-1/3">
                <Select
                  value={templateType}
                  onValueChange={(value) => {
                    setTemplateType(value)
                    setCurrentPage(1)
                  }}
                >
                  <SelectTrigger className="bg-input border-border text-foreground">
                    <SelectValue placeholder="All template types" />
                  </SelectTrigger>
                  <SelectContent className="bg-input border-border text-foreground">
                    <SelectItem value="all" className="text-foreground">All template types</SelectItem>
                    <SelectItem value="sql" className="text-foreground">SQL</SelectItem>
                    <SelectItem value="url" className="text-foreground">URL</SelectItem>
                    <SelectItem value="api" className="text-foreground">API</SelectItem>
                    <SelectItem value="workflow" className="text-foreground">Workflow</SelectItem>
                    <SelectItem value="graphql" className="text-foreground">GraphQL</SelectItem>
                    <SelectItem value="regex" className="text-foreground">Regex</SelectItem>
                    <SelectItem value="script" className="text-foreground">Script</SelectItem>
                    <SelectItem value="nosql" className="text-foreground">NoSQL</SelectItem>
                    <SelectItem value="cli" className="text-foreground">CLI</SelectItem>
                    <SelectItem value="reasoning_steps" className="text-foreground">Reasoning Steps</SelectItem>
                    <SelectItem value="dsl" className="text-foreground">DSL Components</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <form onSubmit={handleSearch} className="flex w-full sm:w-2/3 gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search queries..."
                    className="pl-8 bg-input border-border text-foreground focus-visible:ring-ring placeholder:text-muted-foreground"
                    value={searchInputValue}
                    onChange={(e) => setSearchInputValue(e.target.value)}
                  />
                </div>
                <Button type="submit" className="bg-primary hover:bg-primary/90 text-primary-foreground">Search</Button>
              </form>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="w-full sm:w-1/3">
                <label className="text-xs text-muted-foreground block mb-1">Catalog Type</label>
                <Select
                  value={catalogType}
                  onValueChange={(value) => {
                    setCatalogType(value)
                    setCatalogSubtype("all")
                    setCatalogName("all")
                    setCurrentPage(1)
                  }}
                >
                  <SelectTrigger className="bg-input border-border text-foreground">
                    <SelectValue placeholder="All catalog types" />
                  </SelectTrigger>
                  <SelectContent className="bg-input border-border text-foreground">
                    <SelectItem value="all" className="text-foreground">All catalog types</SelectItem>
                    {catalogValues.catalog_types.map((type) => (
                      <SelectItem key={type} value={type} className="text-foreground">{type}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="w-full sm:w-1/3">
                <label className="text-xs text-muted-foreground block mb-1">Catalog Subtype</label>
                <Select
                  value={catalogSubtype}
                  onValueChange={(value) => {
                    setCatalogSubtype(value)
                    setCurrentPage(1)
                  }}
                  disabled={catalogType === "all"}
                >
                  <SelectTrigger className="bg-input border-border text-foreground">
                    <SelectValue placeholder="All subtypes" />
                  </SelectTrigger>
                  <SelectContent className="bg-input border-border text-foreground">
                    <SelectItem value="all" className="text-foreground">All subtypes</SelectItem>
                    {catalogValues.catalog_subtypes
                      .filter(subtype => catalogType !== "all" && subtype.startsWith(catalogType))
                      .map((subtype) => (
                        <SelectItem key={subtype} value={subtype} className="text-foreground">{subtype}</SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="w-full sm:w-1/3">
                <label className="text-xs text-muted-foreground block mb-1">Catalog Name</label>
                <Select
                  value={catalogName}
                  onValueChange={(value) => {
                    setCatalogName(value)
                    setCurrentPage(1)
                  }}
                  disabled={catalogType === "all"}
                >
                  <SelectTrigger className="bg-input border-border text-foreground">
                    <SelectValue placeholder="All names" />
                  </SelectTrigger>
                  <SelectContent className="bg-input border-border text-foreground">
                    <SelectItem value="all" className="text-foreground">All names</SelectItem>
                    {catalogValues.catalog_names
                      .filter(name => catalogType !== "all" && name.startsWith(catalogType))
                      .map((name) => (
                        <SelectItem key={name} value={name} className="text-foreground">{name}</SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="text-xs text-neutral-500 mt-1 italic">
              Note: Catalog fields may not be available in the current API version. You can still create and edit entries with catalog values.
            </div>
          
            <div className="flex items-center space-x-2">
              <div className="flex h-6 items-center">
                <Switch
                  id="similarity-search"
                  checked={useSimilaritySearch}
                  onCheckedChange={setUseSimilaritySearch}
                />
              </div>
              <Label htmlFor="similarity-search" className="text-sm font-medium text-foreground">
                Use similarity search
              </Label>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card className="workflow-card bg-card border-2 border-card-border overflow-hidden">
        <div className="relative w-full overflow-auto">
          <style jsx>{`
            th {
              position: relative;
              user-select: none;
            }
            th::after {
              content: '';
              position: absolute;
              right: 0;
              top: 0;
              height: 100%;
              width: 5px;
              background: transparent;
              cursor: col-resize;
            }
            th:hover::after {
              background: rgba(255, 255, 255, 0.2);
            }
          `}</style>
          <table className="w-full caption-bottom text-sm" ref={tableRef}>
            <thead className="bg-muted text-foreground">
              <tr>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[0]}%`, minWidth: '200px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[0] = el; }}>Query</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[1]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[1] = el; }}>Template Type</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[2]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[2] = el; }}>Catalog Type</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[3]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[3] = el; }}>Tags</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[4]}%`, minWidth: '80px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[4] = el; }}>Usage Count</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[5]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[5] = el; }}>Updated At</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[6]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[6] = el; }}>Actions</th>
              </tr>
            </thead>
            <tbody className="bg-background text-foreground">
              {loading ? (
                <tr>
                  <td colSpan={7} className="h-24 text-center text-muted-foreground">
                    Loading cache entries...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={7} className="h-24 text-center text-muted-foreground">
                    No cache entries found.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.id} className="transition-colors hover:bg-accent/50 border-b border-border">
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[0]}%`, minWidth: '200px' }}>
                      <div className="truncate font-medium">
                        <Link 
                          href={`/cache-entries/${entry.id}`}
                          className="hover:underline text-foreground"
                        >
                          {entry.nl_query}
                        </Link>
                      </div>
                    </td>
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[1]}%`, minWidth: '100px' }}>
                      <span className="capitalize">{entry.template_type}</span>
                    </td>
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[2]}%`, minWidth: '100px' }}>
                      <span className="capitalize">
                        {entry.catalog_type || 
                          <span className="text-neutral-500 text-xs">Not specified</span>
                        }
                      </span>
                    </td>
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[3]}%`, minWidth: '100px' }}>
                      <div className="flex flex-wrap gap-1">
                        {entry.tags && Array.isArray(entry.tags) && entry.tags.length > 0 ? (
                          entry.tags.map((tag, index) => (
                            <span 
                              key={`tag-${index}-${tag}`} 
                              className="inline-flex items-center rounded-full bg-muted/60 px-2 py-1 text-xs text-foreground"
                            >
                              {tag}
                            </span>
                          ))
                        ) : (
                          <span className="text-neutral-500 text-xs">No tags</span>
                        )}
                      </div>
                    </td>
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[4]}%`, minWidth: '80px' }}>
                      {entry.usage_count}
                    </td>
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[5]}%`, minWidth: '100px' }}>
                      {entry.updated_at ? new Date(entry.updated_at).toLocaleString() : '-'}
                    </td>
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[6]}%`, minWidth: '100px' }}>
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="icon" asChild className="hover:bg-accent text-muted-foreground">
                          <Link href={`/cache-entries/${entry.id}/edit`}>
                            <Edit className="h-4 w-4" />
                            <span className="sr-only">Edit</span>
                          </Link>
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon"
                          onClick={() => handleDeleteEntry(entry.id)}
                          className="hover:bg-accent text-muted-foreground"
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
        
        <div className="flex items-center justify-between px-4 py-4 border-t border-border bg-muted">
          <div className="text-sm text-muted-foreground">
            Showing <span className="font-medium text-foreground">{entries.length}</span> of{" "}
            <span className="font-medium text-foreground">{totalEntries}</span> entries
          </div>
          
          <div className="flex items-center space-x-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handlePreviousPage}
              disabled={currentPage === 1}
              className="border-neutral-600 text-foreground hover:bg-input hover:text-foreground"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <div className="text-sm text-muted-foreground">
              Page <span className="font-medium text-foreground">{currentPage}</span> of{" "}
              <span className="font-medium text-foreground">{totalPages || 1}</span>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
              className="border-neutral-600 text-foreground hover:bg-input hover:text-foreground"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
} 