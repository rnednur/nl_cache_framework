'use client'

import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Textarea } from '../../components/ui/textarea'
import { Switch } from '../../components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../../components/ui/dialog'
import {
  Search,
  Database,
  Code,
  Activity,
  Calendar,
  TrendingUp,
  Users,
  Plus,
  ExternalLink,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Tag,
  Zap,
  FileText,
  Settings,
  Copy,
  Eye
} from 'lucide-react'
import api from '../../services/api'

interface CacheEntry {
  id: number
  nl_query: string
  template_type: string
  catalog_type?: string
  catalog_subtype?: string
  catalog_name?: string
  reasoning_trace?: string
  tags?: Record<string, any>
  execution_count: number
  success_rate: number
  complexity_level?: string
  health_status?: string
  last_executed?: string
  created_at: string
  updated_at: string
  has_hot_command: boolean
  hot_command_name?: string
  hot_command_id?: number
}

interface CacheEntryDetail {
  id: number
  nl_query: string
  template: string
  template_type: string
  is_template: boolean
  entity_replacements?: Record<string, any>
  reasoning_trace?: string
  tags?: Record<string, any>
  catalog_type?: string
  catalog_subtype?: string
  catalog_name?: string
  status: string
  tool_capabilities?: string[]
  execution_config?: Record<string, any>
  health_status?: string
  recipe_steps?: any[]
  required_tools?: number[]
  execution_time_estimate?: number
  complexity_level?: string
  success_rate?: number
  last_executed?: string
  execution_count?: number
  created_at: string
  updated_at: string
  has_hot_command: boolean
  hot_command?: any
}

const TEMPLATE_TYPE_ICONS = {
  sql: Database,
  duckdb_sql: Database,
  workflow: Activity,
  recipe: Activity,
  api: Code,
  mcp_tool: Settings,
  function: Code,
  script: FileText,
  prompt: FileText,
  cli: FileText
} as const

const HEALTH_STATUS_COLORS = {
  healthy: 'bg-green-500',
  degraded: 'bg-yellow-500',
  unhealthy: 'bg-red-500',
  unknown: 'bg-gray-500'
} as const

const COMPLEXITY_COLORS = {
  beginner: 'bg-green-100 text-green-800',
  intermediate: 'bg-yellow-100 text-yellow-800',
  advanced: 'bg-red-100 text-red-800'
} as const

export default function CacheExplorerPage() {
  const [entries, setEntries] = useState<CacheEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [templateTypeFilter, setTemplateTypeFilter] = useState<string>('all')
  const [catalogTypeFilter, setCatalogTypeFilter] = useState<string>('all')
  const [showOnlyAvailable, setShowOnlyAvailable] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<CacheEntryDetail | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [createCommandOpen, setCreateCommandOpen] = useState(false)
  const [commandForm, setCommandForm] = useState({
    command_name: '',
    display_name: '',
    description: '',
    is_public: false,
    tags: [] as string[]
  })
  const [creating, setCreating] = useState(false)
  
  // Metadata state for dynamic dropdowns
  const [catalogValues, setCatalogValues] = useState<{
    catalog_types: string[]
    catalog_subtypes: string[]
    catalog_names: string[]
    template_types: string[]
  }>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: [],
    template_types: []
  })
  const [catalogLoading, setCatalogLoading] = useState(true)

  const fetchCacheEntries = async () => {
    try {
      setLoading(true)
      const data = await api.getAvailableCacheEntries({
        template_type: templateTypeFilter === 'all' ? undefined : templateTypeFilter,
        catalog_type: catalogTypeFilter === 'all' ? undefined : catalogTypeFilter,
        limit: 100
      })
      setEntries(data)
    } catch (error: any) {
      toast.error('Failed to load cache entries')
      console.error('Error loading cache entries:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchEntryDetails = async (entryId: number) => {
    try {
      setDetailsLoading(true)
      const details = await api.getCacheEntryDetails(entryId)
      setSelectedEntry(details)
    } catch (error: any) {
      toast.error('Failed to load entry details')
      console.error('Error loading entry details:', error)
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleCreateCommand = async () => {
    if (!selectedEntry || !commandForm.command_name) {
      toast.error('Please fill in the command name')
      return
    }

    try {
      setCreating(true)
      await api.createHotCommandFromCache({
        cache_entry_id: selectedEntry.id,
        command_name: commandForm.command_name,
        display_name: commandForm.display_name || undefined,
        description: commandForm.description || undefined,
        is_public: commandForm.is_public,
        tags: commandForm.tags.length > 0 ? commandForm.tags : undefined
      })

      toast.success(`Hot command "${commandForm.command_name}" created successfully!`)
      setCreateCommandOpen(false)
      setCommandForm({
        command_name: '',
        display_name: '',
        description: '',
        is_public: false,
        tags: []
      })
      
      // Refresh the entries to update the has_hot_command status
      await fetchCacheEntries()
      
      // Refresh details if the same entry is selected
      if (selectedEntry) {
        await fetchEntryDetails(selectedEntry.id)
      }
    } catch (error: any) {
      toast.error('Failed to create hot command')
      console.error('Error creating hot command:', error)
    } finally {
      setCreating(false)
    }
  }

  const handleTagsChange = (tagsString: string) => {
    const tags = tagsString.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0)
    setCommandForm(prev => ({ ...prev, tags }))
  }

  const openCreateDialog = (entry: CacheEntry) => {
    fetchEntryDetails(entry.id)
    setCommandForm({
      command_name: entry.nl_query.toLowerCase().replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30),
      display_name: entry.nl_query.substring(0, 100),
      description: entry.reasoning_trace || `Generated from cache entry: ${entry.nl_query}`,
      is_public: false,
      tags: entry.tags ? Object.keys(entry.tags) : []
    })
    setCreateCommandOpen(true)
  }

  useEffect(() => {
    fetchCacheEntries()
  }, [templateTypeFilter, catalogTypeFilter])
  
  useEffect(() => {
    loadCatalogValues()
  }, [])
  
  const loadCatalogValues = async () => {
    try {
      setCatalogLoading(true)
      const values = await api.getCatalogValues()
      setCatalogValues(values)
    } catch (error: any) {
      console.error('Failed to load catalog values:', error)
      // Keep default empty arrays - no hardcoded fallbacks
    } finally {
      setCatalogLoading(false)
    }
  }

  const filteredEntries = entries.filter(entry => {
    const matchesSearch = !searchQuery || 
      entry.nl_query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (entry.catalog_type && entry.catalog_type.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (entry.reasoning_trace && entry.reasoning_trace.toLowerCase().includes(searchQuery.toLowerCase()))
    
    const matchesAvailability = !showOnlyAvailable || !entry.has_hot_command
    
    return matchesSearch && matchesAvailability
  })

  const getTemplateIcon = (templateType: string) => {
    const IconComponent = TEMPLATE_TYPE_ICONS[templateType as keyof typeof TEMPLATE_TYPE_ICONS] || FileText
    return <IconComponent className="h-4 w-4" />
  }

  const formatLastExecuted = (lastExecuted?: string) => {
    if (!lastExecuted) return 'Never'
    const date = new Date(lastExecuted)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 3600 * 24))
    
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days} days ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Cache Explorer</h1>
          <p className="text-muted-foreground">
            Browse ThinkForge cache entries and convert them to Hot Commands
          </p>
        </div>
        <Badge variant="secondary" className="text-sm">
          {filteredEntries.length} entries
        </Badge>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search entries..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="template-type">Template Type</Label>
              <Select value={templateTypeFilter} onValueChange={setTemplateTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  {catalogValues.template_types.map(type => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="catalog-type">Catalog Type</Label>
              <Select value={catalogTypeFilter} onValueChange={setCatalogTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All catalogs" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All catalogs</SelectItem>
                  {catalogValues.catalog_types.map(type => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2 pt-6">
              <Switch
                id="show-available"
                checked={showOnlyAvailable}
                onCheckedChange={setShowOnlyAvailable}
              />
              <Label htmlFor="show-available">Only available</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Entries List */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2">Loading cache entries...</span>
          </div>
        ) : filteredEntries.length === 0 ? (
          <div className="text-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No cache entries found</h3>
            <p className="text-muted-foreground">
              {searchQuery || templateTypeFilter || catalogTypeFilter 
                ? 'Try adjusting your filters' 
                : 'No cache entries available'}
            </p>
          </div>
        ) : (
          filteredEntries.map((entry) => (
            <Card key={entry.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      {getTemplateIcon(entry.template_type)}
                      <Badge variant="outline" className="text-xs">
                        {entry.template_type}
                      </Badge>
                      {entry.catalog_type && (
                        <Badge variant="secondary" className="text-xs">
                          {entry.catalog_type}
                        </Badge>
                      )}
                      {entry.health_status && (
                        <div className="flex items-center gap-1">
                          <div className={`w-2 h-2 rounded-full ${HEALTH_STATUS_COLORS[entry.health_status as keyof typeof HEALTH_STATUS_COLORS] || 'bg-gray-500'}`} />
                          <span className="text-xs text-muted-foreground capitalize">
                            {entry.health_status}
                          </span>
                        </div>
                      )}
                      {entry.has_hot_command && (
                        <Badge className="text-xs bg-green-100 text-green-800">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Has Command
                        </Badge>
                      )}
                    </div>

                    <h3 className="text-lg font-semibold mb-2 line-clamp-2">
                      {entry.nl_query}
                    </h3>

                    {entry.reasoning_trace && (
                      <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                        {entry.reasoning_trace}
                      </p>
                    )}

                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Activity className="h-3 w-3" />
                        {entry.execution_count} executions
                      </div>
                      <div className="flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        {entry.success_rate.toFixed(1)}% success
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatLastExecuted(entry.last_executed)}
                      </div>
                      {entry.complexity_level && (
                        <Badge variant="outline" className={`text-xs ${COMPLEXITY_COLORS[entry.complexity_level as keyof typeof COMPLEXITY_COLORS]}`}>
                          {entry.complexity_level}
                        </Badge>
                      )}
                    </div>

                    {entry.tags && Object.keys(entry.tags).length > 0 && (
                      <div className="flex items-center gap-1 mt-2">
                        <Tag className="h-3 w-3" />
                        <div className="flex flex-wrap gap-1">
                          {Object.keys(entry.tags).slice(0, 3).map(tag => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {Object.keys(entry.tags).length > 3 && (
                            <span className="text-xs text-muted-foreground">
                              +{Object.keys(entry.tags).length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => fetchEntryDetails(entry.id)}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      View
                    </Button>
                    
                    {entry.has_hot_command ? (
                      <Button variant="outline" size="sm" disabled>
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Has Command
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => openCreateDialog(entry)}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Create Command
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Entry Details Dialog */}
      <Dialog open={!!selectedEntry} onOpenChange={() => setSelectedEntry(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedEntry && getTemplateIcon(selectedEntry.template_type)}
              Cache Entry Details
            </DialogTitle>
            <DialogDescription>
              Entry ID: {selectedEntry?.id}
            </DialogDescription>
          </DialogHeader>
          
          {detailsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="ml-2">Loading details...</span>
            </div>
          ) : selectedEntry && (
            <div className="space-y-6">
              {/* Basic Info */}
              <div>
                <h4 className="font-semibold mb-2">Query</h4>
                <p className="text-sm bg-muted p-3 rounded-md">{selectedEntry.nl_query}</p>
              </div>

              {/* Template */}
              <div>
                <h4 className="font-semibold mb-2">Template</h4>
                <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-40">
                  {selectedEntry.template}
                </pre>
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-semibold mb-2">Metadata</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Template Type:</span>
                      <Badge variant="outline">{selectedEntry.template_type}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <Badge variant={selectedEntry.status === 'active' ? 'default' : 'secondary'}>
                        {selectedEntry.status}
                      </Badge>
                    </div>
                    {selectedEntry.catalog_type && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Catalog:</span>
                        <span>{selectedEntry.catalog_type}</span>
                      </div>
                    )}
                    {selectedEntry.complexity_level && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Complexity:</span>
                        <Badge variant="outline" className={COMPLEXITY_COLORS[selectedEntry.complexity_level as keyof typeof COMPLEXITY_COLORS]}>
                          {selectedEntry.complexity_level}
                        </Badge>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Performance</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Executions:</span>
                      <span>{selectedEntry.execution_count || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Success Rate:</span>
                      <span>{((selectedEntry.success_rate || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Last Executed:</span>
                      <span>{formatLastExecuted(selectedEntry.last_executed)}</span>
                    </div>
                    {selectedEntry.health_status && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Health:</span>
                        <div className="flex items-center gap-1">
                          <div className={`w-2 h-2 rounded-full ${HEALTH_STATUS_COLORS[selectedEntry.health_status as keyof typeof HEALTH_STATUS_COLORS] || 'bg-gray-500'}`} />
                          <span className="capitalize">{selectedEntry.health_status}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Hot Command Status */}
              {selectedEntry.has_hot_command && selectedEntry.hot_command && (
                <div>
                  <h4 className="font-semibold mb-2">Existing Hot Command</h4>
                  <div className="bg-green-50 border border-green-200 rounded-md p-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <span className="font-medium">{selectedEntry.hot_command.command_name}</span>
                      <Badge variant="outline">
                        {selectedEntry.hot_command.usage_count} uses
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {selectedEntry.hot_command.display_name}
                    </p>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setSelectedEntry(null)}>
                  Close
                </Button>
                {!selectedEntry.has_hot_command && (
                  <Button onClick={() => openCreateDialog(selectedEntry as any)}>
                    <Plus className="h-4 w-4 mr-1" />
                    Create Hot Command
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create Command Dialog */}
      <Dialog open={createCommandOpen} onOpenChange={setCreateCommandOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Hot Command</DialogTitle>
            <DialogDescription>
              Convert this cache entry into a reusable Hot Command
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="command_name">Command Name *</Label>
                <Input
                  id="command_name"
                  value={commandForm.command_name}
                  onChange={(e) => setCommandForm(prev => ({ ...prev, command_name: e.target.value }))}
                  placeholder="my_command"
                  pattern="^[a-zA-Z0-9_]+$"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Letters, numbers, and underscores only
                </p>
              </div>

              <div>
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  value={commandForm.display_name}
                  onChange={(e) => setCommandForm(prev => ({ ...prev, display_name: e.target.value }))}
                  placeholder="My Command"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={commandForm.description}
                onChange={(e) => setCommandForm(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Command description..."
                rows={3}
              />
            </div>

            <div>
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                value={commandForm.tags.join(', ')}
                onChange={(e) => handleTagsChange(e.target.value)}
                placeholder="tag1, tag2, tag3"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="is_public"
                checked={commandForm.is_public}
                onCheckedChange={(checked) => setCommandForm(prev => ({ ...prev, is_public: checked }))}
              />
              <Label htmlFor="is_public">Make command public</Label>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setCreateCommandOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateCommand} disabled={creating || !commandForm.command_name}>
                {creating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-1" />
                    Create Command
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}