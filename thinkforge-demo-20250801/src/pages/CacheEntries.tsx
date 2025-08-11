import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import api, { CacheItem, CatalogValues } from '@/services/api'
import { Eye, Plus, Search, Filter, RefreshCw, Database } from 'lucide-react'
import toast from 'react-hot-toast'

export default function CacheEntries() {
  const [entries, setEntries] = useState<CacheItem[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [templateType, setTemplateType] = useState<string>('')
  const [catalogType, setCatalogType] = useState<string>('')
  const [catalogSubtype, setCatalogSubtype] = useState<string>('')
  const [catalogName, setCatalogName] = useState<string>('')
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: []
  })
  const pageSize = 10

  const fetchEntries = async () => {
    try {
      setLoading(true)
      const result = await api.getCacheEntries(
        page, 
        pageSize, 
        templateType || undefined,
        searchQuery || undefined,
        catalogType || undefined,
        catalogSubtype || undefined,
        catalogName || undefined
      )
      setEntries(result.items)
      setTotal(result.total)
    } catch (error) {
      console.error('Error fetching entries:', error)
      toast.error('Failed to fetch cache entries')
    } finally {
      setLoading(false)
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

  useEffect(() => {
    fetchEntries()
  }, [page, templateType, catalogType, catalogSubtype, catalogName])

  useEffect(() => {
    fetchCatalogValues()
  }, [])

  const handleSearch = () => {
    setPage(1)
    fetchEntries()
  }

  const clearFilters = () => {
    setSearchQuery('')
    setTemplateType('')
    setCatalogType('')
    setCatalogSubtype('')
    setCatalogName('')
    setPage(1)
  }

  const totalPages = Math.ceil(total / pageSize)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
      case 'inactive':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Cache Entries</h1>
          <p className="text-muted-foreground">Manage and search your cache entries by catalog</p>
        </div>
        <Button asChild>
          <Link to="/create-entry">
            <Plus className="h-4 w-4 mr-2" />
            Create Entry
          </Link>
        </Button>
      </div>

      {/* Advanced Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Search & Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search Query */}
          <div className="flex gap-2">
            <div className="flex-1">
              <Label htmlFor="search">Search Query</Label>
              <Input
                id="search"
                placeholder="Search in natural language queries..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={handleSearch}>
                <Search className="h-4 w-4 mr-2" />
                Search
              </Button>
              <Button variant="outline" onClick={clearFilters}>
                Clear
              </Button>
            </div>
          </div>

          {/* Filter Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label>Template Type</Label>
              <Select value={templateType} onValueChange={setTemplateType}>
                <SelectTrigger>
                  <SelectValue placeholder="All template types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All template types</SelectItem>
                  <SelectItem value="sql">SQL</SelectItem>
                  <SelectItem value="api">API</SelectItem>
                  <SelectItem value="url">URL</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Catalog Type</Label>
              <Select value={catalogType} onValueChange={setCatalogType}>
                <SelectTrigger>
                  <SelectValue placeholder="All catalog types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All catalog types</SelectItem>
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
                  <SelectValue placeholder="All catalog subtypes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All catalog subtypes</SelectItem>
                  {catalogValues.catalog_subtypes.map((subtype) => (
                    <SelectItem key={subtype} value={subtype}>
                      {subtype}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Catalog Name</Label>
              <Select value={catalogName} onValueChange={setCatalogName}>
                <SelectTrigger>
                  <SelectValue placeholder="All catalog names" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All catalog names</SelectItem>
                  {catalogValues.catalog_names.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Cache Entries ({total} total)
            </div>
            <Button variant="outline" size="sm" onClick={fetchEntries}>
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
                Loading cache entries...
              </div>
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">No cache entries found</h3>
              <p>Try adjusting your search criteria or create a new entry.</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-4 font-medium">Query</th>
                      <th className="text-left p-4 font-medium">Type</th>
                      <th className="text-left p-4 font-medium">Catalog</th>
                      <th className="text-left p-4 font-medium">Tags</th>
                      <th className="text-left p-4 font-medium">Status</th>
                      <th className="text-left p-4 font-medium">Usage</th>
                      <th className="text-left p-4 font-medium">Updated</th>
                      <th className="text-left p-4 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((entry, index) => (
                      <tr key={entry.id} className={`border-b hover:bg-muted/50 ${index % 2 === 0 ? 'bg-background' : 'bg-muted/20'}`}>
                        <td className="p-4">
                          <div className="max-w-xs">
                            <div className="font-medium truncate" title={entry.nl_query}>
                              {entry.nl_query}
                            </div>
                            <div className="text-xs text-muted-foreground">ID: {entry.id}</div>
                          </div>
                        </td>
                        <td className="p-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                            {entry.template_type.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="text-sm space-y-1">
                            {entry.catalog_type ? (
                              <>
                                <div className="font-medium">{entry.catalog_type}</div>
                                {entry.catalog_subtype && (
                                  <div className="text-muted-foreground text-xs">
                                    {entry.catalog_subtype}
                                  </div>
                                )}
                                {entry.catalog_name && (
                                  <div className="text-muted-foreground text-xs">
                                    {entry.catalog_name}
                                  </div>
                                )}
                              </>
                            ) : (
                              <span className="text-muted-foreground text-xs">No catalog</span>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {entry.tags && entry.tags.length > 0 ? (
                              entry.tags.slice(0, 2).map((tag, index) => (
                                <span 
                                  key={index} 
                                  className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300"
                                >
                                  {tag}
                                </span>
                              ))
                            ) : (
                              <span className="text-muted-foreground text-xs">No tags</span>
                            )}
                            {entry.tags && entry.tags.length > 2 && (
                              <span className="text-xs text-muted-foreground">
                                +{entry.tags.length - 2} more
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(entry.status)}`}>
                            {entry.status}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="text-sm font-medium">{entry.usage_count}</div>
                          <div className="text-xs text-muted-foreground">uses</div>
                        </td>
                        <td className="p-4 text-sm text-muted-foreground">
                          {formatDate(entry.updated_at)}
                        </td>
                        <td className="p-4">
                          <Button variant="ghost" size="sm" asChild>
                            <Link to={`/cache-entries/${entry.id}`}>
                              <Eye className="h-4 w-4" />
                            </Link>
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
                Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total} entries
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