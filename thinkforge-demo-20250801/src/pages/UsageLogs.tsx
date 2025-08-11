import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import api, { CacheItem, CatalogValues } from '@/services/api'
import { Activity, TrendingUp, Filter, RefreshCw, Clock, Eye, BarChart3, Calendar } from 'lucide-react'
import toast from 'react-hot-toast'

interface UsageLogEntry {
  id: string
  timestamp: string
  query: string
  cache_entry_id: number
  catalog_type?: string
  catalog_subtype?: string
  catalog_name?: string
  response_time: number
  success: boolean
}

interface UsageStats {
  total_queries: number
  cache_hits: number
  cache_misses: number
  avg_response_time: number
  top_catalogs: Array<{
    catalog: string
    count: number
  }>
  hourly_usage: Array<{
    hour: string
    count: number
  }>
}

export default function UsageLogs() {
  const [logs, setLogs] = useState<UsageLogEntry[]>([])
  const [stats, setStats] = useState<UsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [catalogType, setCatalogType] = useState('')
  const [catalogSubtype, setCatalogSubtype] = useState('')
  const [catalogName, setCatalogName] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'error'>('all')
  const [dateFilter, setDateFilter] = useState<'1h' | '24h' | '7d' | '30d'>('24h')
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: []
  })
  const pageSize = 20

  // Mock data - In a real app, this would come from your backend API
  const generateMockLogs = (): UsageLogEntry[] => {
    const queries = [
      'Get all customers from New York',
      'Find active users in the system',
      'List products by category',
      'Show sales data for last month',
      'Retrieve user preferences',
      'Get weather information for city',
      'Find top performing products',
      'List recent transactions'
    ]
    
    const catalogs = [
      { type: 'customer_data', subtype: 'geographical', name: 'customer_locations' },
      { type: 'user_management', subtype: 'status', name: 'user_status' },
      { type: 'weather', subtype: 'api', name: 'weather_api' },
      { type: 'sales', subtype: 'analytics', name: 'sales_analytics' },
      { type: 'api', subtype: 'external', name: 'third_party_api' }
    ]

    return Array.from({ length: 100 }, (_, i) => {
      const catalog = catalogs[Math.floor(Math.random() * catalogs.length)]
      const isSuccess = Math.random() > 0.1 // 90% success rate
      
      return {
        id: `log_${i}`,
        timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
        query: queries[Math.floor(Math.random() * queries.length)],
        cache_entry_id: Math.floor(Math.random() * 1000) + 16000,
        catalog_type: catalog.type,
        catalog_subtype: catalog.subtype,
        catalog_name: catalog.name,
        response_time: Math.random() * 2000 + 100, // 100-2100ms
        success: isSuccess
      }
    }).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  }

  const generateMockStats = (filteredLogs: UsageLogEntry[]): UsageStats => {
    const successful = filteredLogs.filter(log => log.success)
    const failed = filteredLogs.filter(log => !log.success)
    
    const catalogCounts = filteredLogs.reduce((acc, log) => {
      const catalog = `${log.catalog_type} > ${log.catalog_subtype} > ${log.catalog_name}`
      acc[catalog] = (acc[catalog] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    const hourlyData = Array.from({ length: 24 }, (_, hour) => {
      const count = filteredLogs.filter(log => 
        new Date(log.timestamp).getHours() === hour
      ).length
      return { hour: `${hour}:00`, count }
    })

    return {
      total_queries: filteredLogs.length,
      cache_hits: successful.length,
      cache_misses: failed.length,
      avg_response_time: filteredLogs.reduce((sum, log) => sum + log.response_time, 0) / filteredLogs.length || 0,
      top_catalogs: Object.entries(catalogCounts)
        .map(([catalog, count]) => ({ catalog, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5),
      hourly_usage: hourlyData
    }
  }

  const fetchCatalogValues = async () => {
    try {
      const values = await api.getCatalogValues()
      setCatalogValues(values)
    } catch (error) {
      console.error('Error fetching catalog values:', error)
    }
  }

  const fetchLogs = async () => {
    try {
      setLoading(true)
      
      // In a real app, this would be an API call
      const allLogs = generateMockLogs()
      
      // Apply filters
      let filteredLogs = allLogs.filter(log => {
        if (searchQuery && !log.query.toLowerCase().includes(searchQuery.toLowerCase())) return false
        if (catalogType && log.catalog_type !== catalogType) return false
        if (catalogSubtype && log.catalog_subtype !== catalogSubtype) return false
        if (catalogName && log.catalog_name !== catalogName) return false
        if (statusFilter === 'success' && !log.success) return false
        if (statusFilter === 'error' && log.success) return false
        
        // Date filter
        const logDate = new Date(log.timestamp)
        const now = new Date()
        const diffHours = (now.getTime() - logDate.getTime()) / (1000 * 60 * 60)
        
        switch (dateFilter) {
          case '1h': return diffHours <= 1
          case '24h': return diffHours <= 24
          case '7d': return diffHours <= 24 * 7
          case '30d': return diffHours <= 24 * 30
          default: return true
        }
      })

      setTotal(filteredLogs.length)
      
      // Paginate
      const start = (page - 1) * pageSize
      const paginatedLogs = filteredLogs.slice(start, start + pageSize)
      
      setLogs(paginatedLogs)
      setStats(generateMockStats(filteredLogs))
      
    } catch (error) {
      console.error('Error fetching logs:', error)
      toast.error('Failed to fetch usage logs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCatalogValues()
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [page, searchQuery, catalogType, catalogSubtype, catalogName, statusFilter, dateFilter])

  const clearFilters = () => {
    setSearchQuery('')
    setCatalogType('')
    setCatalogSubtype('')
    setCatalogName('')
    setStatusFilter('all')
    setDateFilter('24h')
    setPage(1)
  }

  const totalPages = Math.ceil(total / pageSize)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const formatResponseTime = (time: number) => {
    return `${time.toFixed(0)}ms`
  }

  const getStatusColor = (success: boolean) => {
    return success 
      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Usage Logs</h1>
        <p className="text-muted-foreground">Monitor cache usage patterns and performance by catalog</p>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Queries</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_queries.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">In selected timeframe</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cache Hit Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.total_queries > 0 ? ((stats.cache_hits / stats.total_queries) * 100).toFixed(1) : 0}%
              </div>
              <p className="text-xs text-muted-foreground">
                {stats.cache_hits} hits, {stats.cache_misses} misses
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatResponseTime(stats.avg_response_time)}</div>
              <p className="text-xs text-muted-foreground">Average across all queries</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Top Catalog</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-sm font-bold truncate">
                {stats.top_catalogs[0]?.catalog.split(' > ')[0] || 'N/A'}
              </div>
              <p className="text-xs text-muted-foreground">
                {stats.top_catalogs[0]?.count || 0} queries
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </div>
            <Button variant="outline" size="sm" onClick={clearFilters}>
              Clear All
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div className="md:col-span-2">
              <Label htmlFor="search">Search Query</Label>
              <Input
                id="search"
                placeholder="Search in queries..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div>
              <Label>Time Range</Label>
              <Select value={dateFilter} onValueChange={(value: any) => setDateFilter(value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">Last Hour</SelectItem>
                  <SelectItem value="24h">Last 24 Hours</SelectItem>
                  <SelectItem value="7d">Last 7 Days</SelectItem>
                  <SelectItem value="30d">Last 30 Days</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Status</Label>
              <Select value={statusFilter} onValueChange={(value: any) => setStatusFilter(value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="success">Success Only</SelectItem>
                  <SelectItem value="error">Errors Only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Catalog Type</Label>
              <Select value={catalogType} onValueChange={setCatalogType}>
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All types</SelectItem>
                  {catalogValues.catalog_types.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Catalog Subtype</Label>
              <Select value={catalogSubtype} onValueChange={setCatalogSubtype}>
                <SelectTrigger>
                  <SelectValue placeholder="All subtypes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All subtypes</SelectItem>
                  {catalogValues.catalog_subtypes.map((subtype) => (
                    <SelectItem key={subtype} value={subtype}>
                      {subtype}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Usage Logs ({total} entries)
            </div>
            <Button variant="outline" size="sm" onClick={fetchLogs}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="flex items-center gap-2 text-muted-foreground">
                <RefreshCw className="h-4 w-4 animate-spin" />
                Loading usage logs...
              </div>
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">No usage logs found</h3>
              <p>Try adjusting your filter criteria.</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-4 font-medium">Timestamp</th>
                      <th className="text-left p-4 font-medium">Query</th>
                      <th className="text-left p-4 font-medium">Catalog</th>
                      <th className="text-left p-4 font-medium">Response Time</th>
                      <th className="text-left p-4 font-medium">Status</th>
                      <th className="text-left p-4 font-medium">Cache Entry</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log, index) => (
                      <tr key={log.id} className={`border-b hover:bg-muted/50 ${index % 2 === 0 ? 'bg-background' : 'bg-muted/20'}`}>
                        <td className="p-4 text-sm text-muted-foreground">
                          <div className="flex items-center gap-2">
                            <Calendar className="h-3 w-3" />
                            {formatDate(log.timestamp)}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="max-w-xs truncate font-medium" title={log.query}>
                            {log.query}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="text-sm space-y-1">
                            <div className="font-medium">{log.catalog_type}</div>
                            <div className="text-xs text-muted-foreground">
                              {log.catalog_subtype} • {log.catalog_name}
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <span className={`text-sm font-medium ${
                            log.response_time > 1000 ? 'text-red-600' : 
                            log.response_time > 500 ? 'text-yellow-600' : 'text-green-600'
                          }`}>
                            {formatResponseTime(log.response_time)}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(log.success)}`}>
                            {log.success ? 'Success' : 'Error'}
                          </span>
                        </td>
                        <td className="p-4">
                          <Button variant="ghost" size="sm" asChild>
                            <a href={`/cache-entries/${log.cache_entry_id}`}>
                              <Eye className="h-4 w-4" />
                            </a>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t">
              <div className="text-sm text-muted-foreground">
                Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total} logs
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                >
                  Previous
                </Button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNum = i + 1
                    return (
                      <Button
                        key={pageNum}
                        variant={page === pageNum ? "default" : "outline"}
                        size="sm"
                        onClick={() => setPage(pageNum)}
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                  {totalPages > 5 && <span className="text-muted-foreground">...</span>}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
} 