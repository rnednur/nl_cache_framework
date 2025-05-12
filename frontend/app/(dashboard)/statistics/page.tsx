"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { 
  BarChart2, 
  Filter,
  Info,
  Clock,
  CheckCircle2,
  XCircle,
  Zap,
  ClipboardList
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select"
import { Label } from "../../components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import api, { CacheStats, UsageLog, CatalogValues } from "../../services/api"

export default function Statistics() {
  const [stats, setStats] = useState<CacheStats | null>(null)
  const [usageLogs, setUsageLogs] = useState<UsageLog[]>([])
  const [loading, setLoading] = useState(true)
  const [logsLoading, setLogsLoading] = useState(true)
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: []
  })
  const [filters, setFilters] = useState({
    templateType: "all",
    catalogType: "all",
    catalogSubtype: "all",
    catalogName: "all"
  })
  const [page, setPage] = useState(1)
  const pageSize = 10
  const [totalLogs, setTotalLogs] = useState(0)
  
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
    const fetchStats = async () => {
      setLoading(true)
      try {
        const data = await api.getCacheStats(
          filters.templateType === "all" ? undefined : filters.templateType,
          filters.catalogType === "all" ? undefined : filters.catalogType,
          filters.catalogSubtype === "all" ? undefined : filters.catalogSubtype,
          filters.catalogName === "all" ? undefined : filters.catalogName
        )
        setStats(data)
      } catch (error) {
        console.error("Failed to fetch stats:", error)
      } finally {
        setLoading(false)
      }
    }
    
    const fetchLogs = async () => {
      setLogsLoading(true)
      try {
        const data = await api.getUsageLogs(page, pageSize)
        setUsageLogs(data.items || [])
        setTotalLogs(data.total || 0)
      } catch (error) {
        console.error("Failed to fetch usage logs:", error)
      } finally {
        setLogsLoading(false)
      }
    }
    
    fetchStats()
    fetchLogs()
  }, [filters, page])
  
  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }))
    // Reset page when filters change
    setPage(1)
  }
  
  // Convert object to array for recharts
  const templateTypeData = stats ? Object.entries(stats.by_template_type).map(([name, count]) => ({
    name,
    count
  })) : []
  
  const totalPages = Math.ceil(totalLogs / pageSize)
  
  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date)
  }
  
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight text-neutral-200">Detailed Statistics</h2>
        <Button 
          variant="outline" 
          asChild 
          className="border-neutral-700 hover:bg-neutral-800 text-neutral-300"
        >
          <Link href="/usage-logs">
            <ClipboardList className="h-4 w-4 mr-2" />
            View All Usage Logs
          </Link>
        </Button>
      </div>
      
      <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-neutral-200 text-lg flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-[#3B4BF6]" />
              Total Entries
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-neutral-100">
              {loading ? "..." : stats?.total_entries || 0}
            </div>
            <p className="text-xs text-neutral-400 mt-1">Total cached queries and templates</p>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-neutral-200 text-lg flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Valid Entries
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-neutral-100">
              {loading ? "..." : stats?.valid_entries || 0}
            </div>
            <p className="text-xs text-neutral-400 mt-1">Active and usable entries</p>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-neutral-200 text-lg flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-500" />
              Last 30 Days Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-neutral-100">
              {loading ? "..." : stats?.recent_usage.reduce((sum, day) => sum + day.count, 0) || 0}
            </div>
            <p className="text-xs text-neutral-400 mt-1">Cache hits in the last month</p>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-neutral-200 text-lg flex items-center gap-2">
              <Zap className="h-5 w-5 text-[#F97316]" />
              Template Entries
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-neutral-100">
              {loading ? "..." : stats?.template_entries || 0}
            </div>
            <p className="text-xs text-neutral-400 mt-1">Reusable template entries</p>
          </CardContent>
        </Card>
      </div>
      
      {/* Filters */}
      <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-neutral-200 flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filter Statistics
          </CardTitle>
          <CardDescription className="text-neutral-400">
            Filter statistics by template type and catalog
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <Label htmlFor="template-type" className="mb-2 block text-sm font-medium text-neutral-300">Template Type</Label>
              <Select 
                value={filters.templateType} 
                onValueChange={(value) => handleFilterChange("templateType", value)}
              >
                <SelectTrigger id="template-type" className="w-full bg-neutral-800 border-neutral-700 text-neutral-300">
                  <SelectValue placeholder="Select template type" />
                </SelectTrigger>
                <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                  <SelectItem value="all" className="text-neutral-300">All template types</SelectItem>
                  <SelectItem value="sql" className="text-neutral-300">SQL</SelectItem>
                  <SelectItem value="api" className="text-neutral-300">API</SelectItem>
                  <SelectItem value="url" className="text-neutral-300">URL</SelectItem>
                  <SelectItem value="workflow" className="text-neutral-300">Workflow</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
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
        </CardContent>
      </Card>
      
      <Tabs defaultValue="usage" className="w-full">
        <TabsList className="grid grid-cols-3 bg-neutral-800 border-neutral-700">
          <TabsTrigger value="usage" className="data-[state=active]:bg-neutral-700">Usage Over Time</TabsTrigger>
          <TabsTrigger value="entries" className="data-[state=active]:bg-neutral-700">Entry Types</TabsTrigger>
          <TabsTrigger value="logs" className="data-[state=active]:bg-neutral-700">Usage Logs</TabsTrigger>
        </TabsList>
        
        {/* Usage Over Time Tab */}
        <TabsContent value="usage">
          <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
            <CardHeader>
              <CardTitle className="text-neutral-200">Usage Trend (Last 30 Days)</CardTitle>
              <CardDescription className="text-neutral-400">
                Daily cache usage over the past month
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80 w-full">
                {loading ? (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-neutral-400">Loading usage data...</p>
                  </div>
                ) : stats?.recent_usage && stats.recent_usage.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={stats.recent_usage}
                      margin={{
                        top: 5,
                        right: 30,
                        left: 20,
                        bottom: 25,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis 
                        dataKey="date" 
                        stroke="#aaa"
                        angle={-45}
                        textAnchor="end"
                        tick={{ fontSize: 12 }}
                        tickMargin={10}
                      />
                      <YAxis stroke="#aaa" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#333',
                          borderColor: '#555',
                          color: '#eee'
                        }} 
                      />
                      <Line 
                        type="monotone" 
                        dataKey="count" 
                        name="Usage Count"
                        stroke="#3B4BF6" 
                        strokeWidth={2}
                        activeDot={{ r: 8 }} 
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-neutral-400">No usage data available</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Entry Types Tab */}
        <TabsContent value="entries">
          <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
            <CardHeader>
              <CardTitle className="text-neutral-200">Cache Entry Types</CardTitle>
              <CardDescription className="text-neutral-400">
                Distribution of entries by template type
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80 w-full">
                {loading ? (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-neutral-400">Loading template type data...</p>
                  </div>
                ) : templateTypeData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={templateTypeData}
                      margin={{
                        top: 5,
                        right: 30,
                        left: 20,
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis dataKey="name" stroke="#aaa" />
                      <YAxis stroke="#aaa" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#333',
                          borderColor: '#555',
                          color: '#eee'
                        }} 
                      />
                      <Bar 
                        dataKey="count" 
                        name="Entry Count"
                        fill="#3B4BF6" 
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-neutral-400">No template type data available</p>
                  </div>
                )}
              </div>
              
              {stats?.popular_entries && stats.popular_entries.length > 0 && (
                <div className="mt-8">
                  <h3 className="text-lg font-medium text-neutral-200 mb-4">Popular Cache Entries</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-neutral-700">
                      <thead>
                        <tr>
                          <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">ID</th>
                          <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Natural Language Query</th>
                          <th className="px-4 py-3 bg-neutral-800 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Usage Count</th>
                        </tr>
                      </thead>
                      <tbody className="bg-neutral-900 divide-y divide-neutral-800">
                        {stats.popular_entries.map((entry) => (
                          <tr key={entry.id}>
                            <td className="px-4 py-3 text-sm text-neutral-300">{entry.id}</td>
                            <td className="px-4 py-3 text-sm text-neutral-300">{entry.nl_query}</td>
                            <td className="px-4 py-3 text-sm text-neutral-300">{entry.usage_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Logs Tab */}
        <TabsContent value="logs">
          <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
            <CardHeader>
              <CardTitle className="text-neutral-200">Detailed Usage Logs</CardTitle>
              <CardDescription className="text-neutral-400">
                Recent cache query logs with status and similarity scores
              </CardDescription>
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <div className="flex items-center justify-center h-40">
                  <p className="text-neutral-400">Loading usage logs...</p>
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
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-neutral-300">{log.prompt ? (log.prompt.length > 50 ? `${log.prompt.substring(0, 50)}...` : log.prompt) : '-'}</td>
                            <td className="px-4 py-3 text-sm text-neutral-300">{(log.similarity_score * 100).toFixed(2)}%</td>
                            <td className="px-4 py-3 text-sm text-neutral-300">{log.cache_entry_id || '-'}</td>
                            <td className="px-4 py-3 text-sm text-neutral-300">
                              {log.llm_used ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-900 text-purple-300">
                                  Yes
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-700 text-neutral-300">
                                  No
                                </span>
                              )}
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
                        Showing page {page} of {totalPages}
                      </div>
                      <div className="flex gap-2">
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
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-40">
                  <Info className="h-12 w-12 text-neutral-600 mb-2" />
                  <p className="text-neutral-400">No usage logs available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
} 