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
  const [activeTab, setActiveTab] = useState<'overview' | 'settings'>('overview')
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
    return RECIPE_TYPES[templateType as keyof typeof RECIPE_TYPES]?.color || 'bg-neutral-500'
  }

  const getComplexityColor = (complexity?: string) => {
    return COMPLEXITY_COLORS[complexity as keyof typeof COMPLEXITY_COLORS] || 'bg-neutral-500'
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/recipes')}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-lg ${getRecipeTypeColor(recipe.template_type)}`}>
              {getRecipeIcon(recipe.template_type)}
            </div>
            <div>
              {isEditingName ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={editedName}
                    onChange={(e) => setEditedName(e.target.value)}
                    className="text-xl font-semibold bg-neutral-900 border-neutral-700"
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
                <div className="flex items-center gap-2 group">
                  <h1 className="text-2xl font-semibold text-white">{recipe.nl_query}</h1>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsEditingName(true)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-auto"
                  >
                    <Edit className="h-3 w-3" />
                  </Button>
                </div>
              )}
              <p className="text-neutral-400 capitalize">
                {RECIPE_TYPES[recipe.template_type as keyof typeof RECIPE_TYPES]?.label || recipe.template_type}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => router.push(`/recipes/new?edit=${recipe.id}`)}
            className="gap-2 border-neutral-600 text-neutral-300 hover:bg-neutral-700"
          >
            <Edit className="h-4 w-4" />
            Edit
          </Button>
        </div>
      </div>

      {/* Recipe Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {recipe.recipe_steps?.length || 0}
              </div>
              <div className="text-sm text-neutral-400">Steps</div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {recipe.usage_count || 0}
              </div>
              <div className="text-sm text-neutral-400">Usage Count</div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {new Date(recipe.created_at).toLocaleDateString()}
              </div>
              <div className="text-sm text-neutral-400">Created</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recipe Details with Tabs */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recipe Steps */}
            <div className="lg:col-span-2">
              <Card className="bg-neutral-800 border-neutral-700">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Layers className="h-5 w-5" />
                    Recipe Steps
                  </CardTitle>
                  <CardDescription>
                    Workflow execution steps in order
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {recipe.recipe_steps && recipe.recipe_steps.length > 0 ? (
                    recipe.recipe_steps.map((step, index) => (
                      <div
                        key={step.id}
                        className="flex items-center gap-4 p-4 bg-neutral-900 rounded-lg border border-neutral-700"
                      >
                        <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-sm font-semibold">
                          {index + 1}
                        </div>
                        <div className="flex-1">
                          <h4 className="font-medium text-white">{step.name}</h4>
                          <p className="text-sm text-neutral-400 capitalize">{step.type}</p>
                          {step.depends_on && step.depends_on.length > 0 && (
                            <div className="mt-2">
                              <span className="text-xs text-neutral-500">Depends on: </span>
                              {step.depends_on.map((dep, i) => (
                                <Badge key={i} variant="outline" className="text-xs ml-1 border-neutral-600">
                                  Step {dep}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                        {step.tool_id && (
                          <div className="flex-shrink-0">
                            <Badge variant="secondary" className="bg-neutral-700 text-neutral-300">
                              Tool #{step.tool_id}
                            </Badge>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-neutral-400">
                      No steps defined for this recipe
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Recipe Info & Tools */}
            <div className="space-y-6">
              {/* Recipe Information */}
              <Card className="bg-neutral-800 border-neutral-700">
                <CardHeader>
                  <CardTitle>Recipe Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {recipe.complexity_level && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-400">Complexity</span>
                      <div className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${getComplexityColor(recipe.complexity_level)}`} />
                        <span className="text-sm capitalize text-white">{recipe.complexity_level}</span>
                      </div>
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-400">Status</span>
                    <Badge variant={recipe.status === 'valid' ? 'default' : 'destructive'} className="capitalize">
                      {recipe.status}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-400">Usage Count</span>
                    <span className="text-sm text-white">{recipe.usage_count || 0}</span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-400">Updated</span>
                    <span className="text-sm text-white">{new Date(recipe.updated_at).toLocaleDateString()}</span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-400">Created</span>
                    <span className="text-sm text-white">
                      {new Date(recipe.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Required Tools */}
              {tools.length > 0 && (
                <Card className="bg-neutral-800 border-neutral-700">
                  <CardHeader>
                    <CardTitle>Required Tools</CardTitle>
                    <CardDescription>
                      Tools needed for recipe execution
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {tools.map((tool) => (
                      <div
                        key={tool.id}
                        className="flex items-center gap-3 p-3 bg-neutral-900 rounded-lg border border-neutral-700 cursor-pointer hover:border-neutral-600"
                        onClick={() => router.push(`/tools/${tool.id}`)}
                      >
                        <div className="flex-1">
                          <h4 className="font-medium text-white text-sm">{tool.nl_query}</h4>
                          <p className="text-xs text-neutral-400 capitalize">{tool.template_type}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          {tool.health_status && (
                            <div
                              className={`w-2 h-2 rounded-full ${
                                tool.health_status === 'healthy' ? 'bg-green-500' :
                                tool.health_status === 'degraded' ? 'bg-yellow-500' :
                                tool.health_status === 'unhealthy' ? 'bg-red-500' :
                                'bg-neutral-500'
                              }`}
                            />
                          )}
                          <ExternalLink className="h-3 w-3 text-neutral-400" />
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>


        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recipe Settings */}
            <Card className="bg-neutral-800 border-neutral-700">
              <CardHeader>
                <CardTitle>Recipe Settings</CardTitle>
                <CardDescription>
                  Configure recipe behavior and metadata
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Description
                  </label>
                  {isEditingDescription ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editedDescription}
                        onChange={(e) => setEditedDescription(e.target.value)}
                        className="bg-neutral-900 border-neutral-700"
                        placeholder="Enter recipe description..."
                        rows={4}
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleSaveInlineEdit('description')}
                          disabled={isSaving}
                        >
                          {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCancelInlineEdit('description')}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="group">
                      <div className="p-3 bg-neutral-900 rounded-lg border border-neutral-700 min-h-[100px] relative">
                        <p className="text-sm text-neutral-300 whitespace-pre-wrap">
                          {recipe.template || 'No description provided'}
                        </p>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setIsEditingDescription(true)}
                          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 h-auto"
                        >
                          <Edit className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-300 mb-2">
                      Complexity Level
                    </label>
                    <Select value={recipe.complexity_level || 'easy'} onValueChange={() => {}}>
                      <SelectTrigger className="bg-neutral-900 border-neutral-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="easy">Easy</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="hard">Hard</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-neutral-300 mb-2">
                      Status
                    </label>
                    <Select value={recipe.status || 'active'} onValueChange={() => {}}>
                      <SelectTrigger className="bg-neutral-900 border-neutral-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="archived">Archived</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Export Settings */}
            <Card className="bg-neutral-800 border-neutral-700">
              <CardHeader>
                <CardTitle>Export & Integration</CardTitle>
                <CardDescription>
                  Export recipe to different workflow formats
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select value={selectedFormat} onValueChange={setSelectedFormat}>
                  <SelectTrigger className="bg-neutral-900 border-neutral-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SUPPORTED_FORMATS.map((format) => (
                      <SelectItem key={format.value} value={format.value}>
                        <div>
                          <div className="font-medium">{format.label}</div>
                          <div className="text-xs text-neutral-400">{format.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Button
                  onClick={handleExportRecipe}
                  disabled={isExporting}
                  className="w-full gap-2"
                  variant="outline"
                >
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  {isExporting ? 'Compiling...' : 'Export Recipe'}
                </Button>

                <div className="text-xs text-neutral-500 mt-2">
                  Exported workflows can be imported into compatible platforms for execution.
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}