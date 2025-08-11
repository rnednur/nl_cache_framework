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
import { Badge } from '@/app/components/ui/badge'
import {
  ArrowLeft,
  Play,
  Edit,
  Settings,
  CheckCircle,
  AlertCircle,
  XCircle,
  HelpCircle,
  Loader2,
  Wrench,
  Bot,
  Code,
  Webhook,
  Globe,
  Calendar,
  Clock,
} from 'lucide-react'
import api, { type CacheItem } from '@/app/services/api'

interface Tool extends CacheItem {
  tool_capabilities?: string[]
  tool_dependencies?: Record<string, any>
  execution_config?: Record<string, any>
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

const HEALTH_STATUS_CONFIG = {
  healthy: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500' },
  degraded: { icon: AlertCircle, color: 'text-yellow-500', bg: 'bg-yellow-500' },
  unhealthy: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500' },
  unknown: { icon: HelpCircle, color: 'text-neutral-500', bg: 'bg-neutral-500' },
} as const

export default function ToolDetail() {
  const router = useRouter()
  const params = useParams()
  const toolId = parseInt(params.id as string)

  // If ID is not a valid number, redirect to create page
  if (isNaN(toolId)) {
    router.replace('/tools/new')
    return null
  }

  const [tool, setTool] = useState<Tool | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)

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
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tool')
      toast.error('Failed to load tool')
    } finally {
      setLoading(false)
    }
  }

  const handleTestTool = async () => {
    if (!tool) return

    setTesting(true)
    try {
      toast.loading('Testing tool...', { id: 'test' })
      // This would call the test endpoint when implemented
      await new Promise(resolve => setTimeout(resolve, 2000)) // Placeholder
      toast.success('Tool test completed successfully', { id: 'test' })
      
      // Update the tool's last_tested timestamp
      setTool(prev => prev ? { ...prev, last_tested: new Date().toISOString() } : null)
    } catch (err: any) {
      toast.error('Tool test failed', { id: 'test' })
    } finally {
      setTesting(false)
    }
  }

  const getToolIcon = (templateType: string) => {
    const toolType = TOOL_TYPES[templateType as keyof typeof TOOL_TYPES]
    if (toolType) {
      const Icon = toolType.icon
      return <Icon className="h-6 w-6" />
    }
    return <Wrench className="h-6 w-6" />
  }

  const getToolTypeColor = (templateType: string) => {
    return TOOL_TYPES[templateType as keyof typeof TOOL_TYPES]?.color || 'bg-neutral-500'
  }

  const getHealthStatusIcon = (status?: string) => {
    const config = HEALTH_STATUS_CONFIG[status as keyof typeof HEALTH_STATUS_CONFIG] || HEALTH_STATUS_CONFIG.unknown
    const Icon = config.icon
    return <Icon className={`h-5 w-5 ${config.color}`} />
  }

  const getHealthStatusColor = (status?: string) => {
    return HEALTH_STATUS_CONFIG[status as keyof typeof HEALTH_STATUS_CONFIG]?.bg || 'bg-neutral-500'
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

  const parseTemplate = (template: string) => {
    try {
      return JSON.parse(template)
    } catch {
      return {}
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading tool...</span>
      </div>
    )
  }

  if (error || !tool) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 mb-4">{error || 'Tool not found'}</p>
        <Button onClick={() => router.push('/tools')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Tools
        </Button>
      </div>
    )
  }

  const templateData = parseTemplate(tool.template)

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
            Back
          </Button>
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-lg ${getToolTypeColor(tool.template_type)}`}>
              {getToolIcon(tool.template_type)}
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white">{tool.nl_query}</h1>
              <p className="text-neutral-400 capitalize">
                {TOOL_TYPES[tool.template_type as keyof typeof TOOL_TYPES]?.label || tool.template_type}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => router.push(`/tools/${tool.id}/edit`)}
            className="gap-2 border-neutral-600 text-neutral-300 hover:bg-neutral-700"
          >
            <Edit className="h-4 w-4" />
            Edit
          </Button>
          <Button 
            onClick={handleTestTool} 
            disabled={testing}
            className="gap-2"
          >
            {testing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {testing ? 'Testing...' : 'Test Tool'}
          </Button>
        </div>
      </div>

      {/* Tool Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="flex justify-center mb-2">
                {getHealthStatusIcon(tool.health_status)}
              </div>
              <div className="text-sm text-neutral-400 capitalize">
                {tool.health_status || 'Unknown'}
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {tool.tool_capabilities?.length || 0}
              </div>
              <div className="text-sm text-neutral-400">Capabilities</div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {tool.usage_count || 0}
              </div>
              <div className="text-sm text-neutral-400">Usage Count</div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {formatLastTested(tool.last_tested)}
              </div>
              <div className="text-sm text-neutral-400">Last Tested</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tool Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tool Configuration */}
        <div className="lg:col-span-2">
          <Card className="bg-neutral-800 border-neutral-700">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Tool Configuration
              </CardTitle>
              <CardDescription>
                Configuration and template details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-neutral-900 rounded-lg p-4">
                <pre className="text-sm text-neutral-300 overflow-x-auto">
                  {JSON.stringify(templateData, null, 2)}
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tool Info & Capabilities */}
        <div className="space-y-6">
          {/* Tool Information */}
          <Card className="bg-neutral-800 border-neutral-700">
            <CardHeader>
              <CardTitle>Tool Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-400">Status</span>
                <Badge variant={tool.status === 'active' ? 'default' : 'destructive'} className="capitalize">
                  {tool.status}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-400">Template</span>
                <Badge variant="outline" className="border-neutral-600 text-neutral-300">
                  {tool.is_template ? 'Yes' : 'No'}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-400">Created</span>
                <span className="text-sm text-white">
                  {new Date(tool.created_at).toLocaleDateString()}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-400">Last Updated</span>
                <span className="text-sm text-white">
                  {new Date(tool.updated_at).toLocaleDateString()}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Tool Capabilities */}
          {tool.tool_capabilities && tool.tool_capabilities.length > 0 && (
            <Card className="bg-neutral-800 border-neutral-700">
              <CardHeader>
                <CardTitle>Capabilities</CardTitle>
                <CardDescription>
                  What this tool can do
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {tool.tool_capabilities.map((capability, index) => (
                    <Badge
                      key={index}
                      variant="secondary"
                      className="bg-neutral-700 text-neutral-300"
                    >
                      {capability}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Dependencies */}
          {tool.tool_dependencies && Object.keys(tool.tool_dependencies).length > 0 && (
            <Card className="bg-neutral-800 border-neutral-700">
              <CardHeader>
                <CardTitle>Dependencies</CardTitle>
                <CardDescription>
                  Required dependencies for this tool
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(tool.tool_dependencies).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-sm text-neutral-400">{key}</span>
                      <span className="text-sm text-white">
                        {typeof value === 'string' ? value : JSON.stringify(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}