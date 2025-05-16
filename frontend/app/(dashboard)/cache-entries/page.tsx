"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { PlusCircle, Edit, Trash2, Search, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "../../components/ui/button"
import { Input } from "../../components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card"
import { Switch } from "../../components/ui/switch"
import { Label } from "../../components/ui/label"
import api, { CacheItem, CatalogValues } from "../../services/api"
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
  const thRefs = useRef<(HTMLTableCellElement | null)[]>(new Array(6).fill(null))
  const [columnWidths, setColumnWidths] = useState([60, 10, 10, 10, 5, 5])
  
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
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-neutral-200">Cache Entries</h1>
        <Button asChild className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white">
          <Link href="/cache-entries/create">
            <PlusCircle className="mr-2 h-4 w-4" />
            Create Entry
          </Link>
        </Button>
      </div>
      
      <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-neutral-200">Filters</CardTitle>
          <CardDescription className="text-neutral-400">
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
                  <SelectTrigger className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectValue placeholder="All template types" />
                  </SelectTrigger>
                  <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectItem value="all" className="text-neutral-300">All template types</SelectItem>
                    <SelectItem value="sql" className="text-neutral-300">SQL</SelectItem>
                    <SelectItem value="url" className="text-neutral-300">URL</SelectItem>
                    <SelectItem value="api" className="text-neutral-300">API</SelectItem>
                    <SelectItem value="workflow" className="text-neutral-300">Workflow</SelectItem>
                    <SelectItem value="graphql" className="text-neutral-300">GraphQL</SelectItem>
                    <SelectItem value="regex" className="text-neutral-300">Regex</SelectItem>
                    <SelectItem value="script" className="text-neutral-300">Script</SelectItem>
                    <SelectItem value="nosql" className="text-neutral-300">NoSQL</SelectItem>
                    <SelectItem value="cli" className="text-neutral-300">CLI</SelectItem>
                    <SelectItem value="reasoning_steps" className="text-neutral-300">Reasoning Steps</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <form onSubmit={handleSearch} className="flex w-full sm:w-2/3 gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-neutral-400" />
                  <Input
                    placeholder="Search queries..."
                    className="pl-8 bg-neutral-800 border-neutral-700 text-neutral-300 focus-visible:ring-[#3B4BF6] placeholder:text-neutral-500"
                    value={searchInputValue}
                    onChange={(e) => setSearchInputValue(e.target.value)}
                  />
                </div>
                <Button type="submit" className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white">Search</Button>
              </form>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="w-full sm:w-1/3">
                <label className="text-xs text-neutral-400 block mb-1">Catalog Type</label>
                <Select
                  value={catalogType}
                  onValueChange={(value) => {
                    setCatalogType(value)
                    setCatalogSubtype("all")
                    setCatalogName("all")
                    setCurrentPage(1)
                  }}
                >
                  <SelectTrigger className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectValue placeholder="All catalog types" />
                  </SelectTrigger>
                  <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectItem value="all" className="text-neutral-300">All catalog types</SelectItem>
                    {catalogValues.catalog_types.map((type) => (
                      <SelectItem key={type} value={type} className="text-neutral-300">{type}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="w-full sm:w-1/3">
                <label className="text-xs text-neutral-400 block mb-1">Catalog Subtype</label>
                <Select
                  value={catalogSubtype}
                  onValueChange={(value) => {
                    setCatalogSubtype(value)
                    setCurrentPage(1)
                  }}
                  disabled={catalogType === "all"}
                >
                  <SelectTrigger className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectValue placeholder="All subtypes" />
                  </SelectTrigger>
                  <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectItem value="all" className="text-neutral-300">All subtypes</SelectItem>
                    {catalogValues.catalog_subtypes
                      .filter(subtype => catalogType !== "all" && subtype.startsWith(catalogType))
                      .map((subtype) => (
                        <SelectItem key={subtype} value={subtype} className="text-neutral-300">{subtype}</SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="w-full sm:w-1/3">
                <label className="text-xs text-neutral-400 block mb-1">Catalog Name</label>
                <Select
                  value={catalogName}
                  onValueChange={(value) => {
                    setCatalogName(value)
                    setCurrentPage(1)
                  }}
                  disabled={catalogType === "all"}
                >
                  <SelectTrigger className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectValue placeholder="All names" />
                  </SelectTrigger>
                  <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                    <SelectItem value="all" className="text-neutral-300">All names</SelectItem>
                    {catalogValues.catalog_names
                      .filter(name => catalogType !== "all" && name.startsWith(catalogType))
                      .map((name) => (
                        <SelectItem key={name} value={name} className="text-neutral-300">{name}</SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="text-xs text-neutral-500 mt-1 italic">
              Note: Catalog fields may not be available in the current API version. You can still create and edit entries with catalog values.
            </div>
          
            <div className="flex items-center space-x-2">
              <div 
                className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#121212] border border-neutral-800 cursor-pointer"
                onClick={() => setUseSimilaritySearch(!useSimilaritySearch)}
              >
                <div className={`w-10 h-6 rounded-full relative ${useSimilaritySearch ? 'bg-[#3B4BF6]' : 'bg-neutral-700'}`}>
                  <div 
                    className={`absolute w-4 h-4 rounded-full bg-white top-1 transition-all duration-200 ${useSimilaritySearch ? 'left-5' : 'left-1'}`}
                  ></div>
                </div>
                <span className="text-white text-sm font-medium">Use similarity search</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <div className="rounded-md overflow-hidden">
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
            <thead className="bg-[#151515] text-neutral-300">
              <tr>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[0]}%`, minWidth: '200px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[0] = el; }}>Query</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[1]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[1] = el; }}>Template Type</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[2]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[2] = el; }}>Catalog Type</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[3]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[3] = el; }}>Tags</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[4]}%`, minWidth: '80px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[4] = el; }}>Usage Count</th>
                <th className="h-10 px-4 text-left font-medium" style={{ width: `${columnWidths[5]}%`, minWidth: '100px' }} ref={(el: HTMLTableCellElement | null) => { thRefs.current[5] = el; }}>Actions</th>
              </tr>
            </thead>
            <tbody className="bg-[#1a1a1a] text-neutral-200">
              {loading ? (
                <tr>
                  <td colSpan={6} className="h-24 text-center text-neutral-400">
                    Loading cache entries...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={6} className="h-24 text-center text-neutral-400">
                    No cache entries found.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.id} className="transition-colors hover:bg-[#222222] border-b border-[#222222]">
                    <td className="p-4 align-middle" style={{ width: `${columnWidths[0]}%`, minWidth: '200px' }}>
                      <div className="truncate font-medium">
                        <Link 
                          href={`/cache-entries/${entry.id}`}
                          className="hover:underline text-neutral-200"
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
                        {entry.tags && entry.tags.length > 0 ? (
                          entry.tags.map((tag) => (
                            <span 
                              key={tag} 
                              className="inline-flex items-center rounded-full bg-neutral-700 px-2 py-1 text-xs text-neutral-300"
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
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="icon" asChild className="hover:bg-neutral-700 text-neutral-400">
                          <Link href={`/cache-entries/${entry.id}/edit`}>
                            <Edit className="h-4 w-4" />
                            <span className="sr-only">Edit</span>
                          </Link>
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon"
                          onClick={() => handleDeleteEntry(entry.id)}
                          className="hover:bg-neutral-700 text-neutral-400"
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
        
        <div className="flex items-center justify-between px-4 py-4 border-t border-[#222222] bg-[#151515]">
          <div className="text-sm text-neutral-400">
            Showing <span className="font-medium text-neutral-300">{entries.length}</span> of{" "}
            <span className="font-medium text-neutral-300">{totalEntries}</span> entries
          </div>
          
          <div className="flex items-center space-x-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handlePreviousPage}
              disabled={currentPage === 1}
              className="border-neutral-600 text-neutral-300 hover:bg-neutral-800 hover:text-neutral-200"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <div className="text-sm text-neutral-400">
              Page <span className="font-medium text-neutral-300">{currentPage}</span> of{" "}
              <span className="font-medium text-neutral-300">{totalPages || 1}</span>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
              className="border-neutral-600 text-neutral-300 hover:bg-neutral-800 hover:text-neutral-200"
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