'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'react-hot-toast'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/app/components/ui/card'
import { Button } from '@/app/components/ui/button'
import { PageHeader } from '@/app/components/ui/PageHeader'
import { Input } from '@/app/components/ui/input'
import { Badge } from '@/app/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import {
  Search,
  Plus,
  Wrench,
  Play,
  Settings,
  Bot,
  Code,
  Webhook,
  Globe,
  Filter,
  Loader2,
} from 'lucide-react'
import api, { type CacheItem } from '@/app/services/api'

interface Tool extends CacheItem {
  tool_capabilities?: string[]
  tool_dependencies?: Record<string, any>
  health_status?: string
  last_tested?: string
}

const TOOL_TYPES = {
  mcp_tool: { label: 'MCP Tool', icon: Webhook, color: 'bg-blue-500' },
  agent: { label: 'AI Agent', icon: Bot, color: 'bg-purple-500' },
  function: { label: 'Function', icon: Code, color: 'bg-green-500' },
  api: { label: 'API', icon: Globe, color: 'bg-orange-500' },
  workflow: { label: 'Workflow', icon: Settings, color: 'bg-teal-500' },
} as const

const HEALTH_STATUS_COLOR = {
  healthy: 'bg-green-500',
  degraded: 'bg-yellow-500',
  unhealthy: 'bg-red-500',
  unknown: 'bg-muted',
} as const

export default function Tools() {
  const router = useRouter()
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [selectedCatalogType, setSelectedCatalogType] = useState<string>('all')
  const [selectedCatalogSubtype, setSelectedCatalogSubtype] = useState<string>('all')
  const [selectedCatalogName, setSelectedCatalogName] = useState<string>('all')
  const [filteredTools, setFilteredTools] = useState<Tool[]>([])
  const [catalogTypes, setCatalogTypes] = useState<string[]>([])
  const [catalogSubtypes, setCatalogSubtypes] = useState<string[]>([])
  const [catalogNames, setCatalogNames] = useState<string[]>([])

  useEffect(() => {
    fetchTools()
  }, [])

  useEffect(() => {
    filterTools()
  }, [tools, searchQuery, selectedType, selectedStatus, selectedCatalogType, selectedCatalogSubtype, selectedCatalogName])
  
  useEffect(() => {
    // Extract unique catalog values for dropdown options
    const types = new Set<string>()
    const subtypes = new Set<string>()
    const names = new Set<string>()
    
    tools.forEach(tool => {
      if (tool.catalog_type) types.add(tool.catalog_type)
      if (tool.catalog_subtype) subtypes.add(tool.catalog_subtype)
      if (tool.catalog_name) names.add(tool.catalog_name)
    })
    
    setCatalogTypes(Array.from(types).sort())
    setCatalogSubtypes(Array.from(subtypes).sort())
    setCatalogNames(Array.from(names).sort())
  }, [tools])

  const fetchTools = async () => {
    setLoading(true)
    setError(null)
    try {
      // Filter for tool-specific template types
      const toolTypes = ['mcp_tool', 'agent', 'function', 'api', 'workflow']
      const response = await api.getCacheEntries(1, 100, toolTypes.join(','))
      setTools(response.items)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tools')
      toast.error('Failed to load tools')
    } finally {
      setLoading(false)
    }
  }

  const filterTools = () => {
    let filtered = [...tools]

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(tool => 
        tool.nl_query.toLowerCase().includes(query) ||
        tool.template_type.toLowerCase().includes(query) ||
        tool.catalog_type?.toLowerCase().includes(query) ||
        tool.catalog_subtype?.toLowerCase().includes(query) ||
        tool.catalog_name?.toLowerCase().includes(query) ||
        tool.tool_capabilities?.some(cap => cap.toLowerCase().includes(query))
      )
    }

    // Filter by tool type
    if (selectedType !== 'all') {
      filtered = filtered.filter(tool => tool.template_type === selectedType)
    }

    // Filter by health status
    if (selectedStatus !== 'all') {
      filtered = filtered.filter(tool => tool.health_status === selectedStatus)
    }

    // Filter by catalog type
    if (selectedCatalogType !== 'all') {
      filtered = filtered.filter(tool => tool.catalog_type === selectedCatalogType)
    }

    // Filter by catalog subtype
    if (selectedCatalogSubtype !== 'all') {
      filtered = filtered.filter(tool => tool.catalog_subtype === selectedCatalogSubtype)
    }

    // Filter by catalog name
    if (selectedCatalogName !== 'all') {
      filtered = filtered.filter(tool => tool.catalog_name === selectedCatalogName)
    }

    setFilteredTools(filtered)
  }

  const handleToolTest = async (toolId: number) => {
    try {
      toast.loading('Testing tool...', { id: 'test' })
      // This would call a test endpoint when implemented
      await new Promise(resolve => setTimeout(resolve, 1000)) // Placeholder
      toast.success('Tool test completed', { id: 'test' })
      fetchTools() // Refresh to get updated health status
    } catch (err: any) {
      toast.error('Tool test failed', { id: 'test' })
    }
  }

  const getToolIcon = (templateType: string) => {
    const toolType = TOOL_TYPES[templateType as keyof typeof TOOL_TYPES]
    if (toolType) {
      const Icon = toolType.icon
      return <Icon className="h-5 w-5" />
    }
    return <Wrench className="h-5 w-5" />
  }

  const getToolTypeColor = (templateType: string) => {
    return TOOL_TYPES[templateType as keyof typeof TOOL_TYPES]?.color || 'bg-muted'
  }

  const getHealthStatusColor = (status?: string) => {
    return HEALTH_STATUS_COLOR[status as keyof typeof HEALTH_STATUS_COLOR] || 'bg-muted'
  }

  const formatLastTested = (lastTested?: string) => {
    if (!lastTested) return 'Never'
    const date = new Date(lastTested)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 3600 * 24))
    
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days} days ago`
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`
    return `${Math.floor(days / 30)} months ago`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading tools...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 mb-4">{error}</p>
        <Button onClick={fetchTools}>Try Again</Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Tool Hub"
        description="Discover and manage your tools, agents, and functions"
        icon={Wrench}
        actions={
          <Button onClick={() => router.push('/tools/new')} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Tool
          </Button>
        }
      />

      {/* Filters */}
      <Card className="workflow-card bg-card border-2 border-card-border">
        <CardContent className="pt-6">
          <div className="space-y-4">
            {/* Search and Primary Filters */}
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search tools by name, type, catalog, or capabilities..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 bg-card border-border"
                  />
                </div>
              </div>
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger className="w-48 bg-card border-border">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Tool Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="mcp_tool">MCP Tools</SelectItem>
                  <SelectItem value="agent">AI Agents</SelectItem>
                  <SelectItem value="function">Functions</SelectItem>
                  <SelectItem value="api">APIs</SelectItem>
                  <SelectItem value="workflow">Workflows</SelectItem>
                </SelectContent>
              </Select>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger className="w-48 bg-card border-border">
                  <SelectValue placeholder="Health Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="healthy">Healthy</SelectItem>
                  <SelectItem value="degraded">Degraded</SelectItem>
                  <SelectItem value="unhealthy">Unhealthy</SelectItem>
                  <SelectItem value="unknown">Unknown</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Catalog Filters */}
            <div className="flex flex-col md:flex-row gap-4 pt-4 border-t border-border">
              <div className="text-sm font-medium text-foreground flex items-center min-w-fit">
                Catalog Filters:
              </div>
              <Select value={selectedCatalogType} onValueChange={setSelectedCatalogType}>
                <SelectTrigger className="w-full md:w-48 bg-card border-border">
                  <SelectValue placeholder="Catalog Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Catalog Types</SelectItem>
                  {catalogTypes.map(type => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={selectedCatalogSubtype} onValueChange={setSelectedCatalogSubtype}>
                <SelectTrigger className="w-full md:w-48 bg-card border-border">
                  <SelectValue placeholder="Catalog Subtype" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Subtypes</SelectItem>
                  {catalogSubtypes.map(subtype => (
                    <SelectItem key={subtype} value={subtype}>{subtype}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={selectedCatalogName} onValueChange={setSelectedCatalogName}>
                <SelectTrigger className="w-full md:w-48 bg-card border-border">
                  <SelectValue placeholder="Catalog Name" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Catalog Names</SelectItem>
                  {catalogNames.map(name => (
                    <SelectItem key={name} value={name}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Active Filters Summary */}
            {(selectedType !== 'all' || selectedStatus !== 'all' || selectedCatalogType !== 'all' || selectedCatalogSubtype !== 'all' || selectedCatalogName !== 'all' || searchQuery.trim()) && (
              <div className="flex items-center gap-2 pt-2 border-t border-border">
                <span className="text-xs text-muted-foreground">Active filters:</span>
                <div className="flex flex-wrap gap-1">
                  {searchQuery.trim() && (
                    <Badge variant="secondary" className="text-xs bg-blue-600/20 text-blue-400 border border-blue-600/30">
                      Search: "{searchQuery}"
                    </Badge>
                  )}
                  {selectedType !== 'all' && (
                    <Badge variant="secondary" className="text-xs bg-purple-600/20 text-purple-400 border border-purple-600/30">
                      Type: {TOOL_TYPES[selectedType as keyof typeof TOOL_TYPES]?.label || selectedType}
                    </Badge>
                  )}
                  {selectedStatus !== 'all' && (
                    <Badge variant="secondary" className="text-xs bg-yellow-600/20 text-yellow-400 border border-yellow-600/30">
                      Status: {selectedStatus}
                    </Badge>
                  )}
                  {selectedCatalogType !== 'all' && (
                    <Badge variant="secondary" className="text-xs bg-green-600/20 text-green-400 border border-green-600/30">
                      Catalog: {selectedCatalogType}
                    </Badge>
                  )}
                  {selectedCatalogSubtype !== 'all' && (
                    <Badge variant="secondary" className="text-xs bg-green-600/20 text-green-400 border border-green-600/30">
                      Subtype: {selectedCatalogSubtype}
                    </Badge>
                  )}
                  {selectedCatalogName !== 'all' && (
                    <Badge variant="secondary" className="text-xs bg-green-600/20 text-green-400 border border-green-600/30">
                      Name: {selectedCatalogName}
                    </Badge>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs text-muted-foreground hover:text-foreground ml-auto"
                  onClick={() => {
                    setSearchQuery('')
                    setSelectedType('all')
                    setSelectedStatus('all')
                    setSelectedCatalogType('all')
                    setSelectedCatalogSubtype('all')
                    setSelectedCatalogName('all')
                  }}
                >
                  Clear All
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tools Grid */}
      {filteredTools.length === 0 ? (
        <Card className="bg-input border-border">
          <CardContent className="text-center py-8">
            <Wrench className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              {tools.length === 0 
                ? "No tools found. Create your first tool to get started."
                : "No tools match your current filters."
              }
            </p>
            {tools.length === 0 && (
              <Button 
                onClick={() => router.push('/tools/new')} 
                className="mt-4 gap-2"
              >
                <Plus className="h-4 w-4" />
                Create Tool
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTools.map((tool) => (
            <Card 
              key={tool.id} 
              className="workflow-card cursor-pointer border-2 border-card-border bg-card"
              onClick={() => router.push(`/tools/${tool.id}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${getToolTypeColor(tool.template_type)}`}>
                      {getToolIcon(tool.template_type)}
                    </div>
                    <div>
                      <CardTitle className="text-base line-clamp-1 text-foreground">
                        {tool.nl_query}
                      </CardTitle>
                      <CardDescription className="capitalize text-muted-foreground">
                        {TOOL_TYPES[tool.template_type as keyof typeof TOOL_TYPES]?.label || tool.template_type}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div 
                      className={`w-3 h-3 rounded-full ${getHealthStatusColor(tool.health_status)}`}
                      title={`Health: ${tool.health_status || 'unknown'}`}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* Catalog Information */}
                {(tool.catalog_type || tool.catalog_subtype || tool.catalog_name) && (
                  <div className="mb-3">
                    <p className="text-xs text-muted-foreground mb-2">Catalog</p>
                    <div className="flex flex-wrap gap-1">
                      {tool.catalog_type && (
                        <Badge variant="outline" className="text-xs border-green-600 text-green-300">
                          {tool.catalog_type}
                        </Badge>
                      )}
                      {tool.catalog_subtype && (
                        <Badge variant="outline" className="text-xs border-green-600 text-green-300">
                          {tool.catalog_subtype}
                        </Badge>
                      )}
                      {tool.catalog_name && (
                        <Badge variant="outline" className="text-xs border-green-600 text-green-300">
                          {tool.catalog_name}
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* Capabilities */}
                {tool.tool_capabilities && tool.tool_capabilities.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-muted-foreground mb-2">Capabilities</p>
                    <div className="flex flex-wrap gap-1">
                      {tool.tool_capabilities.slice(0, 3).map((capability, index) => (
                        <Badge key={index} variant="secondary" className="text-xs bg-muted/60 text-foreground border border-muted">
                          {capability}
                        </Badge>
                      ))}
                      {tool.tool_capabilities.length > 3 && (
                        <Badge variant="outline" className="text-xs border-border text-muted-foreground">
                          +{tool.tool_capabilities.length - 3}
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* Last tested */}
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                  <span>Last tested: {formatLastTested(tool.last_tested)}</span>
                  <span className="capitalize">{tool.status}</span>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 gap-2 border-border text-foreground hover:bg-accent"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleToolTest(tool.id)
                    }}
                  >
                    <Play className="h-3 w-3" />
                    Test
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-border text-foreground hover:bg-accent"
                    onClick={(e) => {
                      e.stopPropagation()
                      router.push(`/tools/${tool.id}/edit`)
                    }}
                  >
                    <Settings className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}