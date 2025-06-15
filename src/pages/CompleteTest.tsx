import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import api, { CatalogValues, CompletionResult } from '@/services/api'
import { Play, Search, Settings, Clock, CheckCircle, XCircle, AlertCircle, Filter } from 'lucide-react'
import toast from 'react-hot-toast'

export default function CompleteTest() {
  const [query, setQuery] = useState('')
  const [catalogType, setCatalogType] = useState('')
  const [catalogSubtype, setCatalogSubtype] = useState('')
  const [catalogName, setCatalogName] = useState('')
  const [similarityThreshold, setSimilarityThreshold] = useState(0.85)
  const [limit, setLimit] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CompletionResult | null>(null)
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: []
  })
  const [testHistory, setTestHistory] = useState<Array<{
    query: string
    catalog: string
    results: number
    timestamp: string
    success: boolean
  }>>([])

  const fetchCatalogValues = async () => {
    try {
      const values = await api.getCatalogValues()
      setCatalogValues(values)
    } catch (error) {
      console.error('Error fetching catalog values:', error)
    }
  }

  useEffect(() => {
    fetchCatalogValues()
  }, [])

  const handleTest = async () => {
    if (!query.trim()) {
      toast.error('Please enter a query to test')
      return
    }

    try {
      setLoading(true)
      const completion = await api.completeQuery(
        query,
        catalogType || undefined,
        catalogSubtype || undefined,
        catalogName || undefined,
        similarityThreshold,
        limit
      )
      
      setResult(completion)
      
      // Add to test history
      const catalogInfo = [catalogType, catalogSubtype, catalogName].filter(Boolean).join(' > ') || 'No catalog'
      setTestHistory(prev => [{
        query,
        catalog: catalogInfo,
        results: completion.matches.length,
        timestamp: new Date().toISOString(),
        success: true
      }, ...prev.slice(0, 9)]) // Keep only last 10 tests
      
      if (completion.matches.length > 0) {
        toast.success(`Found ${completion.matches.length} cache matches!`)
      } else {
        toast.success('Test completed - no cache matches found')
      }
    } catch (error: any) {
      console.error('Error testing completion:', error)
      toast.error(error.response?.data?.detail || 'Failed to test completion')
      
      // Add failed test to history
      const catalogInfo = [catalogType, catalogSubtype, catalogName].filter(Boolean).join(' > ') || 'No catalog'
      setTestHistory(prev => [{
        query,
        catalog: catalogInfo,
        results: 0,
        timestamp: new Date().toISOString(),
        success: false
      }, ...prev.slice(0, 9)])
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (success: boolean, hasResults: boolean) => {
    if (!success) return <XCircle className="h-4 w-4 text-red-500" />
    if (hasResults) return <CheckCircle className="h-4 w-4 text-green-500" />
    return <AlertCircle className="h-4 w-4 text-yellow-500" />
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const clearFilters = () => {
    setCatalogType('')
    setCatalogSubtype('')
    setCatalogName('')
    setSimilarityThreshold(0.85)
    setLimit(5)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Test Completion</h1>
        <p className="text-muted-foreground">Test cache completion with catalog-specific filtering</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Test Configuration */}
        <div className="lg:col-span-2 space-y-6">
          {/* Query Input */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Test Query
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="query">Natural Language Query</Label>
                <Textarea
                  id="query"
                  placeholder="Enter your natural language query to test..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={3}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Example: "Get all customers from New York with active status"
                </p>
              </div>
              
              <Button 
                onClick={handleTest} 
                disabled={loading || !query.trim()}
                className="w-full"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Testing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Test Completion
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Catalog Filters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Filter className="h-5 w-5" />
                  Catalog Filters
                </div>
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="catalog_type">Catalog Type</Label>
                  <Select value={catalogType} onValueChange={setCatalogType}>
                    <SelectTrigger>
                      <SelectValue placeholder="Any catalog type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Any catalog type</SelectItem>
                      {catalogValues.catalog_types.map((type) => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="catalog_subtype">Catalog Subtype</Label>
                  <Select value={catalogSubtype} onValueChange={setCatalogSubtype}>
                    <SelectTrigger>
                      <SelectValue placeholder="Any catalog subtype" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Any catalog subtype</SelectItem>
                      {catalogValues.catalog_subtypes.map((subtype) => (
                        <SelectItem key={subtype} value={subtype}>
                          {subtype}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="catalog_name">Catalog Name</Label>
                  <Select value={catalogName} onValueChange={setCatalogName}>
                    <SelectTrigger>
                      <SelectValue placeholder="Any catalog name" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Any catalog name</SelectItem>
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

          {/* Advanced Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Advanced Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="similarity_threshold">Similarity Threshold</Label>
                  <Input
                    id="similarity_threshold"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={similarityThreshold}
                    onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value) || 0)}
                  />
                  <p className="text-sm text-muted-foreground mt-1">
                    Minimum similarity score (0-1)
                  </p>
                </div>

                <div>
                  <Label htmlFor="limit">Result Limit</Label>
                  <Input
                    id="limit"
                    type="number"
                    min="1"
                    max="50"
                    value={limit}
                    onChange={(e) => setLimit(parseInt(e.target.value) || 5)}
                  />
                  <p className="text-sm text-muted-foreground mt-1">
                    Maximum number of results
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Test Results */}
          {result && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {result.matches.length > 0 ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-yellow-500" />
                  )}
                  Test Results
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-foreground">{result.matches.length}</div>
                    <div className="text-sm text-muted-foreground">Matches Found</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-foreground">{result.query_time.toFixed(3)}s</div>
                    <div className="text-sm text-muted-foreground">Query Time</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-foreground">{similarityThreshold}</div>
                    <div className="text-sm text-muted-foreground">Threshold</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-foreground">{result.method}</div>
                    <div className="text-sm text-muted-foreground">Method</div>
                  </div>
                </div>

                {result.matches.length > 0 ? (
                  <div className="space-y-3">
                    <h4 className="font-medium">Cache Matches:</h4>
                    {result.matches.map((match, index) => (
                      <div key={index} className="border rounded-lg p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-sm">Score: {match.score.toFixed(4)}</span>
                          <span className="text-xs text-muted-foreground">ID: {match.entry.id}</span>
                        </div>
                        <div className="text-sm">
                          <div className="font-medium mb-1">{match.entry.nl_query}</div>
                          <div className="text-muted-foreground text-xs">
                            Template: {match.entry.template_type.toUpperCase()}
                            {match.entry.catalog_type && (
                              <> | Catalog: {match.entry.catalog_type}</>
                            )}
                          </div>
                        </div>
                        <div className="bg-muted/50 p-2 rounded text-xs font-mono">
                          {match.entry.template}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <h3 className="text-lg font-medium mb-2">No matches found</h3>
                    <p>Try adjusting your query or reducing the similarity threshold.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Test History Sidebar */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Test History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {testHistory.length > 0 ? (
                <div className="space-y-3">
                  {testHistory.map((test, index) => (
                    <div key={index} className="border rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        {getStatusIcon(test.success, test.results > 0)}
                        <span className="text-xs text-muted-foreground">
                          {formatTimestamp(test.timestamp)}
                        </span>
                      </div>
                      <div className="text-sm">
                        <div className="font-medium truncate" title={test.query}>
                          {test.query}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {test.catalog}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {test.results} results
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No tests performed yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
} 