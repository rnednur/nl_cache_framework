'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { toast } from 'react-hot-toast'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/app/components/ui/card'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Badge } from '@/app/components/ui/badge'
import { Textarea } from '@/app/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import {
  ArrowLeft,
  Plus,
  Save,
  Wrench,
  Bot,
  Code,
  Webhook,
  Globe,
  Settings,
  Trash2,
  Loader2,
  Edit,
} from 'lucide-react'
import api, { type CacheItem } from '@/app/services/api'

const TOOL_TYPES = {
  mcp_tool: { label: 'MCP Tool', icon: Webhook, description: 'Model Context Protocol tool' },
  agent: { label: 'AI Agent', icon: Bot, description: 'Autonomous AI agent' },
  function: { label: 'Function', icon: Code, description: 'Reusable function definition' },
  api: { label: 'API', icon: Globe, description: 'API endpoint or service' },
  workflow: { label: 'Workflow', icon: Settings, description: 'Workflow automation' },
} as const

const HEALTH_STATUS_OPTIONS = ['healthy', 'degraded', 'unhealthy', 'unknown'] as const

interface Tool extends CacheItem {
  tool_capabilities?: string[]
  tool_dependencies?: Record<string, any>
  execution_config?: Record<string, any>
  health_status?: string
  last_tested?: string
}

export default function EditTool() {
  const router = useRouter()
  const params = useParams()
  const toolId = parseInt(params.id as string)
  
  const [tool, setTool] = useState<Tool | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [formData, setFormData] = useState({
    nl_query: '',
    template: '{}',
    template_type: 'function' as keyof typeof TOOL_TYPES,
    reasoning_trace: '',
    tool_capabilities: [] as string[],
    health_status: 'unknown' as typeof HEALTH_STATUS_OPTIONS[number],
    execution_config: {} as Record<string, any>,
    tool_dependencies: {} as Record<string, any>,
    catalog_type: '',
    catalog_subtype: '',
    catalog_name: '',
    status: 'active',
  })
  const [newCapability, setNewCapability] = useState('')

  useEffect(() => {
    if (toolId) {
      fetchTool()
    }
  }, [toolId])

  const fetchTool = async () => {
    setLoading(true)
    setError(null)
    try {
      const toolData = await api.getCacheEntry(toolId)
      setTool(toolData)
      
      // Pre-populate form with existing data
      setFormData({
        nl_query: toolData.nl_query || '',
        template: toolData.template || '{}',
        template_type: (toolData.template_type as keyof typeof TOOL_TYPES) || 'function',
        reasoning_trace: toolData.reasoning_trace || '',
        tool_capabilities: toolData.tool_capabilities || [],
        health_status: (toolData.health_status as typeof HEALTH_STATUS_OPTIONS[number]) || 'unknown',
        execution_config: toolData.execution_config || {},
        tool_dependencies: toolData.tool_dependencies || {},
        catalog_type: toolData.catalog_type || '',
        catalog_subtype: toolData.catalog_subtype || '',
        catalog_name: toolData.catalog_name || '',
        status: toolData.status || 'active',
      })
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tool')
      toast.error('Failed to load tool')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.nl_query.trim()) {
      toast.error('Tool name is required')
      return
    }

    setSaving(true)
    try {
      // Prepare the update data
      const updateData = {
        nl_query: formData.nl_query,
        template: formData.template,
        template_type: formData.template_type,
        reasoning_trace: formData.reasoning_trace,
        tool_capabilities: formData.tool_capabilities,
        execution_config: formData.execution_config,
        tool_dependencies: formData.tool_dependencies,
        health_status: formData.health_status,
        catalog_type: formData.catalog_type,
        catalog_subtype: formData.catalog_subtype,
        catalog_name: formData.catalog_name,
        status: formData.status,
      }

      await api.updateCacheEntry(toolId, updateData)
      toast.success('Tool updated successfully!')
      router.push(`/tools/${toolId}`)
    } catch (error: any) {
      toast.error(`Failed to update tool: ${error.message}`)
    } finally {
      setSaving(false)
    }
  }

  const addCapability = () => {
    if (newCapability.trim() && !formData.tool_capabilities.includes(newCapability.trim())) {
      setFormData(prev => ({
        ...prev,
        tool_capabilities: [...prev.tool_capabilities, newCapability.trim()]
      }))
      setNewCapability('')
    }
  }

  const removeCapability = (capability: string) => {
    setFormData(prev => ({
      ...prev,
      tool_capabilities: prev.tool_capabilities.filter(c => c !== capability)
    }))
  }

  const handleExecutionConfigChange = (value: string) => {
    try {
      const parsed = JSON.parse(value)
      setFormData(prev => ({ ...prev, execution_config: parsed }))
    } catch (e) {
      // Invalid JSON, keep the string value for editing
    }
  }

  const handleToolDependenciesChange = (value: string) => {
    try {
      const parsed = JSON.parse(value)
      setFormData(prev => ({ ...prev, tool_dependencies: parsed }))
    } catch (e) {
      // Invalid JSON, keep the string value for editing
    }
  }

  const getToolTypeIcon = (type: keyof typeof TOOL_TYPES) => {
    const Icon = TOOL_TYPES[type]?.icon || Code
    return <Icon className="h-5 w-5" />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error || !tool) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/tools')}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Tools
          </Button>
        </div>
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-red-400">Failed to load tool data</p>
              <p className="text-neutral-400 text-sm mt-2">{error}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/tools/${toolId}`)}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Tool
          </Button>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-blue-500">
              {getToolTypeIcon(formData.template_type)}
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white">Edit Tool</h1>
              <p className="text-neutral-400">
                {TOOL_TYPES[formData.template_type]?.description || 'Tool configuration'}
              </p>
            </div>
          </div>
        </div>
        <Button 
          onClick={handleSubmit} 
          disabled={saving}
          className="gap-2"
        >
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Define the basic properties of your tool
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Tool Name *
              </label>
              <Input
                value={formData.nl_query}
                onChange={(e) => setFormData(prev => ({ ...prev, nl_query: e.target.value }))}
                placeholder="Enter a descriptive name for your tool..."
                className="!bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Tool Type
                </label>
                <Select
                  value={formData.template_type}
                  onValueChange={(value) => setFormData(prev => ({ 
                    ...prev, 
                    template_type: value as keyof typeof TOOL_TYPES 
                  }))}
                >
                  <SelectTrigger className="!bg-neutral-900 border-neutral-700 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(TOOL_TYPES).map(([key, type]) => (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center gap-2">
                          <type.icon className="h-4 w-4" />
                          <span>{type.label}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Health Status
                </label>
                <Select
                  value={formData.health_status}
                  onValueChange={(value) => setFormData(prev => ({ 
                    ...prev, 
                    health_status: value as typeof HEALTH_STATUS_OPTIONS[number]
                  }))}
                >
                  <SelectTrigger className="!bg-neutral-900 border-neutral-700 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {HEALTH_STATUS_OPTIONS.map((status) => (
                      <SelectItem key={status} value={status}>
                        <span className="capitalize">{status}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Reasoning Trace
              </label>
              <Textarea
                value={formData.reasoning_trace}
                onChange={(e) => setFormData(prev => ({ ...prev, reasoning_trace: e.target.value }))}
                placeholder="Describe the purpose and functionality of this tool..."
                className="min-h-[100px] !bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Catalog Information */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Catalog Type
                </label>
                <Input
                  value={formData.catalog_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, catalog_type: e.target.value }))}
                  placeholder="e.g., api, function, agent"
                  className="!bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Catalog Subtype
                </label>
                <Input
                  value={formData.catalog_subtype}
                  onChange={(e) => setFormData(prev => ({ ...prev, catalog_subtype: e.target.value }))}
                  placeholder="e.g., rest, graphql, webhook"
                  className="!bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Catalog Name
                </label>
                <Input
                  value={formData.catalog_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, catalog_name: e.target.value }))}
                  placeholder="Specific tool identifier"
                  className="!bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tool Capabilities */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <CardTitle>Capabilities</CardTitle>
            <CardDescription>
              Define what this tool can do
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={newCapability}
                onChange={(e) => setNewCapability(e.target.value)}
                placeholder="Add a capability..."
                className="flex-1 !bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCapability())}
              />
              <Button type="button" onClick={addCapability} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="flex flex-wrap gap-2">
              {formData.tool_capabilities.map((capability) => (
                <Badge
                  key={capability}
                  variant="secondary"
                  className="flex items-center gap-1 bg-neutral-700 text-neutral-200"
                >
                  {capability}
                  <button
                    type="button"
                    onClick={() => removeCapability(capability)}
                    className="ml-1 hover:text-red-400"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Template Configuration */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <CardTitle>Template Configuration</CardTitle>
            <CardDescription>
              Define the tool's template and configuration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Template JSON
              </label>
              <Textarea
                value={formData.template}
                onChange={(e) => setFormData(prev => ({ ...prev, template: e.target.value }))}
                placeholder="Enter JSON template..."
                className="min-h-[200px] font-mono text-sm !bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Execution Configuration
              </label>
              <Textarea
                value={JSON.stringify(formData.execution_config, null, 2)}
                onChange={(e) => handleExecutionConfigChange(e.target.value)}
                placeholder="Enter execution configuration JSON..."
                className="min-h-[120px] font-mono text-sm !bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Tool Dependencies
              </label>
              <Textarea
                value={JSON.stringify(formData.tool_dependencies, null, 2)}
                onChange={(e) => handleToolDependenciesChange(e.target.value)}
                placeholder="Enter tool dependencies JSON..."
                className="min-h-[120px] font-mono text-sm !bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  )
} 