"use client"

import { useState, useEffect } from "react"
import { 
  BarChart2, 
  Filter,
  Info,
  Clock,
  CheckCircle2,
  XCircle,
  Download,
  Search,
  SlidersHorizontal,
  Zap
} from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select"
import { Label } from "../../components/ui/label"
import { Input } from "../../components/ui/input"
import { Switch } from "../../components/ui/switch"
import api, { UsageLog, CatalogValues } from "../../services/api"

export default function UsageLogs() {
  const [usageLogs, setUsageLogs] = useState<UsageLog[]>([])
  const [loading, setLoading] = useState(true)
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: []
  })
  const [filters, setFilters] = useState({
    catalogType: "all",
    catalogSubtype: "all",
    catalogName: "all",
    successOnly: false,
    llmUsedOnly: false,
    searchQuery: "",
    timePeriod: "all"
  })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [totalLogs, setTotalLogs] = useState(0)
  const [showFilters, setShowFilters] = useState(false)
  
  useEffect(() => {
    const fetchCatalogValues = async () => {
      try {
        const data = await api.getCatalogValues()
        setCatalogValues(data)
      } catch (error) {
        console.error("Failed to fetch catalog values:", error)
      }
    }
    
    fetchCatalogValues()
  }, [])
  
  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true)
      try {
        const data = await api.getUsageLogs(page, pageSize)
        
        // Apply client-side filtering
        let filteredLogs = data.items || []
        
        // Filter by catalog if selected
        if (filters.catalogType !== "all") {
          filteredLogs = filteredLogs.filter(log => log.catalog_type === filters.catalogType)
        }
        
        if (filters.catalogSubtype !== "all") {
          filteredLogs = filteredLogs.filter(log => log.catalog_subtype === filters.catalogSubtype)
        }
        
        if (filters.catalogName !== "all") {
          filteredLogs = filteredLogs.filter(log => log.catalog_name === filters.catalogName)
        }
        
        // Filter by time period if selected
        if (filters.timePeriod !== "all") {
          const now = new Date()
          let cutoffDate = new Date()
          
          switch(filters.timePeriod) {
            case "today":
              cutoffDate.setHours(0, 0, 0, 0)
              break
            case "yesterday":
              cutoffDate.setDate(now.getDate() - 1)
              cutoffDate.setHours(0, 0, 0, 0)
              const yesterdayEnd = new Date(cutoffDate)
              yesterdayEnd.setHours(23, 59, 59, 999)
              filteredLogs = filteredLogs.filter(log => {
                const logDate = new Date(log.timestamp)
                return logDate >= cutoffDate && logDate <= yesterdayEnd
              })
              break
            case "week":
              cutoffDate.setDate(now.getDate() - 7)
              break
            case "month":
              cutoffDate.setMonth(now.getMonth() - 1)
              break
            default:
              break
          }
          
          if (filters.timePeriod !== "yesterday") {
            filteredLogs = filteredLogs.filter(log => {
              return new Date(log.timestamp) >= cutoffDate
            })
          }
        }
        
        // Filter by success status if selected
        if (filters.successOnly) {
          filteredLogs = filteredLogs.filter(log => log.success_status === true)
        }
        
        // Filter by LLM usage if selected
        if (filters.llmUsedOnly) {
          filteredLogs = filteredLogs.filter(log => log.llm_used === true)
        }
        
        // Filter by search query if provided
        if (filters.searchQuery) {
          const query = filters.searchQuery.toLowerCase()
          filteredLogs = filteredLogs.filter(log => 
            (log.prompt && log.prompt.toLowerCase().includes(query)) ||
            (log.error_message && log.error_message.toLowerCase().includes(query))
          )
        }
        
        setUsageLogs(filteredLogs)
        setTotalLogs(data.total || 0)
      } catch (error) {
        console.error("Failed to fetch usage logs:", error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchLogs()
  }, [filters, page, pageSize])
  
  const handleFilterChange = (field: string, value: any) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }))
    // Reset page when filters change
    setPage(1)
  }
  
  const totalPages = Math.ceil(totalLogs / pageSize)
  
  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).format(date)
  }
  
  // Simulate downloading logs as CSV
  const handleDownloadCSV = () => {
    // Create CSV content
    const headers = ["ID", "Timestamp", "Success", "Similarity Score", "Prompt", "Cache Entry ID", "LLM Used", "Catalog Type", "Catalog Subtype", "Catalog Name", "Error Message"]
    const rows = usageLogs.map(log => [
      log.id,
      log.timestamp,
      log.success_status ? "Success" : "Failed",
      log.similarity_score.toFixed(4),
      log.prompt || "",
      log.cache_entry_id || "",
      log.llm_used ? "Yes" : "No",
      log.catalog_type || "",
      log.catalog_subtype || "",
      log.catalog_name || "",
      log.error_message || ""
    ])
    
    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    ].join("\n")
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", `usage_logs_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
  
  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold tracking-tight text-neutral-200">Usage Logs</h2>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => setShowFilters(!showFilters)}
              className="border-neutral-700 hover:bg-neutral-800 text-neutral-300"
            >
              <SlidersHorizontal className="h-4 w-4 mr-2" />
              {showFilters ? "Hide Filters" : "Show Filters"}
            </Button>
            <Button 
              onClick={handleDownloadCSV}
              className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white"
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
        
        {/* Quick filters */}
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-6">
            <div className="flex items-center space-x-2">
              <div className="flex h-6 items-center">
                <Switch
                  id="success-filter-quick"
                  checked={filters.successOnly}
                  onCheckedChange={(checked) => handleFilterChange("successOnly", checked)}
                  className="bg-neutral-700 data-[state=checked]:bg-green-600"
                />
              </div>
              <Label htmlFor="success-filter-quick" className="text-sm font-medium text-neutral-300">
                Show only successful queries
              </Label>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className="flex h-6 items-center">
                <Switch
                  id="llm-filter-quick"
                  checked={filters.llmUsedOnly}
                  onCheckedChange={(checked) => handleFilterChange("llmUsedOnly", checked)}
                  className="bg-neutral-700 data-[state=checked]:bg-purple-600"
                />
              </div>
              <Label htmlFor="llm-filter-quick" className="text-sm font-medium text-neutral-300">
                Show only LLM-assisted queries
              </Label>
            </div>
          </div>
          
          <div className="flex items-center gap-3 ml-auto">
            <Label htmlFor="time-period-quick" className="text-sm font-medium text-neutral-300">Time period:</Label>
            <Select 
              value={filters.timePeriod} 
              onValueChange={(value) => handleFilterChange("timePeriod", value)}
            >
              <SelectTrigger id="time-period-quick" className="w-40 bg-neutral-800 border-neutral-700 text-neutral-300">
                <SelectValue placeholder="All time" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                <SelectItem value="all" className="text-neutral-300">All Time</SelectItem>
                <SelectItem value="today" className="text-neutral-300">Today</SelectItem>
                <SelectItem value="yesterday" className="text-neutral-300">Yesterday</SelectItem>
                <SelectItem value="week" className="text-neutral-300">Last 7 days</SelectItem>
                <SelectItem value="month" className="text-neutral-300">Last 30 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      
      {/* Advanced Filters */}
      {showFilters && (
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-neutral-200 flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Advanced Filters
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Filter logs by various criteria
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Catalog filters section */}
              <div>
                <h3 className="text-sm font-medium text-neutral-400 mb-3">Catalog Filters</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <Label htmlFor="catalog-type" className="mb-2 block text-sm font-medium text-neutral-300">Catalog Type</Label>
                    <Select 
                      value={filters.catalogType} 
                      onValueChange={(value) => handleFilterChange("catalogType", value)}
                    >
                      <SelectTrigger id="catalog-type" className="w-full bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectValue placeholder="Select catalog type" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectItem value="all" className="text-neutral-300">All catalog types</SelectItem>
                        {catalogValues.catalog_types.map((type) => (
                          <SelectItem key={type} value={type} className="text-neutral-300">{type}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="catalog-subtype" className="mb-2 block text-sm font-medium text-neutral-300">Catalog Subtype</Label>
                    <Select 
                      value={filters.catalogSubtype} 
                      onValueChange={(value) => handleFilterChange("catalogSubtype", value)}
                    >
                      <SelectTrigger id="catalog-subtype" className="w-full bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectValue placeholder="Select catalog subtype" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectItem value="all" className="text-neutral-300">All catalog subtypes</SelectItem>
                        {catalogValues.catalog_subtypes.map((subtype) => (
                          <SelectItem key={subtype} value={subtype} className="text-neutral-300">{subtype}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="catalog-name" className="mb-2 block text-sm font-medium text-neutral-300">Catalog Name</Label>
                    <Select 
                      value={filters.catalogName} 
                      onValueChange={(value) => handleFilterChange("catalogName", value)}
                    >
                      <SelectTrigger id="catalog-name" className="w-full bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectValue placeholder="Select catalog name" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectItem value="all" className="text-neutral-300">All catalog names</SelectItem>
                        {catalogValues.catalog_names.map((name) => (
                          <SelectItem key={name} value={name} className="text-neutral-300">{name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              
              {/* Time and search filters section */}
              <div>
                <h3 className="text-sm font-medium text-neutral-400 mb-3">Time & Content Filters</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="time-period" className="mb-2 block text-sm font-medium text-neutral-300">Time Period</Label>
                    <Select 
                      value={filters.timePeriod} 
                      onValueChange={(value) => handleFilterChange("timePeriod", value)}
                    >
                      <SelectTrigger id="time-period" className="w-full bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectValue placeholder="Select time period" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectItem value="all" className="text-neutral-300">All Time</SelectItem>
                        <SelectItem value="today" className="text-neutral-300">Today</SelectItem>
                        <SelectItem value="yesterday" className="text-neutral-300">Yesterday</SelectItem>
                        <SelectItem value="week" className="text-neutral-300">Last 7 days</SelectItem>
                        <SelectItem value="month" className="text-neutral-300">Last 30 days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="search" className="mb-2 block text-sm font-medium text-neutral-300">Search Prompt</Label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                        <Search className="h-4 w-4 text-neutral-400" />
                      </div>
                      <Input
                        id="search"
                        type="text"
                        className="pl-10 bg-neutral-800 border-neutral-700 text-neutral-300 placeholder-neutral-500 focus:border-[#3B4BF6] focus:ring-[#3B4BF6]"
                        placeholder="Search in prompt or error messages"
                        value={filters.searchQuery}
                        onChange={(e) => handleFilterChange("searchQuery", e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Query type filters */}
              <div>
                <h3 className="text-sm font-medium text-neutral-400 mb-3">Query Type Filters</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="flex items-center space-x-2">
                    <div className="flex h-6 items-center">
                      <Switch
                        id="success-filter"
                        checked={filters.successOnly}
                        onCheckedChange={(checked) => handleFilterChange("successOnly", checked)}
                        className="bg-neutral-700 data-[state=checked]:bg-green-600"
                      />
                    </div>
                    <Label htmlFor="success-filter" className="text-sm font-medium text-neutral-300">
                      Show only successful queries
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <div className="flex h-6 items-center">
                      <Switch
                        id="llm-filter"
                        checked={filters.llmUsedOnly}
                        onCheckedChange={(checked) => handleFilterChange("llmUsedOnly", checked)}
                        className="bg-neutral-700 data-[state=checked]:bg-purple-600"
                      />
                    </div>
                    <Label htmlFor="llm-filter" className="text-sm font-medium text-neutral-300">
                      Show only LLM-assisted queries
                    </Label>
                  </div>
                </div>
              </div>
              
              {/* Page size and reset */}
              <div className="flex justify-between items-center pt-4 border-t border-neutral-800">
                <div>
                  <Label htmlFor="page-size" className="mr-2 text-sm font-medium text-neutral-300">Items per page:</Label>
                  <Select 
                    value={String(pageSize)} 
                    onValueChange={(value) => {
                      setPageSize(Number(value))
                      setPage(1)
                    }}
                  >
                    <SelectTrigger id="page-size" className="w-24 bg-neutral-800 border-neutral-700 text-neutral-300">
                      <SelectValue placeholder="Page size" />
                    </SelectTrigger>
                    <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                      <SelectItem value="10" className="text-neutral-300">10</SelectItem>
                      <SelectItem value="20" className="text-neutral-300">20</SelectItem>
                      <SelectItem value="50" className="text-neutral-300">50</SelectItem>
                      <SelectItem value="100" className="text-neutral-300">100</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button 
                  onClick={() => {
                    setFilters({
                      catalogType: "all",
                      catalogSubtype: "all",
                      catalogName: "all",
                      successOnly: false,
                      llmUsedOnly: false,
                      searchQuery: "",
                      timePeriod: "all"
                    })
                    setPage(1)
                  }}
                  variant="outline"
                  className="border-neutral-700 hover:bg-neutral-800 text-neutral-300"
                >
                  Reset Filters
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
        <CardHeader>
          <CardTitle className="text-neutral-200">Detailed Usage Logs</CardTitle>
          <CardDescription className="text-neutral-400">
            Complete cache usage history with {totalLogs} total logs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-96">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3B4BF6]"></div>
            </div>
          ) : usageLogs.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-neutral-700">
                  <thead>
                    <tr>
                      <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Time</th>
                      <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                      <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Prompt</th>
                      <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Similarity</th>
                      <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Cache Entry ID</th>
                      <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">LLM Used</th>
                      <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Catalog</th>
                    </tr>
                  </thead>
                  <tbody className="bg-neutral-900 divide-y divide-neutral-800">
                    {usageLogs.map((log) => (
                      <tr key={log.id}>
                        <td className="px-4 py-3 text-sm text-neutral-300">{formatDate(log.timestamp)}</td>
                        <td className="px-4 py-3 text-sm">
                          {log.success_status ? (
                            <span className="inline-flex items-center gap-1 text-green-400">
                              <CheckCircle2 className="h-4 w-4" />
                              Success
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-red-400">
                              <XCircle className="h-4 w-4" />
                              Failed
                              {log.error_message && (
                                <span className="block mt-1 text-xs text-neutral-400">
                                  {log.error_message.length > 30 
                                    ? `${log.error_message.substring(0, 30)}...` 
                                    : log.error_message}
                                </span>
                              )}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-neutral-300">
                          {log.prompt 
                            ? (log.prompt.length > 50 
                                ? `${log.prompt.substring(0, 50)}...` 
                                : log.prompt) 
                            : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-neutral-300">{(log.similarity_score * 100).toFixed(2)}%</td>
                        <td className="px-4 py-3 text-sm text-neutral-300">{log.cache_entry_id || '-'}</td>
                        <td className="px-4 py-3 text-sm text-neutral-300">
                          {log.llm_used ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-900 text-purple-300">
                              <Zap className="h-3 w-3 mr-1" />
                              Yes
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-700 text-neutral-300">
                              No
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-neutral-300">
                          {log.catalog_type ? (
                            <div className="flex flex-col">
                              <span className="font-medium">{log.catalog_type}</span>
                              {log.catalog_subtype && <span className="text-xs text-neutral-400">{log.catalog_subtype}</span>}
                              {log.catalog_name && <span className="text-xs text-neutral-400">{log.catalog_name}</span>}
                            </div>
                          ) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-neutral-400">
                    Showing page {page} of {totalPages} ({usageLogs.length} of {totalLogs} logs)
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => setPage(1)}
                      disabled={page === 1}
                      className="border-neutral-700 hover:bg-neutral-800 text-neutral-300"
                    >
                      First
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => setPage(prev => Math.max(prev - 1, 1))}
                      disabled={page === 1}
                      className="border-neutral-700 hover:bg-neutral-800 text-neutral-300"
                    >
                      Previous
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => setPage(prev => Math.min(prev + 1, totalPages))}
                      disabled={page === totalPages}
                      className="border-neutral-700 hover:bg-neutral-800 text-neutral-300"
                    >
                      Next
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => setPage(totalPages)}
                      disabled={page === totalPages}
                      className="border-neutral-700 hover:bg-neutral-800 text-neutral-300"
                    >
                      Last
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-96">
              <Info className="h-16 w-16 text-neutral-600 mb-4" />
              <p className="text-neutral-400 text-lg">No usage logs available</p>
              {filters.searchQuery || filters.successOnly || filters.llmUsedOnly || 
               filters.catalogType !== "all" || filters.catalogSubtype !== "all" || filters.catalogName !== "all" ? (
                <p className="text-neutral-500 mt-2">Try changing your filter criteria</p>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
} 