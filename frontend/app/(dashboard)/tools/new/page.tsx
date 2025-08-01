'use client'

import { useState } from 'react'
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
} from 'lucide-react'
import api from '@/app/services/api'

const TOOL_TYPES = {
  mcp_tool: { label: 'MCP Tool', icon: Webhook, description: 'Model Context Protocol tool' },
  agent: { label: 'AI Agent', icon: Bot, description: 'Autonomous AI agent' },
  function: { label: 'Function', icon: Code, description: 'Reusable function definition' },
  api: { label: 'API', icon: Globe, description: 'API endpoint or service' },
  workflow: { label: 'Workflow', icon: Settings, description: 'Workflow automation' },
} as const

const HEALTH_STATUS_OPTIONS = ['healthy', 'degraded', 'unhealthy', 'unknown'] as const

export default function NewTool() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    nl_query: '',
    template: '{}',
    template_type: 'function' as keyof typeof TOOL_TYPES,
    tool_capabilities: [] as string[],
    health_status: 'unknown' as typeof HEALTH_STATUS_OPTIONS[number],
    execution_config: {} as Record<string, any>,
    tool_dependencies: {} as Record<string, any>,
  })
  const [newCapability, setNewCapability] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.nl_query.trim()) {
      toast.error('Tool name is required')
      return
    }

    setLoading(true)
    try {
      // Prepare the tool data based on type
      let templateData = {}
      
      switch (formData.template_type) {
        case 'mcp_tool':
          templateData = {
            server_config: {
              name: formData.nl_query,
              command: '',
              args: [],
              env: {}
            },
            tool_spec: {
              name: formData.nl_query,
              description: formData.nl_query,
              input_schema: {},
              capabilities: formData.tool_capabilities
            },
            connection_params: {
              timeout: 30,
              retry_count: 3
            }
          }
          break
        case 'agent':
          templateData = {
            agent_config: {
              name: formData.nl_query,
              description: formData.nl_query,
              model: 'gpt-4',
              temperature: 0.7,
              max_tokens: 2000
            },
            capabilities: formData.tool_capabilities,
            tools: [],
            system_prompt: `You are ${formData.nl_query}`,
            execution_params: {
              max_iterations: 10,
              timeout: 300,
              memory_enabled: true
            }
          }
          break
        case 'function':
          templateData = {
            function_def: {
              name: formData.nl_query.replace(/\s+/g, '_').toLowerCase(),
              description: formData.nl_query,
              language: 'python',
              code: '# Function implementation goes here',
              entry_point: 'main'
            },
            parameters: {
              required: [],
              optional: [],
              schema: {}
            },
            execution_config: {
              timeout: 60,
              memory_limit: 128,
              allowed_imports: []
            }
          }
          break
        default:
          templateData = {
            name: formData.nl_query,
            description: formData.nl_query,
            capabilities: formData.tool_capabilities
          }
      }

      const toolData = {
        nl_query: formData.nl_query,
        template: JSON.stringify(templateData),
        template_type: formData.template_type,
        is_template: true,
        tool_capabilities: formData.tool_capabilities,
        health_status: formData.health_status,
        execution_config: formData.execution_config,
        tool_dependencies: formData.tool_dependencies,
        status: 'active',
      }

      const createdTool = await api.createCacheEntry(toolData)
      toast.success('Tool created successfully!')
      router.push(`/tools/${createdTool.id}`)
    } catch (error: any) {
      toast.error(`Failed to create tool: ${error.message}`)
    } finally {
      setLoading(false)
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

  const getToolTypeIcon = (templateType: keyof typeof TOOL_TYPES) => {
    const Icon = TOOL_TYPES[templateType].icon
    return <Icon className="h-5 w-5" />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
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
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-blue-500">
              {getToolTypeIcon(formData.template_type)}
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white">Create New Tool</h1>
              <p className="text-neutral-400">
                {TOOL_TYPES[formData.template_type].description}
              </p>
            </div>
          </div>
        </div>
        <Button 
          onClick={handleSubmit} 
          disabled={loading}
          className="gap-2"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {loading ? 'Creating...' : 'Create Tool'}
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
                className="bg-neutral-900 border-neutral-700"
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
                  <SelectTrigger className="bg-neutral-900 border-neutral-700">
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
                  <SelectTrigger className="bg-neutral-900 border-neutral-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {HEALTH_STATUS_OPTIONS.map((status) => (
                      <SelectItem key={status} value={status}>
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            status === 'healthy' ? 'bg-green-500' :
                            status === 'degraded' ? 'bg-yellow-500' :
                            status === 'unhealthy' ? 'bg-red-500' :
                            'bg-neutral-500'
                          }`} />
                          <span className="capitalize">{status}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tool Capabilities */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <CardTitle>Tool Capabilities</CardTitle>
            <CardDescription>
              Define what this tool can do
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={newCapability}
                onChange={(e) => setNewCapability(e.target.value)}
                placeholder="Enter a capability..."
                className="bg-neutral-900 border-neutral-700"
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCapability())}
              />
              <Button
                type="button"
                variant="outline"
                onClick={addCapability}
                className="gap-2 border-neutral-600 text-neutral-300 hover:bg-neutral-700"
              >
                <Plus className="h-4 w-4" />
                Add
              </Button>
            </div>

            {formData.tool_capabilities.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {formData.tool_capabilities.map((capability, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="bg-neutral-700 text-neutral-300 gap-2"
                  >
                    {capability}
                    <button
                      type="button"
                      onClick={() => removeCapability(capability)}
                      className="text-neutral-400 hover:text-red-400"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </form>
    </div>
  )
}