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
import { Input } from '@/app/components/ui/input'
import { Textarea } from '@/app/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import {
  ArrowLeft,
  Download,
  Edit,
  Settings,
  ExternalLink,
  Loader2,
  ChefHat,
  Layers,
  BookOpen,
  Save,
  X,
  Target,
  Home,
  ChevronRight,
  Copy,
  Share,
  MoreHorizontal,
  Clock,
  TrendingUp,
  Database,
  Code,
  Globe,
  Zap,
} from 'lucide-react'
import api, { type CacheItem } from '@/app/services/api'

interface Recipe extends CacheItem {
  recipe_steps?: Array<{
    id: string
    name: string
    type: string
    tool_id?: number
    depends_on?: string[]
  }>
  required_tools?: number[]
}

interface Tool extends CacheItem {
  tool_capabilities?: string[]
  health_status?: string
}

const RECIPE_TYPES = {
  recipe: { label: 'Complete Recipe', icon: ChefHat, color: 'bg-green-500' },
  recipe_step: { label: 'Recipe Step', icon: Layers, color: 'bg-blue-500' },
  recipe_template: { label: 'Recipe Template', icon: BookOpen, color: 'bg-purple-500' },
} as const

const COMPLEXITY_COLORS = {
  beginner: 'bg-green-500',
  intermediate: 'bg-yellow-500',
  advanced: 'bg-red-500',
} as const

const SUPPORTED_FORMATS = [
  { value: 'langchain', label: 'LangChain', description: 'Python LangChain workflow' },
  { value: 'langgraph', label: 'LangGraph', description: 'LangGraph state machine' },
  { value: 'langflow', label: 'Langflow', description: 'Langflow visual workflow' },
  { value: 'generic', label: 'Generic JSON', description: 'Generic workflow JSON' },
]

export default function RecipeDetail() {
  const router = useRouter()
  const params = useParams()
  const recipeId = parseInt(params.id as string)

  // If ID is not a valid number, redirect to create page
  if (isNaN(recipeId)) {
    router.replace('/recipes/new')
    return null
  }

  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFormat, setSelectedFormat] = useState('langchain')
  const [isExporting, setIsExporting] = useState(false)
  const [stepsTab, setStepsTab] = useState<'visual' | 'xml'>('visual')
  const [isEditingName, setIsEditingName] = useState(false)
  const [editedName, setEditedName] = useState('')
  const [isEditingDescription, setIsEditingDescription] = useState(false)
  const [editedDescription, setEditedDescription] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (recipeId) {
      fetchRecipe()
    }
  }, [recipeId])

  const fetchRecipe = async () => {
    setLoading(true)
    setError(null)
    try {
      const recipeData = await api.getCacheEntry(recipeId)
      
      // Parse workflow steps from template if it's our new format
      let enhancedRecipeData = { ...recipeData }
      if (recipeData.template && !recipeData.recipe_steps) {
        try {
          const templateObj = JSON.parse(recipeData.template)
          if (templateObj.flow && templateObj.flow.steps) {
            // Convert our workflow format to the expected recipe_steps format
            enhancedRecipeData.recipe_steps = templateObj.flow.steps.map((step: any) => ({
              id: step.id,
              name: step.name,
              type: step.type,
              tool_id: step.cache_entry_id,
              depends_on: [] // We could derive this from connections if needed
            }))
            
          }
        } catch (error) {
          // Not our format, leave as is
          console.log('Template is not workflow JSON format, using as-is')
        }
      }
      
      setRecipe(enhancedRecipeData)
      setEditedName(enhancedRecipeData.nl_query)
      setEditedDescription(enhancedRecipeData.template || '')

      // Fetch associated tools if they exist
      if (recipeData.required_tools && recipeData.required_tools.length > 0) {
        const toolsData = await api.getBulkCacheEntries(recipeData.required_tools)
        setTools(toolsData)
      }
      
    } catch (err: any) {
      setError(err.message || 'Failed to fetch recipe')
      toast.error('Failed to load recipe')
    } finally {
      setLoading(false)
    }
  }
  

  
  const handleSaveInlineEdit = async (field: 'name' | 'description') => {
    if (!recipe) return
    
    setIsSaving(true)
    try {
      const updateData = field === 'name' 
        ? { nl_query: editedName }
        : { template: editedDescription }
      
      const updatedRecipe = await api.updateCacheEntry(recipe.id, updateData)
      setRecipe(updatedRecipe)
      
      if (field === 'name') {
        setIsEditingName(false)
      } else {
        setIsEditingDescription(false)
      }
      
      toast.success(`Recipe ${field} updated successfully`)
    } catch (error: any) {
      toast.error(`Failed to update recipe ${field}: ${error.message}`)
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleCancelInlineEdit = (field: 'name' | 'description') => {
    if (field === 'name') {
      setEditedName(recipe?.nl_query || '')
      setIsEditingName(false)
    } else {
      setEditedDescription(recipe?.template || '')
      setIsEditingDescription(false)
    }
  }

  const handleExecuteWorkflow = async () => {
    if (!recipe) return

    try {
      toast.loading('Starting workflow execution...', { id: 'execute' })

      const result = await api.executeWorkflow(recipe.id, {}, false)

      toast.success('Workflow execution started successfully', { id: 'execute' })

      // For now, just show the execution URL in a toast
      toast.success(`Execution URL: ${result.execution_url}`)

      // In a full implementation, you might navigate to an execution monitoring page
      // or show a real-time execution progress dialog
      console.log('Workflow execution started:', result)

    } catch (error: any) {
      toast.error(`Workflow execution failed: ${error.message}`, { id: 'execute' })
      console.error('Workflow execution error:', error)
    }
  }
  

  const handleExportRecipe = async () => {
    if (!recipe) return

    setIsExporting(true)
    try {
      toast.loading(`Compiling recipe to ${selectedFormat}...`, { id: 'export' })
      
      // Call the recipe compilation API
      const result = await api.compileRecipe(recipe.id, selectedFormat)
      
      if (result.success) {
        // Create and download the workflow file
        const blob = new Blob([JSON.stringify(result.workflow_definition, null, 2)], {
          type: 'application/json'
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${recipe.nl_query.replace(/[^a-zA-Z0-9]/g, '_')}_${selectedFormat}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        toast.success(`Recipe exported as ${selectedFormat}`, { id: 'export' })
        
        // Show warnings if any
        if (result.warnings && result.warnings.length > 0) {
          result.warnings.forEach(warning => toast(warning, { icon: '⚠️' }))
        }
      } else {
        toast.error(`Export failed: ${result.errors.join(', ')}`, { id: 'export' })
      }
    } catch (err: any) {
      toast.error(`Export failed: ${err.message}`, { id: 'export' })
    } finally {
      setIsExporting(false)
    }
  }

  const getRecipeIcon = (templateType: string) => {
    const recipeType = RECIPE_TYPES[templateType as keyof typeof RECIPE_TYPES]
    if (recipeType) {
      const Icon = recipeType.icon
      return <Icon className="h-6 w-6" />
    }
    return <ChefHat className="h-6 w-6" />
  }

  const getRecipeTypeColor = (templateType: string) => {
    return RECIPE_TYPES[templateType as keyof typeof RECIPE_TYPES]?.color || 'bg-muted'
  }

  const getComplexityColor = (complexity?: string) => {
    return COMPLEXITY_COLORS[complexity as keyof typeof COMPLEXITY_COLORS] || 'bg-muted'
  }

  const getStepTypeIcon = (stepType: string) => {
    const iconMap: Record<string, any> = {
      'sql': Database,
      'api': Globe,
      'script': Code,
      'workflow': Zap,
      'function': Code,
      'data': Database,
      'transform': Layers,
      'validation': Target,
    }
    
    const IconComponent = iconMap[stepType.toLowerCase()] || Code
    return <IconComponent className="h-4 w-4" />
  }

  const getStepTypeColor = (stepType: string) => {
    const colorMap: Record<string, string> = {
      'sql': 'bg-blue-500',
      'api': 'bg-green-500', 
      'script': 'bg-purple-500',
      'workflow': 'bg-yellow-500',
      'function': 'bg-indigo-500',
      'data': 'bg-cyan-500',
      'transform': 'bg-orange-500',
      'validation': 'bg-red-500',
    }
    
    return colorMap[stepType.toLowerCase()] || 'bg-muted'
  }

  const generateRecipeXML = (recipe: Recipe) => {
    const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<recipe id="${recipe.id}" name="${recipe.nl_query}" status="${recipe.status}">
  <metadata>
    <description>${recipe.template || 'No description'}</description>
    <templateType>${recipe.template_type}</templateType>
    <complexity>${recipe.complexity_level || 'unknown'}</complexity>
    <usageCount>${recipe.usage_count || 0}</usageCount>
    <created>${recipe.created_at}</created>
    <updated>${recipe.updated_at}</updated>
  </metadata>
  
  <steps count="${recipe.recipe_steps?.length || 0}">
${recipe.recipe_steps?.map((step, index) => `    <step id="${step.id}" order="${index + 1}">
      <name>${step.name}</name>
      <type>${step.type}</type>
      ${step.tool_id ? `<toolId>${step.tool_id}</toolId>` : ''}
      ${step.depends_on && step.depends_on.length > 0 ? 
        `<dependencies>\n${step.depends_on.map(dep => `        <dependsOn>${dep}</dependsOn>`).join('\n')}\n      </dependencies>` : 
        ''}
    </step>`).join('\n') || '    <!-- No steps defined -->'}
  </steps>
  
  ${tools.length > 0 ? `<requiredTools count="${tools.length}">
${tools.map(tool => `    <tool id="${tool.id}">
      <name>${tool.nl_query}</name>
      <type>${tool.template_type}</type>
      ${tool.health_status ? `<healthStatus>${tool.health_status}</healthStatus>` : ''}
    </tool>`).join('\n')}
  </requiredTools>` : '  <requiredTools count="0" />'}
</recipe>`

    return xmlContent
  }


  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading recipe...</span>
      </div>
    )
  }

  if (error || !recipe) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 mb-4">{error || 'Recipe not found'}</p>
        <Button onClick={() => router.push('/recipes')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Recipes
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button
          onClick={() => router.push('/')}
          className="flex items-center gap-1 hover:text-foreground transition-colors"
        >
          <Home className="h-4 w-4" />
          Home
        </button>
        <ChevronRight className="h-4 w-4" />
        <button
          onClick={() => router.push('/recipes')}
          className="hover:text-foreground transition-colors"
        >
          Workflows
        </button>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground truncate max-w-[200px]" title={recipe.nl_query}>
          {recipe.nl_query}
        </span>
      </div>

      {/* Header */}
      <div className="workflow-card bg-card border-2 border-card-border p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-lg ${getRecipeTypeColor(recipe.template_type)} flex-shrink-0`}>
              {getRecipeIcon(recipe.template_type)}
            </div>
            <div className="min-w-0 flex-1">
              {isEditingName ? (
                <div className="flex items-center gap-2 mb-2">
                  <Input
                    value={editedName}
                    onChange={(e) => setEditedName(e.target.value)}
                    className="text-xl font-semibold bg-input border-border"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveInlineEdit('name')
                      if (e.key === 'Escape') handleCancelInlineEdit('name')
                    }}
                    autoFocus
                  />
                  <Button
                    size="sm"
                    onClick={() => handleSaveInlineEdit('name')}
                    disabled={isSaving}
                    className="shrink-0"
                  >
                    {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCancelInlineEdit('name')}
                    className="shrink-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2 group mb-2">
                  <h1 className="text-2xl font-semibold text-foreground truncate">{recipe.nl_query}</h1>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsEditingName(true)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-auto shrink-0"
                  >
                    <Edit className="h-3 w-3" />
                  </Button>
                </div>
              )}
              <div className="flex items-center gap-3 text-sm">
                <span className="text-muted-foreground capitalize">
                  {RECIPE_TYPES[recipe.template_type as keyof typeof RECIPE_TYPES]?.label || recipe.template_type}
                </span>
                <Badge 
                  variant={recipe.status === 'active' ? 'default' : recipe.status === 'pending' ? 'secondary' : 'outline'}
                  className={`capitalize ${
                    recipe.status === 'active' ? 'bg-green-600' : 
                    recipe.status === 'pending' ? 'bg-yellow-600' : 
                    'bg-muted'
                  }`}
                >
                  {recipe.status}
                </Badge>
                <span className="text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Created {new Date(recipe.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(recipe.id.toString())
                toast.success('Recipe ID copied to clipboard')
              }}
              className="gap-2 border-border text-muted-foreground hover:bg-accent"
            >
              <Copy className="h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const url = window.location.href
                navigator.clipboard.writeText(url)
                toast.success('Recipe URL copied to clipboard')
              }}
              className="gap-2 border-border text-muted-foreground hover:bg-accent"
            >
              <Share className="h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push(`/recipes/new?edit=${recipe.id}`)}
              className="gap-2 border-border text-foreground hover:bg-accent"
            >
              <Edit className="h-4 w-4" />
              Edit
            </Button>
            {recipe.template_type === 'workflow' && (
              <Button
                onClick={() => handleExecuteWorkflow()}
                className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                <Target className="h-4 w-4" />
                Execute
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Recipe Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="workflow-card bg-card border-2 border-card-border transition-colors cursor-pointer">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-foreground mb-1">
                  {recipe.recipe_steps?.length || 0}
                </div>
                <div className="text-sm text-muted-foreground">Steps</div>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-full">
                <Layers className="h-6 w-6 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border transition-colors cursor-pointer">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-foreground mb-1">
                  {recipe.usage_count || 0}
                </div>
                <div className="text-sm text-muted-foreground">Usage Count</div>
                {recipe.usage_count && recipe.usage_count > 0 && (
                  <div className="flex items-center gap-1 text-xs text-green-400 mt-1">
                    <TrendingUp className="h-3 w-3" />
                    Active
                  </div>
                )}
              </div>
              <div className="p-3 bg-green-500/10 rounded-full">
                <TrendingUp className="h-6 w-6 text-green-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border transition-colors cursor-pointer">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-foreground mb-1">
                  {tools.length || 0}
                </div>
                <div className="text-sm text-muted-foreground">Required Tools</div>
                {tools.length > 0 && (
                  <div className="text-xs text-muted-foreground mt-1">
                    {tools.filter(t => t.health_status === 'healthy').length} healthy
                  </div>
                )}
              </div>
              <div className="p-3 bg-purple-500/10 rounded-full">
                <Zap className="h-6 w-6 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border transition-colors cursor-pointer">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold text-foreground mb-1">
                  {new Date(recipe.created_at).toLocaleDateString()}
                </div>
                <div className="text-sm text-muted-foreground">Created</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {Math.floor((Date.now() - new Date(recipe.created_at).getTime()) / (1000 * 60 * 60 * 24))} days ago
                </div>
              </div>
              <div className="p-3 bg-orange-500/10 rounded-full">
                <Clock className="h-6 w-6 text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recipe Content - Unified View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recipe Steps */}
        <div className="lg:col-span-2">
          <Card className="workflow-card bg-card border-2 border-card-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-foreground">
                <Layers className="h-5 w-5" />
                Recipe Steps
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Workflow execution steps in order
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={stepsTab} onValueChange={(value) => setStepsTab(value as typeof stepsTab)}>
                <TabsList className="grid w-full grid-cols-2 mb-6 bg-muted border border-border">
                  <TabsTrigger value="visual" className="flex items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground">
                    <Layers className="h-4 w-4" />
                    Visual Steps
                  </TabsTrigger>
                  <TabsTrigger value="xml" className="flex items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground">
                    <Code className="h-4 w-4" />
                    XML View
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="visual" className="space-y-3">
                  {recipe.recipe_steps && recipe.recipe_steps.length > 0 ? (
                    <>
                      {recipe.recipe_steps.map((step, index) => (
                        <div
                          key={step.id}
                          className="group relative"
                        >
                          <div className="flex items-start gap-4 p-4 bg-muted/50 rounded-lg border border-border hover:border-primary/50 transition-colors">
                            <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-sm font-semibold">
                              {index + 1}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-start gap-2 mb-2">
                                <h4 className="font-medium text-foreground truncate">{step.name}</h4>
                                <div className={`flex items-center gap-1 px-2 py-1 rounded text-xs text-white ${getStepTypeColor(step.type)}`}>
                                  {getStepTypeIcon(step.type)}
                                  <span className="capitalize">{step.type}</span>
                                </div>
                              </div>
                              
                              {step.depends_on && step.depends_on.length > 0 && (
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs text-muted-foreground">Depends on:</span>
                                  <div className="flex gap-1">
                                    {step.depends_on.map((dep, i) => (
                                      <Badge key={i} variant="outline" className="text-xs border-border text-muted-foreground">
                                        #{dep}
                                      </Badge>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                <span>Step {index + 1} of {recipe.recipe_steps?.length}</span>
                                {step.tool_id && (
                                  <span className="flex items-center gap-1">
                                    <Zap className="h-3 w-3" />
                                    Tool #{step.tool_id}
                                  </span>
                                )}
                              </div>
                            </div>
                            
                            {/* Step Actions - shown on hover */}
                            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                              <Button 
                                size="sm" 
                                variant="ghost" 
                                className="h-6 w-6 p-0"
                                onClick={() => {
                                  // TODO: Implement step editing
                                  toast.info('Step editing coming soon!')
                                }}
                              >
                                <Edit className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                          
                          {/* Connection line to next step */}
                          {index < (recipe.recipe_steps?.length || 0) - 1 && (
                            <div className="flex justify-center">
                              <div className="w-px h-4 bg-border mt-2 mb-2"></div>
                            </div>
                          )}
                        </div>
                      ))}
                    </>
                  ) : (
                    <div className="text-center py-12">
                      <Layers className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-muted-foreground mb-2">No steps defined</h3>
                      <p className="text-sm text-muted-foreground mb-4">This workflow doesn't have any steps yet.</p>
                      <Button
                        onClick={() => router.push(`/recipes/new?edit=${recipe.id}`)}
                        variant="outline"
                        size="sm"
                        className="gap-2"
                      >
                        <Edit className="h-4 w-4" />
                        Add Steps
                      </Button>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="xml">
                  <div className="relative">
                    <div className="absolute top-3 right-3 z-10">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          const xmlContent = generateRecipeXML(recipe)
                          navigator.clipboard.writeText(xmlContent)
                          toast.success('XML copied to clipboard!')
                        }}
                        className="gap-2 text-xs bg-input border-border text-foreground hover:bg-accent hover:text-accent-foreground"
                      >
                        <Copy className="h-3 w-3" />
                        Copy XML
                      </Button>
                    </div>
                    <pre className="bg-muted/30 border border-border rounded-lg p-4 text-sm text-foreground overflow-x-auto max-h-[600px] overflow-y-auto">
                      <code className="language-xml">
                        {generateRecipeXML(recipe)}
                      </code>
                    </pre>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Recipe Info & Settings */}
        <div className="space-y-6">
          {/* Recipe Information */}
          <Card className="workflow-card bg-card border-2 border-card-border">
            <CardHeader>
              <CardTitle className="text-foreground">Recipe Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                {recipe.complexity_level && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground">Complexity</span>
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${getComplexityColor(recipe.complexity_level)}`} />
                      <span className="text-sm capitalize text-foreground">{recipe.complexity_level}</span>
                    </div>
                  </div>
                )}
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Status</span>
                  <Badge 
                    variant={recipe.status === 'active' ? 'default' : 'secondary'} 
                    className={`capitalize text-white font-medium ${
                      recipe.status === 'active' ? 'bg-green-600 hover:bg-green-700' : 
                      recipe.status === 'pending' ? 'bg-yellow-600 hover:bg-yellow-700' : 
                      'bg-muted hover:bg-muted/80'
                    }`}
                  >
                    {recipe.status}
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Usage Count</span>
                  <div className="text-right">
                    <span className="text-sm text-foreground font-medium">{recipe.usage_count || 0}</span>
                    <div className="text-xs text-muted-foreground">times executed</div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Recipe ID</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-foreground font-mono">#{recipe.id}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground hover:bg-accent"
                      onClick={() => {
                        navigator.clipboard.writeText(recipe.id.toString())
                        toast.success('ID copied!')
                      }}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
              
              <div className="pt-4 border-t border-border space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Updated</span>
                  <div className="text-right">
                    <span className="text-sm text-foreground">{new Date(recipe.updated_at).toLocaleDateString()}</span>
                    <div className="text-xs text-muted-foreground">
                      {Math.floor((Date.now() - new Date(recipe.updated_at).getTime()) / (1000 * 60 * 60 * 24))} days ago
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Created</span>
                  <div className="text-right">
                    <span className="text-sm text-foreground">
                      {new Date(recipe.created_at).toLocaleDateString()}
                    </span>
                    <div className="text-xs text-muted-foreground">
                      {Math.floor((Date.now() - new Date(recipe.created_at).getTime()) / (1000 * 60 * 60 * 24))} days ago
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Quick Actions */}
              <div className="pt-4 border-t border-border">
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      // TODO: Implement duplicate functionality
                      toast.info('Duplicate recipe coming soon!')
                    }}
                    className="gap-2 text-xs bg-input border-border text-foreground hover:bg-accent hover:text-accent-foreground"
                  >
                    <Copy className="h-3 w-3" />
                    Duplicate
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const url = window.location.href
                      navigator.clipboard.writeText(url)
                      toast.success('URL copied!')
                    }}
                    className="gap-2 text-xs bg-input border-border text-foreground hover:bg-accent hover:text-accent-foreground"
                  >
                    <Share className="h-3 w-3" />
                    Share
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Export Settings */}
          <Card className="workflow-card bg-card border-2 border-card-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-foreground">
                <Download className="h-4 w-4" />
                Export Recipe
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Export to different workflow formats
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Export Format
                </label>
                <Select value={selectedFormat} onValueChange={setSelectedFormat}>
                  <SelectTrigger className="bg-input border-border text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-popover border-border">
                    {SUPPORTED_FORMATS.map((format) => (
                      <SelectItem 
                        key={format.value} 
                        value={format.value}
                        className="text-foreground hover:bg-accent focus:bg-accent"
                      >
                        <div>
                          <div className="font-medium text-foreground">{format.label}</div>
                          <div className="text-xs text-muted-foreground">{format.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <Button
                onClick={handleExportRecipe}
                disabled={isExporting}
                className="w-full gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                variant="outline"
              >
                {isExporting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                {isExporting ? 'Compiling...' : 'Export Recipe'}
              </Button>
            </CardContent>
          </Card>

          {/* Required Tools */}
          {tools.length > 0 && (
            <Card className="workflow-card bg-card border-2 border-card-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-foreground">
                  <Zap className="h-4 w-4" />
                  Required Tools
                </CardTitle>
                <CardDescription className="text-muted-foreground">
                  Tools needed for recipe execution
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {tools.map((tool) => (
                  <div
                    key={tool.id}
                    className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg border border-border cursor-pointer hover:border-primary/50"
                    onClick={() => router.push(`/tools/${tool.id}`)}
                  >
                    <div className="flex-1">
                      <h4 className="font-medium text-foreground text-sm">{tool.nl_query}</h4>
                      <p className="text-xs text-muted-foreground capitalize">{tool.template_type}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {tool.health_status && (
                        <div
                          className={`w-2 h-2 rounded-full ${
                            tool.health_status === 'healthy' ? 'bg-green-500' :
                            tool.health_status === 'degraded' ? 'bg-yellow-500' :
                            tool.health_status === 'unhealthy' ? 'bg-red-500' :
                            'bg-muted'
                          }`}
                        />
                      )}
                      <ExternalLink className="h-3 w-3 text-muted-foreground" />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}