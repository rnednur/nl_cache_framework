'use client'

import React, { useState, useCallback, useEffect, useRef, useMemo, useLayoutEffect } from 'react'
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
import { Search, Plus, Trash2, Play, Database, Code, Globe, Zap, ChevronLeft, ChevronRight, Menu, Focus, RotateCcw, Save, Maximize, Minimize, Filter, X } from 'lucide-react'
import api, { CacheItem } from '@/app/services/api'
import { NodeDetailModal } from '../../../components/ui/NodeDetailModal'
import { LLMStepEditor } from './LLMStepEditor'

interface InteractiveWorkflowBuilderProps {
  catalogType?: string
  catalogSubtype?: string
  catalogName?: string
  initialNodes?: Node[]
  initialEdges?: Edge[]
  onWorkflowChange?: (nodes: Node[], edges: Edge[]) => void
  onMaximizeChange?: (isMaximized: boolean) => void
  isMaximized?: boolean
  clearOnMount?: boolean  // New prop to force clear on mount
  workflowId?: string | number  // Unique identifier for this workflow session
}

// Icon mapping for different template types
const getTemplateIcon = (templateType: string) => {
  const iconMap: Record<string, string> = {
    duckdb_sql: '⚫🟡',
    llm_step: '✨',
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
    llm_step: '#9333ea',
    duckdb_sql: '#0891b2',
    function: '#059669',
    mcp_tool: '#dc2626',
    agent: '#7c3aed',
    reasoning_steps: '#be185d',
  }
  return colorMap[templateType] || '#6b7280'
}

let nodeIdCounter = 1
const generateNodeId = () => `node_${nodeIdCounter++}`

// Built-in step types that users can add directly to workflows
const builtInStepTypes = [
  {
    id: 'llm_step',
    name: 'LLM Step',
    type: 'llm_step',
    description: 'Process data using Large Language Models (AI/ChatGPT)',
    template: {
      prompt_template: 'Analyze the following data: {input_data}',
      input_parameters: ['input_data'],
      output_format: 'json',
      expected_output: { analysis: 'string', recommendations: 'array' },
      model: 'google/gemini-pro',
      temperature: 0.3,
      max_tokens: 1000,
      system_prompt: 'You are a helpful data analyst.'
    },
    category: 'AI & Processing'
  },
  {
    id: 'duckdb_sql',
    name: 'DuckDB SQL',
    type: 'duckdb_sql',
    description: 'Transform data using SQL analytics with DuckDB',
    template: {
      query: 'SELECT * FROM {table:previous_step} WHERE condition = \'{filter_value}\'',
      validation: {
        row_count_min: 1,
        required_columns: ['id', 'name']
      }
    },
    category: 'Data & Queries'
  },
  {
    id: 'function_step',
    name: 'Custom Function',
    type: 'function',
    description: 'Execute custom Python code for data processing',
    template: {
      code: 'def process_data(input_data):\n    # Your custom logic here\n    return processed_data',
      language: 'python',
      timeout: 60
    },
    category: 'Code & Scripts'
  },
  {
    id: 'api_call',
    name: 'API Call',
    type: 'api',
    description: 'Make HTTP requests to external APIs',
    template: {
      url: 'https://api.example.com/endpoint',
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: { data: '{input_data}' }
    },
    category: 'APIs & Services'
  }
]

const WorkflowBuilderComponent: React.FC<InteractiveWorkflowBuilderProps> = ({
  catalogType,
  catalogSubtype,
  catalogName,
  initialNodes,
  initialEdges,
  onWorkflowChange,
  onMaximizeChange,
  isMaximized: isMaximizedProp,
  clearOnMount = false,
  workflowId,
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

  // Memoized stable values to prevent useEffect dependency issues
  const stableInitialNodes = useMemo(
    () => initialNodes || defaultNodes,
    [initialNodes]
  )

  const stableInitialEdges = useMemo(
    () => initialEdges || [],
    [initialEdges]
  )

  // ReactFlow state with start node guarantee
  const ensureStartNode = (nodeList: Node[]) => {
    const hasStartNode = nodeList.some(n => n.id === 'start')
    if (!hasStartNode) {
      return [defaultNodes[0], ...nodeList] // Add start node at beginning
    }
    return nodeList
  }
  
  const [nodes, setNodes, onNodesChange] = useNodesState(ensureStartNode(stableInitialNodes))
  const [edges, setEdges, onEdgesChange] = useEdgesState(stableInitialEdges)

  // Search and cache state
  const [searchQuery, setSearchQuery] = useState('')
  const [cacheEntries, setCacheEntries] = useState<CacheItem[]>([])
  const [filteredEntries, setFilteredEntries] = useState<CacheItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<CacheItem | null>(null)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [isNodeDetailOpen, setIsNodeDetailOpen] = useState(false)
  const [isLLMEditorOpen, setIsLLMEditorOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [internalIsMaximized, setInternalIsMaximized] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [activeTab, setActiveTab] = useState<'cache' | 'builtin'>('cache')
  
  // Enhanced search state
  const [searchStatus, setSearchStatus] = useState<'idle' | 'searching' | 'semantic' | 'llm' | 'fallback'>('idle')
  const [searchResultsCount, setSearchResultsCount] = useState<number>(0)
  const [searchMethod, setSearchMethod] = useState<'semantic' | 'llm' | 'fallback' | 'none'>('none')
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(10)
  const [totalEntries, setTotalEntries] = useState(0)
  const [hasMorePages, setHasMorePages] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  
  // Semantic search pagination
  const [semanticSearchLimit, setSemanticSearchLimit] = useState(20) // Increased from 10
  const [hasMoreSemanticResults, setHasMoreSemanticResults] = useState(false)
  
  // Use controlled state if onMaximizeChange is provided, otherwise use internal state
  const isMaximized = onMaximizeChange ? (isMaximizedProp ?? false) : internalIsMaximized
  const setIsMaximized = onMaximizeChange ? 
    (value: boolean | ((prev: boolean) => boolean)) => {
      const newValue = typeof value === 'function' ? value(isMaximized) : value
      onMaximizeChange(newValue)
    } : 
    setInternalIsMaximized
  
  // Advanced filters with better template type organization
  const [filterCatalogType, setFilterCatalogType] = useState<string>('all')
  const [filterCatalogSubtype, setFilterCatalogSubtype] = useState<string>('all')
  const [filterTemplateType, setFilterTemplateType] = useState<string>('all')
  
  // Enhanced template type categories for better UX
  const templateTypeCategories = {
    'Data & Queries': ['sql', 'nosql', 'graphql'],
    'APIs & Services': ['api', 'url', 'mcp_tool'],
    'Code & Scripts': ['script', 'cli', 'function'],
    'AI & Processing': ['prompt', 'agent', 'reasoning_steps'],
    'Workflows': ['workflow', 'recipe', 'recipe_step', 'recipe_template'],
    'Configuration': ['configuration', 'dsl', 'regex']
  }
  
  // Available filter options (will be populated from actual data)
  const [availableCatalogTypes, setAvailableCatalogTypes] = useState<string[]>([])
  const [availableCatalogSubtypes, setAvailableCatalogSubtypes] = useState<string[]>([])
  const [availableTemplateTypes, setAvailableTemplateTypes] = useState<string[]>([])

  // Generate a stable key for this workflow session (excluding volatile catalogName)
  const workflowKey = workflowId 
    ? `workflow_${workflowId}` 
    : `workflow_${catalogType || 'default'}_${catalogSubtype || 'default'}`

  // Store previous initial props to detect actual changes
  const prevInitialNodesRef = useRef<Node[] | undefined>(undefined)
  const prevInitialEdgesRef = useRef<Edge[] | undefined>(undefined)

  // Track node additions for layout effects
  const lastAddedNodeRef = useRef<{ position?: { x: number; y: number }; timestamp: number } | null>(null)

  // Update nodes and edges when initial props actually change
  useEffect(() => {
    const serialized = JSON.stringify(stableInitialNodes)
    const prevSerialized = JSON.stringify(prevInitialNodesRef.current)

    if (serialized !== prevSerialized) {
      setNodes(stableInitialNodes)
      prevInitialNodesRef.current = stableInitialNodes
    }
  }, [stableInitialNodes])

  useEffect(() => {
    const serialized = JSON.stringify(stableInitialEdges)
    const prevSerialized = JSON.stringify(prevInitialEdgesRef.current)

    if (serialized !== prevSerialized) {
      setEdges(stableInitialEdges)
      prevInitialEdgesRef.current = stableInitialEdges
    }
  }, [stableInitialEdges])

  // Handle layout effects for newly added nodes
  useLayoutEffect(() => {
    const lastAdded = lastAddedNodeRef.current
    if (lastAdded && Date.now() - lastAdded.timestamp < 1000) { // Only handle recent additions
      if (!lastAdded.position) {
        // If double-clicked (no explicit position), fit all nodes in view
        fitView({ padding: 0.1, duration: 800 })
      } else {
        // If dragged to specific position, center the view on the new node
        setCenter(lastAdded.position.x, lastAdded.position.y, { zoom: 1, duration: 600 })
      }
      // Clear the ref after handling
      lastAddedNodeRef.current = null
    }
  }, [nodes.length, fitView, setCenter])

  // Load saved workflow state on mount and when workflow key changes
  useEffect(() => {
    // If clearOnMount is true, clear localStorage and reset to defaults
    if (clearOnMount) {
      try {
        localStorage.removeItem(workflowKey)
        console.log('Cleared workflow from localStorage due to clearOnMount prop')
      } catch (error) {
        console.warn('Failed to clear workflow from localStorage:', error)
      }
      
      // Reset to default state
      setNodes(defaultNodes)
      setEdges([])
      return
    }

    try {
      const savedWorkflow = localStorage.getItem(workflowKey)
      if (savedWorkflow) {
        const { nodes: savedNodes, edges: savedEdges, sidebarCollapsed: savedSidebarState } = JSON.parse(savedWorkflow)
        
        // Only restore if we have meaningful saved data and current state is minimal
        const currentNodeCount = nodes.length
        const hasOnlyStartNode = currentNodeCount <= 1 && nodes.every(n => n.id === 'start')
        
        if (savedNodes && Array.isArray(savedNodes) && savedNodes.length > 0 && hasOnlyStartNode) {
          // Ensure start node always exists in restored nodes
          const hasStartNode = savedNodes.some(n => n.id === 'start')
          let nodesToRestore = savedNodes
          
          if (!hasStartNode) {
            // Add start node if it doesn't exist in saved nodes
            const startNode = {
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
            }
            nodesToRestore = [startNode, ...savedNodes]
            console.log('Added missing start node to restored nodes')
          }
          
          setNodes(nodesToRestore)
          console.log('Restored nodes from localStorage:', { 
            count: nodesToRestore.length,
            hasStartNode: nodesToRestore.some(n => n.id === 'start')
          })
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
  }, [workflowKey, clearOnMount]) // Added clearOnMount to dependencies

  // Save workflow state whenever nodes, edges, or sidebar state changes (debounced)
  useEffect(() => {
    // Only save if we have nodes (avoid saving empty state)
    if (nodes.length === 0) return
    
    const timeoutId = setTimeout(() => {
      try {
        // Ensure start node is always preserved in saved state
        const hasStartNode = nodes.some(n => n.id === 'start')
        let nodesToSave = nodes
        
        if (!hasStartNode && nodes.length > 0) {
          // Add start node if missing before saving
          const startNode = {
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
          }
          nodesToSave = [startNode, ...nodes]
          console.log('Added missing start node before saving')
        }
        
        const workflowState = {
          nodes: nodesToSave,
          edges,
          sidebarCollapsed,
          timestamp: new Date().toISOString()
        }
        localStorage.setItem(workflowKey, JSON.stringify(workflowState))
        console.log('Saved workflow state to localStorage:', { 
          nodes: nodesToSave.length, 
          edges: edges.length,
          hasStartNode: nodesToSave.some(n => n.id === 'start')
        })
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

  // Fetch cache entries with pagination
  useEffect(() => {
    const fetchCacheEntries = async () => {
      setLoading(true)
      try {
        // Always use paginated fetch for initial load since search requires non-empty query
        // The search endpoint doesn't accept empty queries, so we use getCacheEntries instead
        await fetchPaginatedEntries(
          1, 
          'all', 
          catalogType !== 'all' ? catalogType : 'all', 
          catalogSubtype !== 'all' ? catalogSubtype : 'all'
        )
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
            usage_count: 0,
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
            usage_count: 0,
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
            usage_count: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]
        setCacheEntries(mockEntries)
        setFilteredEntries(mockEntries)
        setSearchMethod('none')
        setSearchResultsCount(mockEntries.length)
        setTotalEntries(mockEntries.length)
        setHasMorePages(false)
        setCurrentPage(1)
      } finally {
        setLoading(false)
      }
    }

    fetchCacheEntries()
  }, [catalogType, catalogSubtype])

  // Fetch catalog values for filters
  useEffect(() => {
    const fetchCatalogValues = async () => {
      try {
        // Get catalog values with hierarchical filtering
        const filters: { catalog_type?: string; catalog_subtype?: string } = {}
        if (catalogType && catalogType !== 'all') {
          filters.catalog_type = catalogType
        }
        if (catalogSubtype && catalogSubtype !== 'all') {
          filters.catalog_subtype = catalogSubtype
        }
        
        const catalogData = await api.getCatalogValues(Object.keys(filters).length > 0 ? filters : undefined)
        
        setAvailableCatalogTypes(catalogData.catalog_types || [])
        setAvailableCatalogSubtypes(catalogData.catalog_subtypes || [])
        
        // Get template types from the actual data, but provide fallback
        let templateTypes = catalogData.template_types || []
        if (templateTypes.length === 0) {
          // Fallback to predefined enum values
          templateTypes = [
            'sql', 'url', 'api', 'workflow', 'graphql', 'regex', 'script', 'nosql',
            'cli', 'prompt', 'configuration', 'reasoning_steps', 'dsl', 'mcp_tool',
            'agent', 'function', 'recipe', 'recipe_step', 'recipe_template'
          ]
        }
        setAvailableTemplateTypes(templateTypes)
        
        console.log('Catalog values loaded:', {
          catalogTypes: catalogData.catalog_types?.length || 0,
          catalogSubtypes: catalogData.catalog_subtypes?.length || 0,
          templateTypes: templateTypes.length
        })
        
        // Also refresh catalog values to ensure filter state is correct
        await refreshCatalogValues()
      } catch (error) {
        console.error('Failed to fetch catalog values:', error)
        // Set fallback values
        setAvailableCatalogTypes(['fullflow', 'subflow', 'automation'])
        setAvailableCatalogSubtypes(['interactive', 'batch', 'scheduled'])
        setAvailableTemplateTypes(['sql', 'api', 'script', 'workflow'])
      }
    }

    fetchCatalogValues()
  }, [catalogType, catalogSubtype])

  // Enhanced hierarchical filtering with better state management
  const refreshCatalogValues = async () => {
    try {
      const filters: { catalog_type?: string; catalog_subtype?: string } = {}
      
      // Only include catalog_type filter if it's selected (not 'all')
      if (filterCatalogType !== 'all') {
        filters.catalog_type = filterCatalogType
      }
      
      // Don't include catalog_subtype in the filter when getting available subtypes
      // We want to see all subtypes for the selected catalog_type
      
      console.log('Refreshing catalog values with filters:', filters)
      
      const catalogData = await api.getCatalogValues(Object.keys(filters).length > 0 ? filters : undefined)
      
      console.log('Received catalog data:', catalogData)
      
      // Always update catalog types (they don't change based on filters)
      setAvailableCatalogTypes(catalogData.catalog_types || [])
      
      // Update subtypes based on selected catalog type only
      setAvailableCatalogSubtypes(catalogData.catalog_subtypes || [])
      
      // If current subtype is not available in the new list, reset it
      if (filterCatalogSubtype !== 'all' && 
          catalogData.catalog_subtypes && 
          !catalogData.catalog_subtypes.includes(filterCatalogSubtype)) {
        console.log(`Resetting catalog subtype '${filterCatalogSubtype}' as it's not available for catalog type '${filterCatalogType}'`)
        setFilterCatalogSubtype('all')
      }
      
      console.log('Catalog values refreshed for filters:', {
        filterCatalogType,
        filterCatalogSubtype,
        availableCatalogTypes: catalogData.catalog_types?.length || 0,
        availableCatalogSubtypes: catalogData.catalog_subtypes?.length || 0
      })
    } catch (error) {
      console.error('Failed to refresh catalog values:', error)
    }
  }

  // Paginated fetch function with optional filtering
  const fetchPaginatedEntries = async (page: number, templateType?: string, catalogType?: string, catalogSubtype?: string) => {
    try {
      const response = await api.getCacheEntries(
        page, 
        pageSize,
        templateType !== 'all' ? templateType : undefined,
        undefined, // searchQuery
        catalogType !== 'all' ? catalogType : undefined,
        catalogSubtype !== 'all' ? catalogSubtype : undefined
      )
      
      if (page === 1) {
        // First page - replace all entries
        setCacheEntries(response.items)
        setFilteredEntries(response.items)
        setCurrentPage(1)
      } else {
        // Subsequent pages - append to existing entries
        setCacheEntries(prev => [...prev, ...response.items])
        setFilteredEntries(prev => [...prev, ...response.items])
        setCurrentPage(page)
      }
      
      setTotalEntries(response.total)
      setHasMorePages(response.items.length === pageSize && response.total > page * pageSize)
      setSearchMethod('none')
      setSearchResultsCount(response.items.length)
      console.log(`Fetched filtered page ${page}:`, {
        entries: response.items.length,
        total: response.total,
        templateType,
        catalogType,
        catalogSubtype
      })
    } catch (error) {
      console.error(`Failed to fetch filtered page ${page}:`, error)
    }
  }
  
  // Server-side filtered request
  const performFilteredRequest = async () => {
    setLoading(true)
    try {
      await fetchPaginatedEntries(
        1,
        filterTemplateType,
        filterCatalogType,
        filterCatalogSubtype
      )
      setSearchStatus('idle')
      setSearchMethod('none')
      setHasMoreSemanticResults(false)
      setSemanticSearchLimit(20)
    } catch (error) {
      console.error('Failed to perform filtered request:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load more paginated entries
  const loadMoreEntries = async () => {
    if (isLoadingMore || !hasMorePages) return
    
    setIsLoadingMore(true)
    try {
      await fetchPaginatedEntries(
        currentPage + 1,
        filterTemplateType,
        filterCatalogType,
        filterCatalogSubtype
      )
    } finally {
      setIsLoadingMore(false)
    }
  }

  // Enhanced search with LLM completion fallback and load more support
  const performEnhancedSearch = async (query: string, loadMore: boolean = false) => {
    if (!query.trim()) {
      // Reset to default entries if no query
      setSearchStatus('idle')
      setSearchMethod('none')
      setSearchResultsCount(0)
      setHasMoreSemanticResults(false)
      setSemanticSearchLimit(20) // Increased from 10
      try {
        // Reset to paginated view with current filters
        await fetchPaginatedEntries(
          1, 
          filterTemplateType,
          filterCatalogType,
          filterCatalogSubtype
        )
      } catch (error) {
        console.error('Failed to reset cache entries:', error)
      }
      return
    }

    // Don't search if query is too short (backend might reject it)
    if (query.trim().length < 2) {
      console.log('Query too short for search, waiting for more input')
      return
    }

    setLoading(true)
    setSearchStatus('searching')
    
    // Determine search limit for load more - start with more results
    const searchLimit = loadMore ? semanticSearchLimit + 20 : 20 // Increased from 10
    
    try {
      // Primary: Semantic search with more lenient threshold
      console.log('Performing semantic search with filters:', {
        query,
        templateType: filterTemplateType,
        catalogType: filterCatalogType,
        catalogSubtype: filterCatalogSubtype,
        catalogName,
        limit: searchLimit
      })
      
      const searchResults = await api.searchCacheEntries(
        query,
        filterTemplateType !== 'all' ? filterTemplateType : undefined,
        0.6, // Lowered from 0.8 to be less restrictive
        searchLimit,
        filterCatalogType !== 'all' ? filterCatalogType : undefined,
        filterCatalogSubtype !== 'all' ? filterCatalogSubtype : undefined,
        catalogName
      )

      console.log('Semantic search results:', searchResults)

      if (searchResults && searchResults.length > 0) {
        // Good semantic matches found
        if (loadMore) {
          // Append to existing results, avoiding duplicates
          setCacheEntries(prev => {
            const existingIds = new Set(prev.map(item => item.id))
            const newResults = searchResults.filter(item => !existingIds.has(item.id))
            return [...prev, ...newResults]
          })
          setFilteredEntries(prev => {
            const existingIds = new Set(prev.map(item => item.id))
            const newResults = searchResults.filter(item => !existingIds.has(item.id))
            return [...prev, ...newResults]
          })
        } else {
          // Replace all results
          setCacheEntries(searchResults)
          setFilteredEntries(searchResults)
        }
        
        setSearchStatus('semantic')
        setSearchMethod('semantic')
        setSearchResultsCount(searchResults.length)
        setSemanticSearchLimit(searchLimit)
        setHasMoreSemanticResults(searchResults.length === searchLimit)
        console.log(`Found ${searchResults.length} semantic matches for: "${query}"`)
      } else {
        // No semantic matches, try LLM completion for suggestions
        console.log('No semantic matches found, trying LLM completion...')
        setSearchStatus('llm')
        
        try {
          const completion = await api.complete({
            prompt: `Suggest cache entries for workflow step: "${query}". Consider workflow context: type=${filterCatalogType}, mode=${filterCatalogSubtype}`,
            use_llm: true,
            catalog_type: filterCatalogType !== 'all' ? filterCatalogType : undefined,
            catalog_subtype: filterCatalogSubtype !== 'all' ? filterCatalogSubtype : undefined,
            similarity_threshold: 0.5, // Lowered from 0.6 for more suggestions
            limit: 10 // Increased from 5
          })

          console.log('LLM completion result:', completion)

          if (completion.cache_hit && completion.considered_entries && completion.considered_entries.length > 0) {
            // LLM found some suggestions, fetch those entries
            const suggestedEntries = await api.getBulkCacheEntries(completion.considered_entries)
            console.log('LLM suggested entries:', suggestedEntries)
            
            setCacheEntries(suggestedEntries)
            setFilteredEntries(suggestedEntries)
            setSearchStatus('llm')
            setSearchMethod('llm')
            setSearchResultsCount(suggestedEntries.length)
            setHasMoreSemanticResults(false) // LLM suggestions are limited
            console.log(`LLM suggested ${suggestedEntries.length} alternative entries`)
          } else {
            // No LLM suggestions either, show empty state with helpful message
            setCacheEntries([])
            setFilteredEntries([])
            setSearchStatus('idle')
            setSearchMethod('none')
            setSearchResultsCount(0)
            setHasMoreSemanticResults(false)
            console.log('No LLM suggestions found')
          }
        } catch (llmError) {
          console.warn('LLM completion failed, showing empty results:', llmError)
          setCacheEntries([])
          setFilteredEntries([])
          setSearchStatus('idle')
          setSearchMethod('none')
          setSearchResultsCount(0)
          setHasMoreSemanticResults(false)
        }
      }
    } catch (error) {
      console.error('Enhanced search failed:', error)
      setSearchStatus('fallback')
      // Fallback to basic search
      try {
        console.log('Trying fallback search...')
        const fallbackResults = await api.getCacheEntries(1, 50) // Increased from 20
        
        // Apply current filters to fallback results
        let basicFiltered = fallbackResults.items.filter(entry => {
          const matchesQuery = entry.nl_query.toLowerCase().includes(query.toLowerCase()) ||
                              entry.template_type.toLowerCase().includes(query.toLowerCase())
          
          const matchesCatalogType = filterCatalogType === 'all' || entry.catalog_type === filterCatalogType
          const matchesCatalogSubtype = filterCatalogSubtype === 'all' || entry.catalog_subtype === filterCatalogSubtype
          const matchesTemplateType = filterTemplateType === 'all' || entry.template_type === filterTemplateType
          
          return matchesQuery && matchesCatalogType && matchesCatalogSubtype && matchesTemplateType
        })
        
        console.log('Fallback search results:', basicFiltered)
        
        setCacheEntries(basicFiltered)
        setFilteredEntries(basicFiltered)
        setSearchMethod('fallback')
        setSearchResultsCount(basicFiltered.length)
        setHasMoreSemanticResults(false)
      } catch (fallbackError) {
        console.error('Fallback search also failed:', fallbackError)
        setCacheEntries([])
        setFilteredEntries([])
        setSearchMethod('none')
        setSearchResultsCount(0)
        setHasMoreSemanticResults(false)
      }
    } finally {
      setLoading(false)
    }
  }

  // Load more semantic search results
  const loadMoreSemanticResults = async () => {
    if (searchQuery.trim() && hasMoreSemanticResults) {
      await performEnhancedSearch(searchQuery, true)
    }
  }

  // Debounced search and filter application
  useEffect(() => {
    if (!searchQuery.trim()) {
      // If search is empty, check if we need to apply server-side filters
      const hasActiveFilters = filterCatalogType !== 'all' || 
                              filterCatalogSubtype !== 'all' || 
                              filterTemplateType !== 'all'
      
      if (hasActiveFilters) {
        // Make server-side filtered request
        performFilteredRequest()
      } else {
        // No filters active, use existing entries or fetch default
        if (cacheEntries.length === 0) {
          fetchPaginatedEntries(1, 'all', 'all', 'all')
        } else {
          setFilteredEntries(cacheEntries)
          setSearchStatus('idle')
          setSearchMethod('none')
          setSearchResultsCount(cacheEntries.length)
          setHasMoreSemanticResults(false)
          setSemanticSearchLimit(20)
        }
      }
      return
    }

    const timeoutId = setTimeout(() => {
      console.log('Triggering search for:', searchQuery)
      performEnhancedSearch(searchQuery)
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [searchQuery, filterCatalogType, filterCatalogSubtype, filterTemplateType])

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

  // Handle node clicks to show details or open editors
  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    // Only handle clicks on workflow nodes (not start node)
    if (node.id !== 'start') {
      setSelectedNode(node)
      
      // Check if this is specifically an LLM step that needs the special editor
      if (node.data?.templateType === 'llm_step') {
        setIsLLMEditorOpen(true)
      } else if (node.data?.cacheEntryId || node.data?.isBuiltIn) {
        // For all other nodes (cache entries, other built-in steps), use the regular detail modal
        setIsNodeDetailOpen(true)
      }
    }
  }, [])

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
      const centerX = -viewport.x + (window.innerWidth - (sidebarCollapsed ? 0 : 384)) / 2 / viewport.zoom
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
      className: 'clickable-workflow-node',
      data: {
        label: `${getTemplateIcon(entry.template_type)} ${entry.nl_query}`,
        cacheEntryId: entry.id,
        templateType: entry.template_type,
        template: entry.template,
        // Enhanced metadata for better DSL generation
        catalogType: entry.catalog_type,
        catalogSubtype: entry.catalog_subtype,
        catalogName: entry.catalog_name,
        reasoningTrace: entry.reasoning_trace,
        entityReplacements: entry.entity_replacements,
        tags: entry.tags,
        status: entry.status,
        // For DSL compilation
        originalQuery: entry.nl_query,
        isTemplate: entry.is_template,
        usageCount: entry.usage_count || 0
      },
      style: {
        background: getTemplateColor(entry.template_type),
        color: 'white',
        border: '2px solid #374151',
        borderRadius: '8px',
        fontSize: '12px',
        fontWeight: 'bold',
        width: 220, // Slightly wider to accommodate more info
        textAlign: 'center',
        padding: '8px',
        minHeight: '60px',
        // Visual indicator for clickable nodes
        cursor: 'pointer',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
        // Safe transitions that don't conflict with React Flow's transform updates
        transition: 'background-color 150ms ease, box-shadow 150ms ease, border-color 150ms ease, color 150ms ease',
        // Hint to browser for smoother panning/dragging without animating
        willChange: 'transform',
      },
      selected: true, // Auto-select the new node for visual feedback
    }
    
    setNodes((nds) => [...nds.map(n => ({ ...n, selected: false })), newNode])
    
    // Track the added node for layout effect handling
    lastAddedNodeRef.current = {
      position: position,
      timestamp: Date.now()
    }
  }

  // Handle adding a built-in step as a node
  const addBuiltInStepAsNode = (stepType: any, position?: { x: number; y: number }) => {
    let nodePosition = position

    // If no position specified, place node in the center of the visible viewport
    if (!nodePosition) {
      const viewport = getViewport()
      const centerX = -viewport.x + (window.innerWidth - (sidebarCollapsed ? 0 : 384)) / 2 / viewport.zoom
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
      className: 'clickable-workflow-node',
      data: {
        label: `${getTemplateIcon(stepType.type)} ${stepType.name}`,
        builtInStepId: stepType.id,
        templateType: stepType.type,
        template: JSON.stringify(stepType.template),
        // Enhanced metadata for better DSL generation
        catalogType: 'builtin',
        catalogSubtype: stepType.category.toLowerCase().replace(/ & /g, '_').replace(/ /g, '_'),
        catalogName: stepType.name,
        reasoningTrace: stepType.description,
        entityReplacements: {},
        tags: { builtin: [stepType.type], category: [stepType.category] },
        status: 'active',
        // For DSL compilation
        originalQuery: stepType.description,
        isTemplate: true,
        usageCount: 0,
        isBuiltIn: true
      },
      style: {
        background: getTemplateColor(stepType.type),
        color: 'white',
        border: '2px solid #374151',
        borderRadius: '8px',
        fontSize: '12px',
        fontWeight: 'bold',
        width: 220,
        textAlign: 'center',
        padding: '8px',
        minHeight: '60px',
        cursor: 'pointer',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
        // Safe transitions that don't conflict with React Flow's transform updates
        transition: 'background-color 150ms ease, box-shadow 150ms ease, border-color 150ms ease, color 150ms ease',
        // Hint to browser for smoother panning/dragging without animating
        willChange: 'transform',
      },
      selected: false,
    }
    
    setNodes((nds) => [...nds.map(n => ({ ...n, selected: false })), newNode])
    
    // Track the added node for layout effect handling
    lastAddedNodeRef.current = {
      position: position,
      timestamp: Date.now()
    }
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

      // Check for cache entry
      const entryId = event.dataTransfer.getData('application/cache-entry')
      if (entryId) {
        const entry = cacheEntries.find(e => e.id.toString() === entryId)
        if (entry) {
          addCacheEntryAsNode(entry, clampedPosition)
          return
        }
      }

      // Check for built-in step type
      const builtInStepId = event.dataTransfer.getData('application/builtin-step')
      if (builtInStepId) {
        const stepType = builtInStepTypes.find(s => s.id === builtInStepId)
        if (stepType) {
          addBuiltInStepAsNode(stepType, clampedPosition)
          return
        }
      }
    },
    [screenToFlowPosition, cacheEntries, addCacheEntryAsNode, addBuiltInStepAsNode]
  )

  // Handle drag start for cache entries
  const onDragStart = (event: React.DragEvent, entry: CacheItem) => {
    event.dataTransfer.setData('application/cache-entry', entry.id.toString())
    event.dataTransfer.effectAllowed = 'move'
  }

  // Handle drag start for built-in steps
  const onBuiltInStepDragStart = (event: React.DragEvent, stepType: any) => {
    event.dataTransfer.setData('application/builtin-step', stepType.id)
    event.dataTransfer.effectAllowed = 'move'
  }

  // Handle saving updated node from LLM editor
  const handleLLMStepSave = useCallback((updatedNode: Node) => {
    setNodes((nds) => nds.map(node => 
      node.id === updatedNode.id ? updatedNode : node
    ))
  }, [setNodes])

  // Get available inputs for LLM step (previous step outputs)
  const getAvailableInputs = useCallback((currentNodeId: string) => {
    // Find all nodes that come before this one in the workflow
    const currentNode = nodes.find(n => n.id === currentNodeId)
    if (!currentNode) return []

    // For now, we'll consider all nodes except the current one and start node as potential inputs
    // In a more sophisticated implementation, you'd analyze the actual flow/connections
    return nodes
      .filter(node => node.id !== currentNodeId && node.id !== 'start')
      .map(node => ({
        stepId: node.id,
        stepName: node.data.label || `Step ${node.id}`,
        outputSchema: {
          // Default output schema - in a real implementation, this would be 
          // determined by the step type and configuration
          output: 'any',
          metadata: {
            stepType: node.data.templateType,
            timestamp: 'string'
          }
        }
      }))
  }, [nodes])

  // Delete selected nodes (but never delete start node)
  const deleteSelected = () => {
    const selectedNodeIds = nodes.filter(node => node.selected && node.id !== 'start').map(node => node.id)
    const selectedEdgeIds = edges.filter(edge => edge.selected).map(edge => edge.id)

    const remainingNodes = nodes.filter(node => !selectedNodeIds.includes(node.id))
    
    // Ensure start node always exists after deletion
    const hasStartNode = remainingNodes.some(n => n.id === 'start')
    if (!hasStartNode) {
      remainingNodes.unshift(defaultNodes[0]) // Add start node at beginning
      console.log('Re-added start node after deletion')
    }
    
    setNodes(remainingNodes)
    setEdges(eds => eds.filter(edge => 
      !selectedEdgeIds.includes(edge.id) && 
      !selectedNodeIds.includes(edge.source) && 
      !selectedNodeIds.includes(edge.target)
    ))
  }

  // Clear entire workflow
  const clearWorkflow = () => {
    if (confirm('Are you sure you want to clear the entire workflow? This will remove all nodes and connections.')) {
      setNodes(defaultNodes) // Use the defaultNodes to ensure consistent start node
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
    <div className={`flex bg-background text-foreground relative transition-all duration-300 ${
      (isMaximized && !onMaximizeChange)
        ? 'fixed inset-0 z-50 h-screen w-screen' 
        : 'h-full w-full'
    }`}>
      {/* Left Sidebar - Workflow Steps */}
      <div className={`${sidebarCollapsed ? 'w-0' : 'w-96'} bg-card border-r border-border flex flex-col transition-all duration-300 overflow-hidden`}>
        {!sidebarCollapsed && (
          <>
            <div className="p-4 border-b border-border">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold">Workflow Steps</h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowFilters(prev => !prev)}
                    className={`p-1 hover:bg-accent rounded transition-colors ${
                      showFilters ? 'text-green-400' : 'text-muted-foreground'
                    }`}
                    title="Toggle filters (Ctrl+F)"
                  >
                    <Filter className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setIsMaximized(prev => !prev)}
                    className="p-1 hover:bg-accent rounded transition-colors"
                    title={`${isMaximized ? 'Minimize' : 'Maximize'} (F11 or Ctrl+M)`}
                  >
                    {isMaximized ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={() => setSidebarCollapsed(true)}
                    className="p-1 hover:bg-accent rounded transition-colors"
                    title="Collapse sidebar (Ctrl+B)"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Tab Navigation */}
              <div className="flex mb-3 bg-input/50 rounded-lg p-1">
                <button
                  onClick={() => setActiveTab('builtin')}
                  className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors flex items-center justify-center gap-2 ${
                    activeTab === 'builtin'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  <Zap className="h-4 w-4" />
                  Built-in Steps
                </button>
                <button
                  onClick={() => setActiveTab('cache')}
                  className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors flex items-center justify-center gap-2 ${
                    activeTab === 'cache'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  <Database className="h-4 w-4" />
                  Cache Entries
                </button>
              </div>

              {/* Search and Filters - Only show for Cache Entries tab */}
              {activeTab === 'cache' && (
                <>
                  {/* Compact Search Info */}
              <div className="mb-3 p-2 bg-input/30 rounded-md border border-border/30">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-medium">Smart Search:</span>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1">
                      <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                      <span>Semantic</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full"></div>
                      <span>LLM</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-1.5 h-1.5 bg-orange-400 rounded-full"></div>
                      <span>Fallback</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Search Bar */}
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder={`Search ${filterTemplateType !== 'all' ? filterTemplateType + ' ' : ''}entries... (try "fetch user data" or "send email")`}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-20 py-2 bg-input border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  minLength={2}
                />
                {searchQuery.trim() && (
                  <button
                    onClick={() => {
                      setSearchQuery('')
                      setSearchStatus('idle')
                      setSearchMethod('none')
                      setSearchResultsCount(0)
                      setHasMoreSemanticResults(false)
                      setSemanticSearchLimit(20)
                      // Reset to paginated view with current filters
                      fetchPaginatedEntries(1, filterTemplateType, filterCatalogType, filterCatalogSubtype)
                    }}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition-colors"
                    title="Clear search and return to paginated view"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

              {/* Search Status Indicator */}
              {searchQuery.trim() && (
                <div className="mb-3 p-2 bg-input rounded-md border border-border">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {searchStatus === 'searching' && (
                        <div className="flex items-center gap-1 text-yellow-400">
                          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
                          Searching...
                        </div>
                      )}
                      {searchStatus === 'semantic' && (
                        <div className="flex items-center gap-1 text-green-400">
                          <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                          Semantic Search
                        </div>
                      )}
                      {searchStatus === 'llm' && (
                        <div className="flex items-center gap-1 text-blue-400">
                          <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                          LLM Enhanced
                        </div>
                      )}
                      {searchStatus === 'fallback' && (
                        <div className="flex items-center gap-1 text-orange-400">
                          <div className="w-2 h-2 bg-orange-400 rounded-full"></div>
                          Fallback Search
                        </div>
                      )}
                    </div>
                    {searchResultsCount > 0 && (
                      <span className="text-muted-foreground">
                        {searchResultsCount} result{searchResultsCount !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  {searchMethod !== 'none' && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {searchMethod === 'semantic' && 'Using vector similarity search (60% threshold)'}
                      {searchMethod === 'llm' && 'Using LLM-enhanced suggestions'}
                      {searchMethod === 'fallback' && 'Using basic text matching with filters'}
                    </div>
                  )}
                  {searchQuery.trim().length < 2 && (
                    <div className="mt-1 text-xs text-yellow-400">
                      Type at least 2 characters to search
                    </div>
                  )}
                </div>
              )}

              {/* Advanced Filters */}
              {showFilters && (
                <div className="space-y-3 p-3 bg-input/50 rounded-lg border border-border">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">Advanced Filters</span>
                    <button
                      onClick={async () => {
                        setFilterCatalogType('all')
                        setFilterCatalogSubtype('all')
                        setFilterTemplateType('all')
                        // Refresh catalog values after clearing filters
                        await refreshCatalogValues()
                      }}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      Clear All
                    </button>
                  </div>

                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Catalog Type</label>
                    <select
                      value={filterCatalogType}
                      onChange={async (e) => {
                        const newValue = e.target.value
                        console.log('Catalog type changing from', filterCatalogType, 'to', newValue)
                        
                        // Always reset subtype when catalog type changes
                        setFilterCatalogSubtype('all')
                        setFilterCatalogType(newValue)
                        
                        // Refresh catalog values for hierarchical filtering
                        console.log('Refreshing catalog values after catalog type change')
                        // Use setTimeout to ensure state updates are processed
                        setTimeout(async () => {
                          await refreshCatalogValues()
                        }, 100)
                      }}
                      className="w-full px-2 py-1 bg-muted border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-green-500"
                    >
                      <option value="all">All Types</option>
                      {availableCatalogTypes.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Catalog Subtype</label>
                    <select
                      value={filterCatalogSubtype}
                      onChange={async (e) => {
                        const newValue = e.target.value
                        console.log('Catalog subtype changing from', filterCatalogSubtype, 'to', newValue)
                        setFilterCatalogSubtype(newValue)
                        // Note: We don't need to refresh catalog values when subtype changes
                        // as subtypes are already filtered by the current catalog type
                      }}
                      className="w-full px-2 py-1 bg-muted border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-green-500"
                    >
                      <option value="all">All Subtypes</option>
                      {availableCatalogSubtypes.map(subtype => (
                        <option key={subtype} value={subtype}>{subtype}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Template Type</label>
                    <select
                      value={filterTemplateType}
                      onChange={(e) => setFilterTemplateType(e.target.value)}
                      className="w-full px-2 py-1 bg-muted border border-border rounded text-xs focus:outline-none focus:ring-1 focus:ring-green-500"
                    >
                      <option value="all">All Templates</option>
                      {Object.entries(templateTypeCategories).map(([category, types]) => {
                        const availableInCategory = types.filter(type => availableTemplateTypes.includes(type))
                        if (availableInCategory.length === 0) return null
                        
                        return (
                          <optgroup key={category} label={category}>
                            {availableInCategory.map(type => (
                              <option key={type} value={type}>
                                {getTemplateIcon(type)} {type.charAt(0).toUpperCase() + type.slice(1)}
                              </option>
                            ))}
                          </optgroup>
                        )
                      })}
                      {/* Show uncategorized types */}
                      {availableTemplateTypes.filter(type => 
                        !Object.values(templateTypeCategories).flat().includes(type)
                      ).map(type => (
                        <option key={type} value={type}>
                          {getTemplateIcon(type)} {type.charAt(0).toUpperCase() + type.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="text-xs text-muted-foreground pt-2 border-t border-border">
                    {searchMethod === 'semantic' && (
                      <div className="space-y-1">
                        <div>Showing {filteredEntries.length} semantic search results</div>
                        {hasMoreSemanticResults && (
                          <div className="text-blue-400">More results available - use "Load More" below</div>
                        )}
                      </div>
                    )}
                    {searchMethod === 'none' && (
                      <div className="space-y-1">
                        <div>Showing {filteredEntries.length} of {totalEntries} total entries</div>
                        {(filterCatalogType !== 'all' || filterCatalogSubtype !== 'all' || filterTemplateType !== 'all') && (
                          <div className="text-blue-400 text-xs">
                            Server-side filtered: 
                            {filterTemplateType !== 'all' && `${filterTemplateType} `}
                            {filterCatalogType !== 'all' && `${filterCatalogType} `}
                            {filterCatalogSubtype !== 'all' && `${filterCatalogSubtype}`}
                          </div>
                        )}
                        {hasMorePages && (
                          <div className="text-green-400">More pages available - use "Load More" below</div>
                        )}
                      </div>
                    )}
                    {(searchMethod === 'llm' || searchMethod === 'fallback') && (
                      <div>Showing {filteredEntries.length} {searchMethod === 'llm' ? 'LLM-suggested' : 'fallback'} results</div>
                    )}
                  </div>
                </div>
              )}
                </>
              )}
            </div>

            {/* Tab Content */}
            {activeTab === 'builtin' ? (
              /* Built-in Steps Tab */
              <div className="flex-1 overflow-y-auto p-4">
                <div className="space-y-3">
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                      <Zap className="h-4 w-4 text-purple-400" />
                      Built-in Step Types
                    </h4>
                    <p className="text-xs text-muted-foreground mb-3">
                      Pre-configured workflow steps you can drag and drop or double-click to add
                    </p>
                  </div>
                  <div className="grid grid-cols-1 gap-3">
                    {builtInStepTypes.map((stepType) => (
                      <div
                        key={stepType.id}
                        draggable
                        onDragStart={(e) => onBuiltInStepDragStart(e, stepType)}
                        onDoubleClick={() => addBuiltInStepAsNode(stepType)}
                        className="p-3 bg-input border border-border rounded-lg cursor-grab hover:bg-accent hover:border-border active:cursor-grabbing transition-all group"
                        title={`${stepType.description} - Drag to canvas or double-click to add`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg">{getTemplateIcon(stepType.type)}</span>
                          <span className="text-xs px-2 py-1 rounded-full text-foreground font-medium" style={{ 
                            backgroundColor: getTemplateColor(stepType.type)
                          }}>
                            {stepType.type}
                          </span>
                        </div>
                        <div className="text-sm font-semibold text-foreground mb-1">
                          {stepType.name}
                        </div>
                        <div className="text-xs text-muted-foreground leading-relaxed">
                          {stepType.description}
                        </div>
                        <div className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                          <span className="px-1.5 py-0.5 bg-muted rounded text-foreground">
                            {stepType.category}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              /* Cache Entries Tab */
              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                <div className="mb-3">
                  <h4 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                    <Database className="h-4 w-4 text-blue-400" />
                    Cache Entries
                    {searchResultsCount > 0 && (
                      <span className="text-xs text-muted-foreground">({searchResultsCount})</span>
                    )}
                  </h4>
                </div>
              {loading ? (
                <div className="text-center text-muted-foreground py-8">Loading cache entries...</div>
              ) : filteredEntries.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  {searchQuery ? (
                    <div className="space-y-3">
                      <div className="text-lg font-medium">No entries match your search</div>
                      <div className="text-sm space-y-2">
                        {searchMethod === 'semantic' && (
                          <div className="text-yellow-400">
                            Semantic search found no similar entries above 60% similarity threshold.
                          </div>
                        )}
                        {searchMethod === 'llm' && (
                          <div className="text-blue-400">
                            LLM couldn't find suitable alternatives for this step.
                          </div>
                        )}
                        {searchMethod === 'fallback' && (
                          <div className="text-orange-400">
                            Basic text matching with current filters found no results.
                          </div>
                        )}
                        <div className="text-muted-foreground pt-2">
                          Try:
                          <ul className="list-disc list-inside mt-1 space-y-1">
                            <li>Using different keywords or synonyms</li>
                            <li>Broadening your search terms</li>
                            <li>Checking if the step exists in a different catalog</li>
                            <li>Adjusting the catalog type/subtype filters</li>
                            <li>Creating a new cache entry for this step</li>
                          </ul>
                        </div>
                        <div className="pt-2">
                          <button
                            onClick={() => {
                              setSearchQuery('')
                              setSearchStatus('idle')
                              setSearchMethod('none')
                              setSearchResultsCount(0)
                              setHasMoreSemanticResults(false)
                              setSemanticSearchLimit(20)
                              fetchPaginatedEntries(1, filterTemplateType, filterCatalogType, filterCatalogSubtype)
                            }}
                            className="text-blue-400 hover:text-blue-300 underline"
                          >
                            Clear search and browse all entries
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    'No cache entries found'
                  )}
                </div>
              ) : (
                filteredEntries.map((entry) => (
                  <div
                    key={entry.id}
                    draggable
                    onDragStart={(e) => onDragStart(e, entry)}
                    onDoubleClick={() => addCacheEntryAsNode(entry)}
                    className="p-2 bg-input border border-border rounded-md cursor-grab hover:bg-accent active:cursor-grabbing transition-colors group"
                    onClick={() => setSelectedEntry(entry)}
                    title="Drag to canvas or double-click to add at center"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm">{getTemplateIcon(entry.template_type)}</span>
                      <span className="text-xs px-1 py-0.5 rounded text-foreground" style={{ 
                        backgroundColor: getTemplateColor(entry.template_type)
                      }}>
                        {entry.template_type}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-foreground mb-1 line-clamp-2 leading-tight">
                      {entry.nl_query}
                    </div>
                    {entry.catalog_type && (
                      <div className="text-xs text-muted-foreground mb-1">
                        {entry.catalog_type}{entry.catalog_subtype ? ` • ${entry.catalog_subtype}` : ''}
                      </div>
                    )}
                    {entry.usage_count !== undefined && entry.usage_count > 0 && (
                      <div className="text-xs text-green-400">
                        Used {entry.usage_count}x
                      </div>
                    )}
                  </div>
                ))
              )}

              {/* Pagination and Load More Controls */}
              {!loading && filteredEntries.length > 0 && (
              <div className="p-4 border-t border-border bg-input/50">
                {/* Search Method Specific Controls */}
                {searchMethod === 'semantic' && (
                  <div className="space-y-3">
                    <div className="text-center text-sm text-muted-foreground">
                      Showing {filteredEntries.length} semantic search results
                    </div>
                    {hasMoreSemanticResults && (
                      <button
                        onClick={loadMoreSemanticResults}
                        disabled={isLoadingMore}
                        className="w-full py-2 px-4 bg-primary hover:bg-primary/90 disabled:bg-primary/50 text-primary-foreground text-sm rounded-md transition-colors flex items-center justify-center gap-2"
                      >
                        {isLoadingMore ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            Loading More...
                          </>
                        ) : (
                          <>
                            <Plus className="h-4 w-4" />
                            Load More Semantic Results
                          </>
                        )}
                      </button>
                    )}
                  </div>
                )}

                {searchMethod === 'none' && (
                  <div className="space-y-3">
                    <div className="text-center text-sm text-muted-foreground">
                      Showing {filteredEntries.length} of {totalEntries} total entries
                    </div>
                    {hasMorePages && (
                      <button
                        onClick={loadMoreEntries}
                        disabled={isLoadingMore}
                        className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-foreground text-sm rounded-md transition-colors flex items-center justify-center gap-2"
                      >
                        {isLoadingMore ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            Loading Page {currentPage + 1}...
                          </>
                        ) : (
                          <>
                            <Plus className="h-4 w-4" />
                            Load More Entries (Page {currentPage + 1})
                          </>
                        )}
                      </button>
                    )}
                    {!hasMorePages && totalEntries > 0 && (
                      <div className="text-center text-xs text-muted-foreground">
                        All {totalEntries} entries loaded
                      </div>
                    )}
                  </div>
                )}

                {/* Other search methods don't need pagination */}
                {(searchMethod === 'llm' || searchMethod === 'fallback') && (
                  <div className="text-center text-sm text-muted-foreground">
                    Showing {filteredEntries.length} {searchMethod === 'llm' ? 'LLM-suggested' : 'fallback'} results
                  </div>
                )}
              </div>
            )}
              </div>
            )}


          </>
        )}
      </div>

      {/* Collapse/Expand Button */}
      {sidebarCollapsed && (
        <div className="absolute left-0 top-4 z-10">
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="p-3 bg-input border border-border rounded-r-lg hover:bg-muted transition-colors shadow-lg"
            title="Expand sidebar (Ctrl+B)"
          >
            <div className="flex flex-col items-center gap-1">
              <Menu className="h-4 w-4" />
              <span className="text-xs">Steps</span>
            </div>
          </button>
        </div>
      )}

      {/* Maximize/Minimize Button for collapsed sidebar */}
      {sidebarCollapsed && (
        <div className="absolute left-0 top-20 z-10">
          <button
            onClick={() => setIsMaximized(prev => !prev)}
            className="p-3 bg-input border border-border rounded-r-lg hover:bg-muted transition-colors shadow-lg"
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
      <div className="flex-1 flex flex-col bg-neutral-950">
        <div className="flex-1 w-full h-full" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={handleNodeClick}
            onDrop={onDrop}
            onDragOver={onDragOver}
            className="bg-background w-full h-full"
          >
            <Controls className="bg-input border-border text-foreground" />
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} className="bg-background" />
            
            <Panel position="top-left">
              <div className="flex items-center gap-2 bg-input/90 px-3 py-2 rounded-md text-xs">
                <Save className="h-3 w-3 text-green-400" />
                <span className="text-foreground">Auto-saved • {nodes.length - 1} nodes • {edges.length} connections</span>
              </div>
            </Panel>

            <Panel position="top-right">
              <div className="flex gap-2">
                <button
                  onClick={() => setSidebarCollapsed(prev => !prev)}
                  className="px-3 py-2 bg-muted text-foreground rounded-md hover:bg-neutral-600 flex items-center gap-1 text-sm"
                  title={`${sidebarCollapsed ? 'Show' : 'Hide'} steps sidebar (Ctrl+B)`}
                >
                  {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                  {sidebarCollapsed ? 'Show' : 'Hide'} Steps
                </button>
                <button
                  onClick={() => fitView({ padding: 0.1, duration: 800 })}
                  className="px-3 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center gap-1 text-sm"
                  title="Fit all nodes in view"
                >
                  <Focus className="h-4 w-4" />
                  Fit View
                </button>
                <button
                  onClick={clearWorkflow}
                  className="px-3 py-2 bg-yellow-600 text-foreground rounded-md hover:bg-yellow-700 flex items-center gap-1 text-sm"
                  title="Clear entire workflow"
                >
                  <RotateCcw className="h-4 w-4" />
                  Clear
                </button>
                <button
                  onClick={deleteSelected}
                  disabled={!nodes.some(n => n.selected && n.id !== 'start') && !edges.some(e => e.selected)}
                  className="px-3 py-2 bg-red-600 text-foreground rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 text-sm"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </button>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>

      {/* Node Detail Modal */}
      <NodeDetailModal
        isOpen={isNodeDetailOpen}
        onClose={() => setIsNodeDetailOpen(false)}
        node={selectedNode}
      />

      {/* LLM Step Editor Modal */}
      <LLMStepEditor
        isOpen={isLLMEditorOpen}
        onClose={() => setIsLLMEditorOpen(false)}
        node={selectedNode}
        onSave={handleLLMStepSave}
        availableInputs={selectedNode ? getAvailableInputs(selectedNode.id) : []}
      />
    </div>
  )
}

const InteractiveWorkflowBuilder: React.FC<InteractiveWorkflowBuilderProps> = (props) => {
  const key = props.workflowId 
    ? `flow-${props.workflowId}`
    : `flow-${props.catalogType}-${props.catalogSubtype}`

  return (
    <ReactFlowProvider key={key}>
      <WorkflowBuilderComponent {...props} />
    </ReactFlowProvider>
  )
}

export default InteractiveWorkflowBuilder