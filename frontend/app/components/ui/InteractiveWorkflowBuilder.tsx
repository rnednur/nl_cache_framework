'use client'

import React, { useState, useCallback, useEffect, useRef } from 'react'
import ReactFlow, {
  Controls,
  Background,
  addEdge,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  Connection,
  BackgroundVariant,
  ReactFlowProvider,
  useReactFlow,
  Panel,
} from 'reactflow'
import { Search, Plus, Trash2, Play, Database, Code, Globe, Zap, ChevronLeft, ChevronRight, Menu, Focus, MousePointer2, RotateCcw, Save, Maximize, Minimize, Filter, X } from 'lucide-react'
import api, { CacheItem } from '@/app/services/api'

interface InteractiveWorkflowBuilderProps {
  catalogType?: string
  catalogSubtype?: string
  catalogName?: string
  initialNodes?: Node[]
  initialEdges?: Edge[]
  onWorkflowChange?: (nodes: Node[], edges: Edge[]) => void
  onMaximizeChange?: (isMaximized: boolean) => void
  isMaximized?: boolean
}

// Icon mapping for different template types
const getTemplateIcon = (templateType: string) => {
  const iconMap: Record<string, string> = {
    sql: '🗄️',
    api: '🌐',
    workflow: '⚡',
    script: '📜',
    url: '🔗',
    cli: '💻',
    prompt: '🤖',
    configuration: '⚙️',
    graphql: '📊',
    nosql: '🍃',
  }
  return iconMap[templateType] || '📋'
}

const getTemplateColor = (templateType: string) => {
  const colorMap: Record<string, string> = {
    sql: '#3b82f6',
    api: '#10b981',
    workflow: '#8b5cf6',
    script: '#f59e0b',
    url: '#06b6d4',
    cli: '#6b7280',
    prompt: '#ec4899',
    configuration: '#84cc16',
    graphql: '#f97316',
    nosql: '#14b8a6',
  }
  return colorMap[templateType] || '#6b7280'
}

let nodeIdCounter = 1
const generateNodeId = () => `node_${nodeIdCounter++}`

const WorkflowBuilderComponent: React.FC<InteractiveWorkflowBuilderProps> = ({
  catalogType,
  catalogSubtype,
  catalogName,
  initialNodes,
  initialEdges,
  onWorkflowChange,
  onMaximizeChange,
  isMaximized: isMaximizedProp,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null)
  const { screenToFlowPosition, fitView, getViewport, zoomTo, setCenter } = useReactFlow()

  // Default initial nodes if none provided
  const defaultNodes = [
    {
      id: 'start',
      type: 'input',
      position: { x: 250, y: 50 },
      data: { label: 'Start' },
      style: {
        background: '#10b981',
        color: 'white',
        border: '2px solid #047857',
        borderRadius: '8px',
      },
    },
  ]

  // ReactFlow state
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes || defaultNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges || [])

  // Search and cache state
  const [searchQuery, setSearchQuery] = useState('')
  const [cacheEntries, setCacheEntries] = useState<CacheItem[]>([])
  const [filteredEntries, setFilteredEntries] = useState<CacheItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<CacheItem | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [internalIsMaximized, setInternalIsMaximized] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  
  // Use controlled state if onMaximizeChange is provided, otherwise use internal state
  const isMaximized = onMaximizeChange ? (isMaximizedProp ?? false) : internalIsMaximized
  const setIsMaximized = onMaximizeChange ? 
    (value: boolean | ((prev: boolean) => boolean)) => {
      const newValue = typeof value === 'function' ? value(isMaximized) : value
      onMaximizeChange(newValue)
    } : 
    setInternalIsMaximized
  
  // Advanced filters
  const [filterCatalogType, setFilterCatalogType] = useState<string>('all')
  const [filterCatalogSubtype, setFilterCatalogSubtype] = useState<string>('all')
  const [filterTemplateType, setFilterTemplateType] = useState<string>('all')
  
  // Available filter options (will be populated from actual data)
  const [availableCatalogTypes, setAvailableCatalogTypes] = useState<string[]>([])
  const [availableCatalogSubtypes, setAvailableCatalogSubtypes] = useState<string[]>([])
  const [availableTemplateTypes, setAvailableTemplateTypes] = useState<string[]>([])

  // Generate a unique key for this workflow session
  const workflowKey = `workflow_${catalogType || 'default'}_${catalogSubtype || 'default'}_${catalogName || 'default'}`

  // Store previous initial props to detect actual changes
  const prevInitialNodesRef = useRef<Node[] | undefined>(undefined)
  const prevInitialEdgesRef = useRef<Edge[] | undefined>(undefined)

  // Update nodes and edges when initial props actually change
  useEffect(() => {
    if (initialNodes && initialNodes.length > 0) {
      // Only update if the props actually changed (not just a re-render)
      if (JSON.stringify(initialNodes) !== JSON.stringify(prevInitialNodesRef.current)) {
        setNodes(initialNodes)
        prevInitialNodesRef.current = initialNodes
      }
    }
  }, [initialNodes])

  useEffect(() => {
    if (initialEdges && initialEdges.length > 0) {
      // Only update if the props actually changed (not just a re-render)  
      if (JSON.stringify(initialEdges) !== JSON.stringify(prevInitialEdgesRef.current)) {
        setEdges(initialEdges)
        prevInitialEdgesRef.current = initialEdges
      }
    }
  }, [initialEdges])

  // Load saved workflow state on mount and when workflow key changes
  useEffect(() => {
    try {
      const savedWorkflow = localStorage.getItem(workflowKey)
      if (savedWorkflow) {
        const { nodes: savedNodes, edges: savedEdges, sidebarCollapsed: savedSidebarState } = JSON.parse(savedWorkflow)
        
        // Only restore if we have meaningful saved data and current state is minimal
        const currentNodeCount = nodes.length
        const hasOnlyStartNode = currentNodeCount <= 1 && nodes.every(n => n.id === 'start')
        
        if (savedNodes && Array.isArray(savedNodes) && savedNodes.length > 0 && hasOnlyStartNode) {
          setNodes(savedNodes)
          console.log('Restored nodes from localStorage:', { count: savedNodes.length })
        }
        
        if (savedEdges && Array.isArray(savedEdges) && edges.length === 0) {
          setEdges(savedEdges)
          console.log('Restored edges from localStorage:', { count: savedEdges.length })
        }
        
        if (typeof savedSidebarState === 'boolean') {
          setSidebarCollapsed(savedSidebarState)
        }
      }
    } catch (error) {
      console.warn('Failed to restore workflow state:', error)
    }
  }, [workflowKey]) // Removed setNodes, setEdges to prevent infinite loops

  // Save workflow state whenever nodes, edges, or sidebar state changes (debounced)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      try {
        const workflowState = {
          nodes,
          edges,
          sidebarCollapsed,
          timestamp: new Date().toISOString()
        }
        localStorage.setItem(workflowKey, JSON.stringify(workflowState))
        console.log('Saved workflow state to localStorage:', { nodes: nodes.length, edges: edges.length })
      } catch (error) {
        console.warn('Failed to save workflow state:', error)
      }
    }, 500) // 500ms debounce

    return () => clearTimeout(timeoutId)
  }, [nodes, edges, sidebarCollapsed, workflowKey])

  // Auto-save search query
  useEffect(() => {
    try {
      localStorage.setItem(`${workflowKey}_search`, searchQuery)
    } catch (error) {
      console.warn('Failed to save search query:', error)
    }
  }, [searchQuery, workflowKey])

  // Restore search query
  useEffect(() => {
    try {
      const savedSearchQuery = localStorage.getItem(`${workflowKey}_search`)
      if (savedSearchQuery) {
        setSearchQuery(savedSearchQuery)
      }
    } catch (error) {
      console.warn('Failed to restore search query:', error)
    }
  }, [workflowKey])

  // Fetch cache entries
  useEffect(() => {
    const fetchCacheEntries = async () => {
      setLoading(true)
      try {
        const response = await api.getCacheEntries(1, 50) // Get first 50 entries
        setCacheEntries(response.items)
        setFilteredEntries(response.items)
        
        // Extract unique filter options from the data
        const catalogTypes = [...new Set(response.items.map(item => item.catalog_type).filter(Boolean))]
        const catalogSubtypes = [...new Set(response.items.map(item => item.catalog_subtype).filter(Boolean))]
        const templateTypes = [...new Set(response.items.map(item => item.template_type).filter(Boolean))]
        
        setAvailableCatalogTypes(catalogTypes)
        setAvailableCatalogSubtypes(catalogSubtypes)
        setAvailableTemplateTypes(templateTypes)
      } catch (error) {
        console.error('Failed to fetch cache entries:', error)
        // Fallback mock data
        const mockEntries: CacheItem[] = [
          {
            id: 1,
            nl_query: 'Fetch user data from database',
            template: 'SELECT * FROM users WHERE id = {{user_id}}',
            template_type: 'sql',
            reasoning_trace: 'Query to retrieve user information',
            is_template: true,
            entity_replacements: {},
            tags: { database: ['users'] },
            status: 'active',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: 2,
            nl_query: 'Send notification via API',
            template: '{"url": "https://api.notifications.com/send", "method": "POST"}',
            template_type: 'api',
            reasoning_trace: 'API call to send notifications',
            is_template: true,
            entity_replacements: {},
            tags: { notification: ['api'] },
            status: 'active',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: 3,
            nl_query: 'Transform data with Python script',
            template: 'def transform_data(input_data):\n    return processed_data',
            template_type: 'script',
            reasoning_trace: 'Python script for data transformation',
            is_template: true,
            entity_replacements: {},
            tags: { python: ['transform'] },
            status: 'active',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]
        setCacheEntries(mockEntries)
        setFilteredEntries(mockEntries)
        
        // Set mock filter options
        setAvailableCatalogTypes(['fullflow', 'subflow', 'automation'])
        setAvailableCatalogSubtypes(['interactive', 'batch', 'scheduled'])
        setAvailableTemplateTypes(['sql', 'api', 'script', 'workflow'])
      } finally {
        setLoading(false)
      }
    }

    fetchCacheEntries()
  }, [])

  // Filter entries based on search query and advanced filters
  useEffect(() => {
    let filtered = [...cacheEntries]

    // Apply text search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(entry =>
        entry.nl_query.toLowerCase().includes(query) ||
        entry.template_type.toLowerCase().includes(query) ||
        (entry.reasoning_trace && entry.reasoning_trace.toLowerCase().includes(query)) ||
        (entry.catalog_type && entry.catalog_type.toLowerCase().includes(query)) ||
        (entry.catalog_subtype && entry.catalog_subtype.toLowerCase().includes(query))
      )
    }

    // Apply catalog type filter
    if (filterCatalogType !== 'all') {
      filtered = filtered.filter(entry => entry.catalog_type === filterCatalogType)
    }

    // Apply catalog subtype filter
    if (filterCatalogSubtype !== 'all') {
      filtered = filtered.filter(entry => entry.catalog_subtype === filterCatalogSubtype)
    }

    // Apply template type filter
    if (filterTemplateType !== 'all') {
      filtered = filtered.filter(entry => entry.template_type === filterTemplateType)
    }

    setFilteredEntries(filtered)
  }, [searchQuery, cacheEntries, filterCatalogType, filterCatalogSubtype, filterTemplateType])

  // Store the latest onWorkflowChange callback in a ref to avoid dependency issues
  const onWorkflowChangeRef = useRef(onWorkflowChange)
  useEffect(() => {
    onWorkflowChangeRef.current = onWorkflowChange
  }, [onWorkflowChange])

  // Handle workflow changes (debounced to prevent rapid-fire updates)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (onWorkflowChangeRef.current) {
        onWorkflowChangeRef.current(nodes, edges)
      }
    }, 100) // 100ms debounce

    return () => clearTimeout(timeoutId)
  }, [nodes, edges])

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Toggle sidebar with Ctrl+B or Cmd+B
      if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
        event.preventDefault()
        setSidebarCollapsed(prev => !prev)
      }
      
      // Toggle maximize with F11 or Ctrl+M
      if (event.key === 'F11' || ((event.ctrlKey || event.metaKey) && event.key === 'm')) {
        event.preventDefault()
        setIsMaximized(prev => !prev)
      }
      
      // Toggle filters with Ctrl+F
      if ((event.ctrlKey || event.metaKey) && event.key === 'f' && !sidebarCollapsed) {
        event.preventDefault()
        setShowFilters(prev => !prev)
      }
      
      // Escape key to close filters or un-maximize
      if (event.key === 'Escape') {
        if (showFilters) {
          setShowFilters(false)
        } else if (isMaximized) {
          setIsMaximized(false)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sidebarCollapsed, showFilters, isMaximized])

  // Handle connections between nodes
  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        animated: true,
        style: { stroke: '#10b981', strokeWidth: 2 },
      }
      setEdges((eds) => addEdge(newEdge, eds))
    },
    [setEdges]
  )

  // Handle adding a cache entry as a node
  const addCacheEntryAsNode = (entry: CacheItem, position?: { x: number; y: number }) => {
    let nodePosition = position

    // If no position specified, place node in the center of the visible viewport
    if (!nodePosition) {
      const viewport = getViewport()
      const centerX = -viewport.x + (window.innerWidth - (sidebarCollapsed ? 0 : 320)) / 2 / viewport.zoom
      const centerY = -viewport.y + window.innerHeight / 2 / viewport.zoom
      
      // Add some randomness to avoid overlapping nodes
      const randomOffsetX = (Math.random() - 0.5) * 100
      const randomOffsetY = (Math.random() - 0.5) * 100
      
      nodePosition = { 
        x: centerX + randomOffsetX, 
        y: centerY + randomOffsetY 
      }
    }

    const newNode: Node = {
      id: generateNodeId(),
      type: 'default',
      position: nodePosition,
      data: {
        label: `${getTemplateIcon(entry.template_type)} ${entry.nl_query}`,
        cacheEntryId: entry.id,
        templateType: entry.template_type,
        template: entry.template,
      },
      style: {
        background: getTemplateColor(entry.template_type),
        color: 'white',
        border: '2px solid #374151',
        borderRadius: '8px',
        fontSize: '12px',
        fontWeight: 'bold',
        width: 200,
        textAlign: 'center',
      },
      selected: true, // Auto-select the new node for visual feedback
    }
    
    setNodes((nds) => [...nds.map(n => ({ ...n, selected: false })), newNode])
    
    // Always ensure the new node is visible
    setTimeout(() => {
      if (!position) {
        // If double-clicked (no explicit position), fit all nodes in view
        fitView({ padding: 0.1, duration: 800 })
      } else {
        // If dragged to specific position, center the view on the new node
        setCenter(nodePosition.x, nodePosition.y, { zoom: 1, duration: 600 })
      }
    }, 150)
  }

  // Handle drag and drop
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      if (!reactFlowWrapper.current) return

      const entryId = event.dataTransfer.getData('application/cache-entry')
      if (!entryId) return

      const entry = cacheEntries.find(e => e.id.toString() === entryId)
      if (!entry) return

      // Get the exact drop position relative to the ReactFlow canvas
      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect()
      const position = screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      })

      // Ensure the position is within reasonable bounds
      const clampedPosition = {
        x: Math.max(0, Math.min(position.x, 2000)),
        y: Math.max(0, Math.min(position.y, 2000))
      }

      addCacheEntryAsNode(entry, clampedPosition)
    },
    [screenToFlowPosition, cacheEntries, addCacheEntryAsNode]
  )

  // Handle drag start for cache entries
  const onDragStart = (event: React.DragEvent, entry: CacheItem) => {
    event.dataTransfer.setData('application/cache-entry', entry.id.toString())
    event.dataTransfer.effectAllowed = 'move'
  }

  // Delete selected nodes
  const deleteSelected = () => {
    const selectedNodeIds = nodes.filter(node => node.selected && node.id !== 'start').map(node => node.id)
    const selectedEdgeIds = edges.filter(edge => edge.selected).map(edge => edge.id)

    setNodes(nds => nds.filter(node => !selectedNodeIds.includes(node.id)))
    setEdges(eds => eds.filter(edge => 
      !selectedEdgeIds.includes(edge.id) && 
      !selectedNodeIds.includes(edge.source) && 
      !selectedNodeIds.includes(edge.target)
    ))
  }

  // Clear entire workflow
  const clearWorkflow = () => {
    if (confirm('Are you sure you want to clear the entire workflow? This will remove all nodes and connections.')) {
      setNodes([
        {
          id: 'start',
          type: 'input',
          position: { x: 250, y: 50 },
          data: { label: 'Start' },
          style: {
            background: '#10b981',
            color: 'white',
            border: '2px solid #047857',
            borderRadius: '8px',
          },
        },
      ])
      setEdges([])
      
      // Clear from localStorage
      try {
        localStorage.removeItem(workflowKey)
        console.log('Cleared workflow from localStorage')
      } catch (error) {
        console.warn('Failed to clear workflow from localStorage:', error)
      }
    }
  }

  return (
    <div className={`flex bg-neutral-950 text-white relative transition-all duration-300 ${
      (isMaximized && !onMaximizeChange)
        ? 'fixed inset-0 z-50 h-screen w-screen' 
        : 'h-full'
    }`}>
      {/* Left Sidebar - Cache Entry Search */}
      <div className={`${sidebarCollapsed ? 'w-0' : 'w-80'} bg-neutral-900 border-r border-neutral-800 flex flex-col transition-all duration-300 overflow-hidden`}>
        {!sidebarCollapsed && (
          <>
            <div className="p-4 border-b border-neutral-800">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold">Cache Entries</h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowFilters(prev => !prev)}
                    className={`p-1 hover:bg-neutral-800 rounded transition-colors ${
                      showFilters ? 'text-green-400' : 'text-neutral-400'
                    }`}
                    title="Toggle filters (Ctrl+F)"
                  >
                    <Filter className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setIsMaximized(prev => !prev)}
                    className="p-1 hover:bg-neutral-800 rounded transition-colors"
                    title={`${isMaximized ? 'Minimize' : 'Maximize'} (F11 or Ctrl+M)`}
                  >
                    {isMaximized ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={() => setSidebarCollapsed(true)}
                    className="p-1 hover:bg-neutral-800 rounded transition-colors"
                    title="Collapse sidebar (Ctrl+B)"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Search Bar */}
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-neutral-400" />
                <input
                  type="text"
                  placeholder="Search entries..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-neutral-800 border border-neutral-700 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>

              {/* Advanced Filters */}
              {showFilters && (
                <div className="space-y-3 p-3 bg-neutral-800/50 rounded-lg border border-neutral-700">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-neutral-300">Advanced Filters</span>
                    <button
                      onClick={() => {
                        setFilterCatalogType('all')
                        setFilterCatalogSubtype('all')
                        setFilterTemplateType('all')
                      }}
                      className="text-xs text-neutral-400 hover:text-neutral-300"
                    >
                      Clear All
                    </button>
                  </div>

                  <div>
                    <label className="block text-xs text-neutral-400 mb-1">Catalog Type</label>
                    <select
                      value={filterCatalogType}
                      onChange={(e) => setFilterCatalogType(e.target.value)}
                      className="w-full px-2 py-1 bg-neutral-700 border border-neutral-600 rounded text-xs focus:outline-none focus:ring-1 focus:ring-green-500"
                    >
                      <option value="all">All Types</option>
                      {availableCatalogTypes.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-neutral-400 mb-1">Catalog Subtype</label>
                    <select
                      value={filterCatalogSubtype}
                      onChange={(e) => setFilterCatalogSubtype(e.target.value)}
                      className="w-full px-2 py-1 bg-neutral-700 border border-neutral-600 rounded text-xs focus:outline-none focus:ring-1 focus:ring-green-500"
                    >
                      <option value="all">All Subtypes</option>
                      {availableCatalogSubtypes.map(subtype => (
                        <option key={subtype} value={subtype}>{subtype}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-neutral-400 mb-1">Template Type</label>
                    <select
                      value={filterTemplateType}
                      onChange={(e) => setFilterTemplateType(e.target.value)}
                      className="w-full px-2 py-1 bg-neutral-700 border border-neutral-600 rounded text-xs focus:outline-none focus:ring-1 focus:ring-green-500"
                    >
                      <option value="all">All Templates</option>
                      {availableTemplateTypes.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>

                  <div className="text-xs text-neutral-500 pt-2 border-t border-neutral-700">
                    Showing {filteredEntries.length} of {cacheEntries.length} entries
                  </div>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {loading ? (
                <div className="text-center text-neutral-400 py-8">Loading cache entries...</div>
              ) : filteredEntries.length === 0 ? (
                <div className="text-center text-neutral-400 py-8">
                  {searchQuery ? 'No entries match your search' : 'No cache entries found'}
                </div>
              ) : (
                filteredEntries.map((entry) => (
                  <div
                    key={entry.id}
                    draggable
                    onDragStart={(e) => onDragStart(e, entry)}
                    onDoubleClick={() => addCacheEntryAsNode(entry)}
                    className="p-3 bg-neutral-800 border border-neutral-700 rounded-lg cursor-grab hover:bg-neutral-750 active:cursor-grabbing transition-colors group"
                    onClick={() => setSelectedEntry(entry)}
                    title="Drag to canvas or double-click to add at center"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{getTemplateIcon(entry.template_type)}</span>
                      <span className="text-xs px-2 py-1 rounded-full" style={{ 
                        backgroundColor: getTemplateColor(entry.template_type) + '20',
                        color: getTemplateColor(entry.template_type)
                      }}>
                        {entry.template_type}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-white mb-1 line-clamp-2">
                      {entry.nl_query}
                    </div>
                    {entry.reasoning_trace && (
                      <div className="text-xs text-neutral-400 line-clamp-2">
                        {entry.reasoning_trace}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t border-neutral-800 text-xs text-neutral-400 space-y-1">
              <div className="flex items-center gap-2">
                <MousePointer2 className="h-3 w-3" />
                <span>Drag entries to canvas or double-click to add at center</span>
              </div>
              <div className="flex items-center gap-2">
                <Focus className="h-3 w-3" />
                <span>Use "Fit View" button if nodes go out of sight</span>
              </div>
              <div className="flex items-center gap-2">
                <Save className="h-3 w-3 text-green-400" />
                <span>Workflow auto-saved locally - changes persist across sessions</span>
              </div>
              <div className="text-xs text-neutral-500 pt-2 border-t border-neutral-600">
                <div className="grid grid-cols-2 gap-1">
                  <span>Ctrl+B: Toggle sidebar</span>
                  <span>Ctrl+F: Toggle filters</span>
                  <span>Ctrl+M/F11: Maximize</span>
                  <span>Esc: Close/minimize</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Collapse/Expand Button */}
      {sidebarCollapsed && (
        <div className="absolute left-0 top-4 z-10">
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="p-3 bg-neutral-800 border border-neutral-700 rounded-r-lg hover:bg-neutral-700 transition-colors shadow-lg"
            title="Expand sidebar (Ctrl+B)"
          >
            <div className="flex flex-col items-center gap-1">
              <Menu className="h-4 w-4" />
              <span className="text-xs">Search</span>
            </div>
          </button>
        </div>
      )}

      {/* Maximize/Minimize Button for collapsed sidebar */}
      {sidebarCollapsed && (
        <div className="absolute left-0 top-20 z-10">
          <button
            onClick={() => setIsMaximized(prev => !prev)}
            className="p-3 bg-neutral-800 border border-neutral-700 rounded-r-lg hover:bg-neutral-700 transition-colors shadow-lg"
            title={`${isMaximized ? 'Minimize' : 'Maximize'} (F11 or Ctrl+M)`}
          >
            <div className="flex flex-col items-center gap-1">
              {isMaximized ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
              <span className="text-xs">{isMaximized ? 'Min' : 'Max'}</span>
            </div>
          </button>
        </div>
      )}

      {/* Main Canvas */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            fitView
            className="bg-neutral-950"
          >
            <Controls className="bg-neutral-800 border-neutral-700 text-white" />
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} className="bg-neutral-950" />
            
            <Panel position="top-left">
              <div className="flex items-center gap-2 bg-neutral-800/90 px-3 py-2 rounded-md text-xs">
                <Save className="h-3 w-3 text-green-400" />
                <span className="text-neutral-300">Auto-saved • {nodes.length - 1} nodes • {edges.length} connections</span>
              </div>
            </Panel>

            <Panel position="top-right">
              <div className="flex gap-2">
                <button
                  onClick={() => setSidebarCollapsed(prev => !prev)}
                  className="px-3 py-2 bg-neutral-700 text-white rounded-md hover:bg-neutral-600 flex items-center gap-1 text-sm"
                  title={`${sidebarCollapsed ? 'Show' : 'Hide'} search sidebar (Ctrl+B)`}
                >
                  {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                  {sidebarCollapsed ? 'Show' : 'Hide'} Search
                </button>
                <button
                  onClick={() => fitView({ padding: 0.1, duration: 800 })}
                  className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-1 text-sm"
                  title="Fit all nodes in view"
                >
                  <Focus className="h-4 w-4" />
                  Fit View
                </button>
                <button
                  onClick={clearWorkflow}
                  className="px-3 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 flex items-center gap-1 text-sm"
                  title="Clear entire workflow"
                >
                  <RotateCcw className="h-4 w-4" />
                  Clear
                </button>
                <button
                  onClick={deleteSelected}
                  disabled={!nodes.some(n => n.selected && n.id !== 'start') && !edges.some(e => e.selected)}
                  className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 text-sm"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </button>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>
    </div>
  )
}

const InteractiveWorkflowBuilder: React.FC<InteractiveWorkflowBuilderProps> = (props) => {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderComponent {...props} />
    </ReactFlowProvider>
  )
}

export default InteractiveWorkflowBuilder