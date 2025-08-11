import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  ArrowLeft,
  Download,
  Play,
  Settings,
  Clock,
  Users,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  ChevronRight,
  ChevronDown,
  Copy,
  ExternalLink,
  Loader2,
  ChefHat,
  ListChecks,
  FileTemplate,
  Wrench,
  GitBranch,
} from 'lucide-react'
import { api } from '../services/api'

interface RecipeStep {
  id: string
  name: string
  type: string
  tool_id?: number
  parameters?: Record<string, any>
  depends_on?: string[]
}

interface Recipe {
  id: number
  nl_query: string
  template: string
  template_type: string
  recipe_steps?: RecipeStep[]
  required_tools?: number[]
  execution_time_estimate?: number
  complexity_level?: string
  success_rate?: number
  last_executed?: string
  execution_count?: number
  reasoning_trace?: string
  status: string
  created_at: string
  updated_at: string
}

interface Tool {
  id: number
  nl_query: string
  template_type: string
  tool_capabilities?: string[]
  health_status?: string
}

interface SupportedFormat {
  format: string
  name: string
  description: string
}

const RECIPE_TYPE_ICONS = {
  recipe: ChefHat,
  recipe_step: ListChecks,
  recipe_template: FileTemplate,
} as const

const STEP_TYPE_COLORS = {
  action: 'bg-blue-500',
  condition: 'bg-yellow-500',
  loop: 'bg-purple-500',
  transform: 'bg-green-500',
  tool: 'bg-orange-500',
  parallel: 'bg-teal-500',
} as const

const COMPLEXITY_COLORS = {
  beginner: 'bg-green-500',
  intermediate: 'bg-yellow-500',
  advanced: 'bg-red-500',
} as const

export default function RecipeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [tools, setTools] = useState<Record<number, Tool>>({})
  const [supportedFormats, setSupportedFormats] = useState<SupportedFormat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [selectedFormat, setSelectedFormat] = useState<string>('')
  const [compilingFormat, setCompilingFormat] = useState<string>('')
  const [compiledWorkflow, setCompiledWorkflow] = useState<any>(null)
  const [showWorkflow, setShowWorkflow] = useState(false)

  useEffect(() => {
    if (id) {
      fetchRecipeDetails(parseInt(id))
    }
  }, [id])

  const fetchRecipeDetails = async (recipeId: number) => {
    setLoading(true)
    setError(null)
    
    try {
      // Fetch recipe details
      const recipeData = await api.getCacheEntry(recipeId)
      setRecipe(recipeData)

      // Fetch required tools
      if (recipeData.required_tools && recipeData.required_tools.length > 0) {
        const toolPromises = recipeData.required_tools.map(toolId => 
          api.getCacheEntry(toolId).catch(() => null)
        )
        const toolResults = await Promise.all(toolPromises)
        const toolsMap: Record<number, Tool> = {}
        
        toolResults.forEach((tool, index) => {
          if (tool) {
            toolsMap[recipeData.required_tools![index]] = tool
          }
        })
        setTools(toolsMap)
      }

      // Fetch supported formats
      try {
        const formatsData = await api.getSupportedFormats(recipeId)
        setSupportedFormats(formatsData.supported_formats)
        if (formatsData.supported_formats.length > 0) {
          setSelectedFormat(formatsData.supported_formats[0].format)
        }
      } catch (err) {
        console.warn('Failed to fetch supported formats:', err)
      }

    } catch (err: any) {
      setError(err.message || 'Failed to fetch recipe details')
      toast.error('Failed to load recipe details')
    } finally {
      setLoading(false)
    }
  }

  const handleExportRecipe = async (format: string) => {
    if (!recipe) return

    setCompilingFormat(format)
    try {
      toast.loading(`Compiling to ${format}...`, { id: 'compile' })
      
      const result = await api.compileRecipe(recipe.id, format)
      
      if (result.success) {
        setCompiledWorkflow(result.workflow_definition)
        setShowWorkflow(true)
        toast.success(`Recipe compiled to ${format}`, { id: 'compile' })
      } else {
        toast.error(`Compilation failed: ${result.errors.join(', ')}`, { id: 'compile' })
      }
    } catch (err: any) {
      toast.error('Export failed', { id: 'compile' })
    } finally {
      setCompilingFormat('')
    }
  }

  const handleCopyWorkflow = () => {
    if (compiledWorkflow) {
      navigator.clipboard.writeText(JSON.stringify(compiledWorkflow, null, 2))
      toast.success('Workflow copied to clipboard')
    }
  }

  const handleDownloadWorkflow = () => {
    if (compiledWorkflow && recipe) {
      const blob = new Blob([JSON.stringify(compiledWorkflow, null, 2)], {
        type: 'application/json'
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${recipe.nl_query.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_${selectedFormat}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('Workflow downloaded')
    }
  }

  const toggleStepExpansion = (stepId: string) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId)
    } else {
      newExpanded.add(stepId)
    }
    setExpandedSteps(newExpanded)
  }

  const getStepTypeColor = (stepType: string) => {
    return STEP_TYPE_COLORS[stepType as keyof typeof STEP_TYPE_COLORS] || 'bg-gray-500'
  }

  const getComplexityColor = (complexity?: string) => {
    return COMPLEXITY_COLORS[complexity as keyof typeof COMPLEXITY_COLORS] || 'bg-gray-500'
  }

  const formatExecutionTime = (seconds?: number) => {
    if (!seconds) return 'Unknown'
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h`
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

  const getRecipeIcon = (templateType: string) => {
    const IconComponent = RECIPE_TYPE_ICONS[templateType as keyof typeof RECIPE_TYPE_ICONS] || ChefHat
    return <IconComponent className="h-6 w-6" />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading recipe details...</span>
      </div>
    )
  }

  if (error || !recipe) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 mb-4">{error || 'Recipe not found'}</p>
        <Button onClick={() => navigate('/recipes')}>Back to Recipes</Button>
      </div>
    )
  }

  const recipeData = recipe.template ? JSON.parse(recipe.template) : {}
  const steps = recipe.recipe_steps || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm" 
          onClick={() => navigate('/recipes')}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Recipes
        </Button>
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-purple-500`}>
            {getRecipeIcon(recipe.template_type)}
          </div>
          <div>
            <h1 className="text-2xl font-semibold">{recipe.nl_query}</h1>
            <p className="text-muted-foreground capitalize">
              {recipe.template_type.replace('_', ' ')}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Recipe Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Recipe Overview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {recipe.execution_time_estimate && (
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{formatExecutionTime(recipe.execution_time_estimate)}</p>
                      <p className="text-xs text-muted-foreground">Est. Time</p>
                    </div>
                  </div>
                )}
                
                {recipe.execution_count !== undefined && (
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{recipe.execution_count}</p>
                      <p className="text-xs text-muted-foreground">Executions</p>
                    </div>
                  </div>
                )}

                {recipe.success_rate !== undefined && (
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{Math.round(recipe.success_rate)}%</p>
                      <p className="text-xs text-muted-foreground">Success Rate</p>
                    </div>
                  </div>
                )}

                {recipe.complexity_level && (
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${getComplexityColor(recipe.complexity_level)}`} />
                    <div>
                      <p className="text-sm font-medium capitalize">{recipe.complexity_level}</p>
                      <p className="text-xs text-muted-foreground">Complexity</p>
                    </div>
                  </div>
                )}
              </div>

              {recipe.reasoning_trace && (
                <div className="mt-4 p-3 bg-muted rounded-md">
                  <p className="text-sm text-muted-foreground">{recipe.reasoning_trace}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recipe Steps */}
          {steps.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ListChecks className="h-5 w-5" />
                  Recipe Steps ({steps.length})
                </CardTitle>
                <CardDescription>
                  Step-by-step breakdown of the recipe workflow
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {steps.map((step, index) => (
                    <div key={step.id} className="border rounded-lg p-4">
                      <div 
                        className="flex items-center justify-between cursor-pointer"
                        onClick={() => toggleStepExpansion(step.id)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-muted-foreground">
                              {index + 1}
                            </span>
                            <div className={`w-3 h-3 rounded-full ${getStepTypeColor(step.type)}`} />
                          </div>
                          <div>
                            <p className="font-medium">{step.name}</p>
                            <p className="text-sm text-muted-foreground capitalize">
                              {step.type} {step.tool_id && `• Tool #${step.tool_id}`}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {step.depends_on && step.depends_on.length > 0 && (
                            <Badge variant="outline" className="text-xs">
                              Depends on {step.depends_on.length} step{step.depends_on.length > 1 ? 's' : ''}
                            </Badge>
                          )}
                          {expandedSteps.has(step.id) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </div>
                      </div>

                      {expandedSteps.has(step.id) && (
                        <div className="mt-3 pl-8 space-y-2">
                          {step.parameters && Object.keys(step.parameters).length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-1">Parameters:</p>
                              <div className="bg-muted p-2 rounded text-xs font-mono">
                                {JSON.stringify(step.parameters, null, 2)}
                              </div>
                            </div>
                          )}
                          
                          {step.depends_on && step.depends_on.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-1">Dependencies:</p>
                              <div className="flex flex-wrap gap-1">
                                {step.depends_on.map(dep => (
                                  <Badge key={dep} variant="outline" className="text-xs">
                                    {dep}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}

                          {step.tool_id && tools[step.tool_id] && (
                            <div>
                              <p className="text-sm font-medium mb-1">Tool Details:</p>
                              <div className="flex items-center gap-2 p-2 bg-muted rounded">
                                <Wrench className="h-4 w-4" />
                                <span className="text-sm">{tools[step.tool_id].nl_query}</span>
                                <Badge variant="secondary" className="text-xs">
                                  {tools[step.tool_id].template_type}
                                </Badge>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Export Section */}
          {supportedFormats.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Download className="h-5 w-5" />
                  Export Recipe
                </CardTitle>
                <CardDescription>
                  Compile recipe to executable workflow format
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select value={selectedFormat} onValueChange={setSelectedFormat}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select format" />
                  </SelectTrigger>
                  <SelectContent>
                    {supportedFormats.map(format => (
                      <SelectItem key={format.format} value={format.format}>
                        <div>
                          <p className="font-medium">{format.name}</p>
                          <p className="text-xs text-muted-foreground">{format.description}</p>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Button 
                  onClick={() => handleExportRecipe(selectedFormat)}
                  disabled={!selectedFormat || compilingFormat === selectedFormat}
                  className="w-full gap-2"
                >
                  {compilingFormat === selectedFormat ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Compiling...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4" />
                      Compile & Export
                    </>
                  )}
                </Button>

                {showWorkflow && compiledWorkflow && (
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">Compiled Workflow</p>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleCopyWorkflow}
                          className="h-8 w-8 p-0"
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleDownloadWorkflow}
                          className="h-8 w-8 p-0"
                        >
                          <Download className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <div className="bg-muted p-3 rounded max-h-64 overflow-auto">
                      <pre className="text-xs">
                        {JSON.stringify(compiledWorkflow, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Required Tools */}
          {recipe.required_tools && recipe.required_tools.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wrench className="h-5 w-5" />
                  Required Tools ({recipe.required_tools.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recipe.required_tools.map(toolId => {
                    const tool = tools[toolId]
                    return (
                      <div key={toolId} className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-blue-500" />
                          <div>
                            <p className="text-sm font-medium">
                              {tool ? tool.nl_query : `Tool #${toolId}`}
                            </p>
                            {tool && (
                              <p className="text-xs text-muted-foreground capitalize">
                                {tool.template_type}
                              </p>
                            )}
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/tools/${toolId}`)}
                          className="h-8 w-8 p-0"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recipe Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium">Status</p>
                <Badge variant={recipe.status === 'active' ? 'default' : 'secondary'}>
                  {recipe.status}
                </Badge>
              </div>
              
              <div>
                <p className="text-sm font-medium">Last Executed</p>
                <p className="text-sm text-muted-foreground">
                  {formatLastExecuted(recipe.last_executed)}
                </p>
              </div>

              <div>
                <p className="text-sm font-medium">Created</p>
                <p className="text-sm text-muted-foreground">
                  {new Date(recipe.created_at).toLocaleDateString()}
                </p>
              </div>

              <div>
                <p className="text-sm font-medium">Updated</p>
                <p className="text-sm text-muted-foreground">
                  {new Date(recipe.updated_at).toLocaleDateString()}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}