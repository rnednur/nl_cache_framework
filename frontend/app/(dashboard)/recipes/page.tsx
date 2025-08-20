'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'react-hot-toast'
import {
  Search,
  Plus,
  Play,
  Clock,
  Users,
  Filter,
  Loader2,
  TrendingUp,
  CheckCircle,
  Download,
  Trash2,
  Copy,
  MoreVertical,
  Calendar,
  Target,
  Activity,
  Zap,
  Workflow,
  Settings,
  Eye,
  AlertCircle,
  GitBranch,
  ChefHat
} from 'lucide-react'
import api, { type CacheItem } from '@/app/services/api'
import { PageHeader } from '@/app/components/ui/PageHeader'

interface Recipe extends CacheItem {
  recipe_steps?: Array<{
    id: string
    name: string
    type: string 
    tool_id?: number
    depends_on?: string[]
  }>
  required_tools?: number[]
  complexity_level?: string
  success_rate?: number
  last_executed?: string
  execution_count?: number
}

const WORKFLOW_TYPES = [
  { 
    value: 'fullflow', 
    label: 'Full Workflows', 
    icon: '🔄', 
    color: 'bg-green-500',
    description: 'Complete end-to-end workflows'
  },
  { 
    value: 'subflow', 
    label: 'Sub Workflows', 
    icon: '⚡', 
    color: 'bg-blue-500',
    description: 'Reusable workflow components'
  },
  { 
    value: 'workflow', 
    label: 'All Workflows', 
    icon: '🔗', 
    color: 'bg-purple-500',
    description: 'All workflow types'
  }
] as const

const COMPLEXITY_COLORS = {
  easy: 'bg-green-500',
  medium: 'bg-yellow-500', 
  hard: 'bg-red-500',
  // Legacy support
  beginner: 'bg-green-500',
  intermediate: 'bg-yellow-500', 
  advanced: 'bg-red-500',
} as const

export default function WorkflowHub() {
  const router = useRouter()
  const [workflows, setWorkflows] = useState<Recipe[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [selectedComplexity, setSelectedComplexity] = useState<string>('all')
  const [filteredWorkflows, setFilteredWorkflows] = useState<Recipe[]>([])
  const [selectedWorkflows, setSelectedWorkflows] = useState<Set<number>>(new Set())
  const [showBulkActions, setShowBulkActions] = useState(false)
  const [sortBy, setSortBy] = useState<'name' | 'last_executed' | 'success_rate' | 'execution_count'>('last_executed')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    fetchWorkflows()
  }, [])

  useEffect(() => {
    filterWorkflows()
  }, [workflows, searchQuery, selectedType, selectedComplexity, sortBy, sortOrder])

  useEffect(() => {
    setShowBulkActions(selectedWorkflows.size > 0)
  }, [selectedWorkflows])

  const fetchWorkflows = async () => {
    setLoading(true)
    setError(null)
    try {
      // Filter for workflow template type only (fullflow/subflow are catalog_type values)
      const response = await api.getCacheEntries(1, 100, 'workflow')
      setWorkflows(response.items)
    } catch (err: any) {
      // If backend is not available, use mock data for demonstration
      console.warn('Backend not available, using mock data:', err.message)
      
      // Mock workflow data for demonstration
      const mockWorkflows = [
        {
          id: 1,
          nl_query: "Post-Incident Review Automation",
          template_type: "workflow",
          template: JSON.stringify({
            steps: [
              { id: "s1", type: "jira", name: "Fetch Jira Issues" },
              { id: "s2", type: "llm", name: "Summarize with Claude" },
              { id: "s3", type: "confluence", name: "Update Confluence" }
            ],
            edges: [
              { from: "s1", to: "s2" },
              { from: "s2", to: "s3" }
            ]
          }),
          reasoning_trace: "Automated workflow for post-incident reviews",
          is_template: false,
          entity_replacements: {},
          tags: { flow_type: ["fullflow"], execution_mode: ["interactive"] },
          catalog_type: "fullflow",
          catalog_subtype: "interactive",
          catalog_name: "post-incident-review",
          status: "active",
          created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
          updated_at: new Date(Date.now() - 86400000).toISOString(),
          recipe_steps: [
            { id: "s1", name: "Fetch Jira Issues", type: "data-fetch" },
            { id: "s2", name: "Summarize with Claude", type: "llm-processing" },
            { id: "s3", name: "Update Confluence", type: "data-output" }
          ],
          required_tools: [1, 2, 3],
          complexity_level: "medium",
          success_rate: 0.85,
          last_executed: new Date(Date.now() - 3600000 * 6).toISOString(),
          execution_count: 12
        },
        {
          id: 2,
          nl_query: "Daily Standup Report Generator",
          template_type: "workflow",
          template: JSON.stringify({
            steps: [
              { id: "s1", type: "slack", name: "Fetch Team Updates" },
              { id: "s2", type: "llm", name: "Generate Summary" }
            ],
            edges: [{ from: "s1", to: "s2" }]
          }),
          reasoning_trace: "Generate daily standup reports from team updates",
          is_template: false,
          entity_replacements: {},
          tags: { flow_type: ["subflow"], execution_mode: ["batch"] },
          catalog_type: "subflow",
          catalog_subtype: "batch",
          catalog_name: "daily-standup-report",
          status: "active",
          created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
          updated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
          recipe_steps: [
            { id: "s1", name: "Fetch Team Updates", type: "data-fetch" },
            { id: "s2", name: "Generate Summary", type: "llm-processing" }
          ],
          required_tools: [1, 4],
          complexity_level: "easy",
          success_rate: 0.92,
          last_executed: new Date(Date.now() - 3600000 * 2).toISOString(),
          execution_count: 35
        },
        {
          id: 3,
          nl_query: "Customer Feedback Analysis",
          template_type: "workflow",
          template: JSON.stringify({
            steps: [
              { id: "s1", type: "database", name: "Extract Feedback" },
              { id: "s2", type: "llm", name: "Sentiment Analysis" },
              { id: "s3", type: "visualization", name: "Create Dashboard" }
            ],
            edges: [
              { from: "s1", to: "s2" },
              { from: "s2", to: "s3" }
            ]
          }),
          reasoning_trace: "Analyze customer feedback and generate insights",
          is_template: false,
          entity_replacements: {},
          tags: { flow_type: ["workflow"], execution_mode: ["scheduled"] },
          catalog_type: "workflow",
          catalog_subtype: "scheduled",
          catalog_name: "customer-feedback-analysis",
          status: "active",
          created_at: new Date(Date.now() - 86400000 * 10).toISOString(),
          updated_at: new Date(Date.now() - 86400000 * 3).toISOString(),
          recipe_steps: [
            { id: "s1", name: "Extract Feedback", type: "data-extraction" },
            { id: "s2", name: "Sentiment Analysis", type: "llm-processing" },
            { id: "s3", name: "Create Dashboard", type: "visualization" }
          ],
          required_tools: [5, 2, 6],
          complexity_level: "hard",
          success_rate: 0.78,
          last_executed: new Date(Date.now() - 86400000).toISOString(),
          execution_count: 8
        }
      ]
      
      setWorkflows(mockWorkflows as Recipe[])
      toast.success('Using demo workflows (backend not connected)')
    } finally {
      setLoading(false)
    }
  }

  const filterWorkflows = () => {
    let filtered = [...workflows]

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(workflow => 
        workflow.nl_query.toLowerCase().includes(query) ||
        workflow.template_type.toLowerCase().includes(query) ||
        workflow.recipe_steps?.some(step => step.name.toLowerCase().includes(query)) ||
        workflow.tags && typeof workflow.tags === 'object' && Object.values(workflow.tags as any).some((tagValue: any) => {
          if (Array.isArray(tagValue)) {
            return tagValue.some((t: any) => typeof t === 'string' && t.toLowerCase().includes(query))
          }
          return typeof tagValue === 'string' && tagValue.toLowerCase().includes(query)
        })
      )
    }

    // Filter by catalog type (fullflow/subflow stored in catalog_type)
    if (selectedType !== 'all') {
      filtered = filtered.filter(workflow => workflow.catalog_type === selectedType)
    }

    // Filter by complexity level
    if (selectedComplexity !== 'all') {
      filtered = filtered.filter(workflow => workflow.complexity_level === selectedComplexity)
    }

    // Sort workflows
    filtered.sort((a, b) => {
      let aValue: any, bValue: any
      
      switch (sortBy) {
        case 'name':
          aValue = a.nl_query.toLowerCase()
          bValue = b.nl_query.toLowerCase()
          break
        case 'last_executed':
          aValue = a.last_executed ? new Date(a.last_executed).getTime() : 0
          bValue = b.last_executed ? new Date(b.last_executed).getTime() : 0
          break
        case 'success_rate':
          aValue = a.success_rate || 0
          bValue = b.success_rate || 0
          break
        case 'execution_count':
          aValue = a.execution_count || 0
          bValue = b.execution_count || 0
          break
        default:
          aValue = a.id
          bValue = b.id
      }
      
      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })

    setFilteredWorkflows(filtered)
  }

  const handleWorkflowExecute = async (workflowId: number) => {
    try {
      toast.loading('Initiating workflow execution...', { id: 'execute' })
      // This would call an execution endpoint when implemented
      await new Promise(resolve => setTimeout(resolve, 1000)) // Placeholder
      toast.success('Workflow execution initiated', { id: 'execute' })
      fetchWorkflows() // Refresh to get updated execution stats
    } catch (err: any) {
      toast.error('Workflow execution failed', { id: 'execute' })
    }
  }

  const handleBulkAction = async (action: 'delete' | 'duplicate' | 'export') => {
    const selectedIds = Array.from(selectedWorkflows)
    
    try {
      switch (action) {
        case 'delete':
          toast.loading(`Deleting ${selectedIds.length} workflows...`, { id: 'bulk-action' })
          for (const id of selectedIds) {
            await api.deleteCacheEntry(id)
          }
          toast.success(`Deleted ${selectedIds.length} workflows`, { id: 'bulk-action' })
          setSelectedWorkflows(new Set())
          fetchWorkflows()
          break
          
        case 'duplicate':
          toast.loading(`Duplicating ${selectedIds.length} workflows...`, { id: 'bulk-action' })
          for (const id of selectedIds) {
            const workflow = workflows.find(w => w.id === id)
            if (workflow) {
              await api.createCacheEntry({
                nl_query: `${workflow.nl_query} (Copy)`,
                template: workflow.template,
                template_type: workflow.template_type,
                reasoning_trace: workflow.reasoning_trace,
                is_template: workflow.is_template,
                entity_replacements: workflow.entity_replacements,
                tags: workflow.tags,
                catalog_type: workflow.catalog_type,
                catalog_subtype: workflow.catalog_subtype,
                catalog_name: workflow.catalog_name,
                status: 'pending'
              })
            }
          }
          toast.success(`Duplicated ${selectedIds.length} workflows`, { id: 'bulk-action' })
          setSelectedWorkflows(new Set())
          fetchWorkflows()
          break
          
        case 'export':
          toast.loading('Exporting workflows...', { id: 'bulk-action' })
          const exportData = workflows.filter(w => selectedIds.includes(w.id))
          const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `workflows-export-${new Date().toISOString().split('T')[0]}.json`
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          URL.revokeObjectURL(url)
          toast.success(`Exported ${selectedIds.length} workflows`, { id: 'bulk-action' })
          break
      }
    } catch (err: any) {
      toast.error(`Bulk action failed: ${err.message}`, { id: 'bulk-action' })
    }
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedWorkflows(new Set(filteredWorkflows.map(w => w.id)))
    } else {
      setSelectedWorkflows(new Set())
    }
  }

  const handleSelectWorkflow = (workflowId: number, checked: boolean) => {
    const newSelected = new Set(selectedWorkflows)
    if (checked) {
      newSelected.add(workflowId)
    } else {
      newSelected.delete(workflowId)
    }
    setSelectedWorkflows(newSelected)
  }

  const getWorkflowIcon = (catalogType: string) => {
    const workflowType = WORKFLOW_TYPES.find(t => t.value === catalogType)
    if (workflowType) {
      return workflowType.icon
    }
    return '🔗'
  }

  const getWorkflowTypeColor = (catalogType: string) => {
    const workflowType = WORKFLOW_TYPES.find(t => t.value === catalogType)
    return workflowType?.color || 'bg-neutral-500'
  }

  const getComplexityColor = (complexity?: string) => {
    return COMPLEXITY_COLORS[complexity as keyof typeof COMPLEXITY_COLORS] || 'bg-neutral-500'
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
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`
    return `${Math.floor(days / 30)} months ago`
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-green-500" />
          <span className="text-muted-foreground">Loading workflows...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchWorkflows}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <div className="bg-card border-b-2 border-card-border px-6 py-6 shadow-sm">
        <PageHeader
          title="Recipes"
          description="Build, manage, and execute your automation workflows"
          icon={ChefHat}
          iconColor="text-green-600"
          actions={
            <div className="flex items-center gap-3">
              {showBulkActions && (
                <div className="flex gap-2 mr-4">
                  <button
                    onClick={() => handleBulkAction('duplicate')}
                    className="p-2 bg-input border border-border rounded-md text-foreground hover:bg-accent transition-colors"
                    title="Duplicate Selected"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleBulkAction('export')}
                    className="p-2 bg-input border border-border rounded-md text-foreground hover:bg-accent transition-colors"
                    title="Export Selected"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleBulkAction('delete')}
                    className="p-2 bg-red-600/20 border border-red-600/30 rounded-md text-red-400 hover:bg-red-600/30 transition-colors"
                    title="Delete Selected"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              )}
              <button 
                onClick={() => router.push('/recipes/new')} 
                className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow hover:bg-primary/90 h-9 px-4 py-2 gap-2"
              >
                <Plus className="h-4 w-4" />
                Add Recipe
              </button>
            </div>
          }
        />
        
        {/* Statistics */}
        <div className="flex items-center gap-6 text-sm text-muted-foreground mt-4">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            <span>{workflows.length} total workflows</span>
          </div>
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            <span>{filteredWorkflows.length} showing</span>
          </div>
          {selectedWorkflows.size > 0 && (
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-400" />
              <span className="text-green-400">{selectedWorkflows.size} selected</span>
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card border-b-2 border-card-border px-6 py-4 shadow-sm">
        <div className="flex flex-col lg:flex-row gap-4 items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search workflows by name, type, steps, or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-input border border-border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
          
          <div className="flex gap-3">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-3 py-2.5 bg-input border border-border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="all">All Types</option>
              <option value="fullflow">Full Workflows</option>
              <option value="subflow">Sub Workflows</option>
              <option value="workflow">Generic Workflows</option>
            </select>
            
            <select
              value={selectedComplexity}
              onChange={(e) => setSelectedComplexity(e.target.value)}
              className="px-3 py-2.5 bg-input border border-border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="all">All Complexity</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
            
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-2.5 bg-input border border-border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="last_executed">Last Executed</option>
              <option value="name">Name</option>
              <option value="success_rate">Success Rate</option>
              <option value="execution_count">Execution Count</option>
            </select>

            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="px-3 py-2.5 bg-input border border-border rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors text-sm"
              title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
          </div>
        </div>

        {filteredWorkflows.length > 0 && (
          <div className="flex items-center justify-between mt-4">
            <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={selectedWorkflows.size === filteredWorkflows.length && filteredWorkflows.length > 0}
                onChange={(e) => handleSelectAll(e.target.checked)}
                className="rounded border-border text-green-500 focus:ring-green-500 focus:ring-offset-0"
              />
              Select all visible workflows
            </label>
          </div>
        )}
      </div>

      {/* Workflows Grid */}
      <div className="p-6">
        {filteredWorkflows.length === 0 ? (
          <div className="text-center py-16">
            <Workflow className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {workflows.length === 0 
                ? "No workflows found" 
                : "No workflows match your filters"
              }
            </h3>
            <p className="text-muted-foreground mb-6">
              {workflows.length === 0 
                ? "Create your first workflow to get started with automation"
                : "Try adjusting your search or filters to find workflows"
              }
            </p>
            {workflows.length === 0 && (
              <button 
                onClick={() => router.push('/recipes/new')} 
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors mx-auto"
              >
                <Plus className="h-5 w-5" />
                Create Your First Workflow
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredWorkflows.map((workflow) => (
              <div
                key={workflow.id}
                className={`workflow-card group relative bg-card border-2 rounded-xl p-6 cursor-pointer ${
                  selectedWorkflows.has(workflow.id) 
                    ? 'selected ring-2 ring-green-500 border-green-500' 
                    : 'border-card-border'
                }`}
                onClick={(e) => {
                  if ((e.target as HTMLElement).closest('.workflow-actions')) {
                    return // Don't navigate when clicking actions
                  }
                  router.push(`/recipes/${workflow.id}`)
                }}
              >
                {/* Selection Checkbox */}
                <div className="absolute top-4 right-4 workflow-actions">
                  <input
                    type="checkbox"
                    checked={selectedWorkflows.has(workflow.id)}
                    onChange={(e) => handleSelectWorkflow(workflow.id, e.target.checked)}
                    className="rounded border-border text-green-500 focus:ring-green-500 focus:ring-offset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  />
                </div>

                {/* Workflow Header */}
                <div className="flex items-start gap-3 mb-4">
                  <div 
                    className={`w-12 h-12 ${getWorkflowTypeColor(workflow.catalog_type)} rounded-lg flex items-center justify-center text-2xl shrink-0`}
                  >
                    {getWorkflowIcon(workflow.catalog_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-foreground mb-1 line-clamp-2">
                      {workflow.nl_query}
                    </h3>
                    <p className="text-sm text-muted-foreground capitalize">
                      {workflow.catalog_type?.replace('_', ' ') || 'workflow'}
                    </p>
                    {workflow.complexity_level && (
                      <div className="flex items-center gap-2 mt-1">
                        <div 
                          className={`w-2 h-2 rounded-full ${getComplexityColor(workflow.complexity_level)}`}
                          title={`Complexity: ${workflow.complexity_level}`}
                        />
                        <span className="text-xs text-muted-foreground capitalize">
                          {workflow.complexity_level}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Workflow Stats */}
                <div className="grid grid-cols-3 gap-3 mb-4 text-center">
                  <div>
                    <div className="text-lg font-semibold text-foreground">
                      {workflow.recipe_steps?.length || 0}
                    </div>
                    <div className="text-xs text-muted-foreground">Steps</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-foreground">
                      {workflow.required_tools?.length || 0}
                    </div>
                    <div className="text-xs text-muted-foreground">Tools</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-foreground">
                      {workflow.execution_count || 0}
                    </div>
                    <div className="text-xs text-muted-foreground">Runs</div>
                  </div>
                </div>

                {/* Performance Indicators */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    {workflow.success_rate !== undefined && (
                      <div className="flex items-center gap-1">
                        <TrendingUp className={`h-3 w-3 ${
                          workflow.success_rate > 0.8 ? 'text-green-400' : 
                          workflow.success_rate > 0.6 ? 'text-yellow-400' : 'text-red-400'
                        }`} />
                        <span className={workflow.success_rate > 0.8 ? 'text-green-400' : 
                          workflow.success_rate > 0.6 ? 'text-yellow-400' : 'text-red-400'}>
                          {Math.round(workflow.success_rate * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>{formatLastExecuted(workflow.last_executed)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Zap className="h-3 w-3" />
                      <span className="capitalize">{workflow.status || 'active'}</span>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="workflow-actions flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleWorkflowExecute(workflow.id)
                    }}
                    className="flex-1 flex items-center justify-center gap-2 py-2 px-3 bg-green-600/20 border border-green-600/30 rounded-lg text-green-400 hover:bg-green-600/30 transition-colors text-sm"
                  >
                    <Play className="h-3 w-3" />
                    Execute
                  </button>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      router.push(`/recipes/${workflow.id}`)
                    }}
                    className="flex items-center justify-center gap-2 py-2 px-3 bg-input border border-border rounded-lg text-foreground hover:bg-accent transition-colors text-sm"
                  >
                    <Eye className="h-3 w-3" />
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedWorkflows(new Set([workflow.id]))
                      // Open context menu or more actions
                    }}
                    className="flex items-center justify-center gap-2 py-2 px-3 bg-input border border-border rounded-lg text-foreground hover:bg-accent transition-colors text-sm"
                  >
                    <MoreVertical className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}