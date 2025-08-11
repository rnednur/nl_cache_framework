'use client'

import { useState, useCallback } from 'react'
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
import { Textarea } from '@/app/components/ui/textarea'
import { Badge } from '@/app/components/ui/badge'
import { Progress } from '@/app/components/ui/progress'
import { Alert, AlertDescription } from '@/app/components/ui/alert'
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
  Plus,
  Save,
  ChefHat,
  Layers,
  BookOpen,
  Trash2,
  Loader2,
  Wand2,
  FileText,
  CheckCircle,
  AlertTriangle,
  Target,
  Eye,
  ExternalLink,
  PlusCircle,
  AlertCircle,
  Edit3,
  RefreshCw,
  X,
} from 'lucide-react'
import api from '@/app/services/api'

const RECIPE_TYPES = {
  recipe: { label: 'Complete Recipe', icon: ChefHat, description: 'Multi-step automation workflow' },
  recipe_step: { label: 'Recipe Step', icon: Layers, description: 'Reusable workflow component' },
  recipe_template: { label: 'Recipe Template', icon: BookOpen, description: 'Parameterized workflow pattern' },
} as const

const COMPLEXITY_LEVELS = ['beginner', 'intermediate', 'advanced'] as const

interface RecipeStep {
  id: string
  name: string
  type: string
  description?: string
  tool_id?: number
  depends_on?: string[]
  confidence?: number
  actionVerbs?: string[]
  entities?: string[]
  mappedTool?: {
    id: number
    name: string
    type: string
    confidence: number
    reasoning: string
  }
}

interface ParsedRecipeStep {
  id: string
  name: string
  description: string
  stepType: string
  confidence: number
  actionVerbs: string[]
  entities: string[]
  mappedTool?: {
    id: number | null
    cacheEntryId: number | null
    name: string
    type: string
    confidence: number
    reasoning: string
    exists: boolean
    needsCreation: boolean
  }
}

interface RecipeAnalysis {
  recipeName: string
  description: string
  steps: ParsedRecipeStep[]
  totalSteps: number
  complexityScore: number
  estimatedDuration: number
  requiredCapabilities: string[]
  recipeType: string
}

export default function NewRecipe() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'natural' | 'manual'>('natural')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isMapping, setIsMapping] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [analysisResult, setAnalysisResult] = useState<RecipeAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [naturalLanguageText, setNaturalLanguageText] = useState('')
  const [rewritingStepId, setRewritingStepId] = useState<string | null>(null)
  const [rewriteText, setRewriteText] = useState('')
  const [isRewriting, setIsRewriting] = useState(false)
  
  const [formData, setFormData] = useState({
    nl_query: '',
    template: '{}',
    template_type: 'recipe' as keyof typeof RECIPE_TYPES,
    complexity_level: 'beginner' as typeof COMPLEXITY_LEVELS[number],
    execution_time_estimate: 0,
    catalog_type: '',
    catalog_subtype: '',
    catalog_name: '',
    recipe_steps: [] as RecipeStep[],
    required_tools: [] as number[],
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.nl_query.trim()) {
      toast.error('Recipe name is required')
      return
    }

    setLoading(true)
    try {
      // Prepare the recipe data
      const recipeData = {
        nl_query: formData.nl_query,
        template: JSON.stringify({
          recipe_metadata: {
            name: formData.nl_query,
            description: formData.nl_query,
            complexity_level: formData.complexity_level,
            catalog_type: formData.catalog_type,
            catalog_subtype: formData.catalog_subtype,
            catalog_name: formData.catalog_name,
          },
          steps: formData.recipe_steps,
          execution_config: {
            timeout_seconds: formData.execution_time_estimate * 60,
            parallel_limit: 5,
            fail_fast: true,
          },
        }),
        template_type: formData.template_type,
        is_template: true,
        complexity_level: formData.complexity_level,
        execution_time_estimate: formData.execution_time_estimate,
        catalog_type: formData.catalog_type,
        catalog_subtype: formData.catalog_subtype,
        catalog_name: formData.catalog_name,
        recipe_steps: formData.recipe_steps,
        required_tools: formData.required_tools,
        status: 'active',
      }

      const createdRecipe = await api.createCacheEntry(recipeData)
      toast.success('Recipe created successfully!')
      router.push(`/recipes/${createdRecipe.id}`)
    } catch (error: any) {
      toast.error(`Failed to create recipe: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const addStep = () => {
    const newStep: RecipeStep = {
      id: `step_${Date.now()}`,
      name: '',
      type: 'action',
      depends_on: [],
    }
    setFormData(prev => ({
      ...prev,
      recipe_steps: [...prev.recipe_steps, newStep],
    }))
  }

  const updateStep = (index: number, field: keyof RecipeStep, value: any) => {
    setFormData(prev => ({
      ...prev,
      recipe_steps: prev.recipe_steps.map((step, i) => 
        i === index ? { ...step, [field]: value } : step
      ),
    }))
  }

  const removeStep = (index: number) => {
    setFormData(prev => ({
      ...prev,
      recipe_steps: prev.recipe_steps.filter((_, i) => i !== index),
    }))
  }

  const analyzeNaturalLanguage = async () => {
    if (!naturalLanguageText.trim()) {
      setError('Please enter a recipe description')
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setAnalysisProgress(0)

    try {
      // Start analysis
      setAnalysisProgress(25)
      
      // Call real API endpoint for recipe analysis
      const apiResponse = await api.analyzeRecipeText({
        recipe_text: naturalLanguageText,
        recipe_name: formData.nl_query || 'Generated Recipe',
        similarity_threshold: 0.6,
        max_matches_per_step: 5,
        catalog_type: formData.catalog_type || undefined,
        catalog_subtype: formData.catalog_subtype || undefined,
        catalog_name: formData.catalog_name || undefined
      })
      
      setAnalysisProgress(75)

      // Convert API response to frontend format
      const analysisResult: RecipeAnalysis = {
        recipeName: apiResponse.recipe_name,
        description: apiResponse.description,
        steps: apiResponse.steps.map(step => ({
          id: step.id,
          name: step.name,
          description: step.description,
          stepType: step.step_type,
          confidence: step.confidence,
          actionVerbs: step.action_verbs,
          entities: step.entities,
          mappedTool: step.mapped_tool ? {
            id: step.mapped_tool.id,
            cacheEntryId: step.mapped_tool.cache_entry_id,
            name: step.mapped_tool.name,
            type: step.mapped_tool.type,
            confidence: step.mapped_tool.confidence,
            reasoning: step.mapped_tool.reasoning,
            exists: step.mapped_tool.exists,
            needsCreation: step.mapped_tool.needs_creation
          } : undefined
        })),
        totalSteps: apiResponse.total_steps,
        complexityScore: apiResponse.complexity_score,
        estimatedDuration: apiResponse.estimated_duration,
        requiredCapabilities: apiResponse.required_capabilities,
        recipeType: apiResponse.recipe_type
      }

      setAnalysisProgress(100)
      setAnalysisResult(analysisResult)
      
      // Update form data with analysis results
      setFormData(prev => ({
        ...prev,
        execution_time_estimate: analysisResult.estimatedDuration,
        complexity_level: analysisResult.complexityScore > 0.7 ? 'advanced' : analysisResult.complexityScore > 0.4 ? 'intermediate' : 'beginner'
      }))

    } catch (err: any) {
      console.error('Recipe analysis failed:', err)
      setError(err.message || 'Failed to analyze recipe. Please try again.')
    } finally {
      setIsAnalyzing(false)
      setAnalysisProgress(0)
    }
  }

  const acceptAnalysisResult = useCallback(() => {
    if (!analysisResult) return

    const convertedSteps: RecipeStep[] = analysisResult.steps.map((step, index) => ({
      id: step.id,
      name: step.name,
      type: step.stepType,
      description: step.description,
      tool_id: step.mappedTool?.id,
      depends_on: index > 0 ? [analysisResult.steps[index - 1].id] : [],
      confidence: step.confidence,
      actionVerbs: step.actionVerbs,
      entities: step.entities,
      mappedTool: step.mappedTool
    }))

    setFormData(prev => ({
      ...prev,
      recipe_steps: convertedSteps,
      required_tools: convertedSteps.map(step => step.tool_id).filter(Boolean) as number[]
    }))

    // Switch to manual tab to show the converted steps
    setActiveTab('manual')
    toast.success('Recipe steps imported from natural language analysis!')
  }, [analysisResult])

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500 text-white border-green-500'
    if (confidence >= 0.6) return 'bg-yellow-500 text-black border-yellow-500'
    return 'bg-red-500 text-white border-red-500'
  }

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircle className="h-4 w-4 text-green-400" />
    if (confidence >= 0.6) return <AlertTriangle className="h-4 w-4 text-yellow-400" />
    return <AlertTriangle className="h-4 w-4 text-red-400" />
  }

  const handleCreateTool = async (stepId: string, toolData: any) => {
    try {
      // This would open a dialog to create the tool or navigate to tool creation
      // For now, we'll just show a toast
      toast.success(`Opening tool creation for: ${toolData.name}`)
      console.log('Create tool for step:', stepId, toolData)
    } catch (error) {
      toast.error('Failed to initiate tool creation')
    }
  }

  const handleViewTool = (cacheEntryId: number) => {
    // Navigate to tool detail view
    window.open(`/tools/${cacheEntryId}`, '_blank')
  }

  const handleRewriteStep = async (stepId: string, newDescription: string) => {
    if (!newDescription.trim()) {
      toast.error('Please enter a step description')
      return
    }

    setIsRewriting(true)
    try {
      const rewriteResponse = await api.rewriteRecipeStep({
        step_id: stepId,
        new_description: newDescription,
        similarity_threshold: 0.6,
        max_matches: 5,
        catalog_type: formData.catalog_type || undefined,
        catalog_subtype: formData.catalog_subtype || undefined,
        catalog_name: formData.catalog_name || undefined
      })

      // Update the analysis result with the rewritten step
      if (analysisResult) {
        const updatedSteps = analysisResult.steps.map(step => 
          step.id === stepId ? {
            ...rewriteResponse.rewritten_step,
            // Convert API response format to frontend format
            stepType: rewriteResponse.rewritten_step.step_type,
            actionVerbs: rewriteResponse.rewritten_step.action_verbs,
            mappedTool: rewriteResponse.rewritten_step.mapped_tool ? {
              ...rewriteResponse.rewritten_step.mapped_tool,
              cacheEntryId: rewriteResponse.rewritten_step.mapped_tool.cache_entry_id,
              needsCreation: rewriteResponse.rewritten_step.mapped_tool.needs_creation
            } : undefined
          } : step
        )

        setAnalysisResult({
          ...analysisResult,
          steps: updatedSteps
        })
      }

      // Reset rewrite state
      setRewritingStepId(null)
      setRewriteText('')
      
      toast.success('Step rewritten and reanalyzed successfully!')
    } catch (error: any) {
      toast.error(`Failed to rewrite step: ${error.message}`)
    } finally {
      setIsRewriting(false)
    }
  }

  const startRewriteStep = (stepId: string, currentDescription: string) => {
    setRewritingStepId(stepId)
    setRewriteText(currentDescription)
  }

  const cancelRewriteStep = () => {
    setRewritingStepId(null)
    setRewriteText('')
  }

  const getRecipeTypeIcon = (templateType: keyof typeof RECIPE_TYPES) => {
    const Icon = RECIPE_TYPES[templateType].icon
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
            onClick={() => router.push('/recipes')}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Recipes
          </Button>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-green-500">
              {getRecipeTypeIcon(formData.template_type)}
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white">Create New Recipe</h1>
              <p className="text-neutral-400">
                {RECIPE_TYPES[formData.template_type].description}
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
          {loading ? 'Creating...' : 'Create Recipe'}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Define the basic properties of your recipe
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Recipe Name *
              </label>
              <Input
                value={formData.nl_query}
                onChange={(e) => setFormData(prev => ({ ...prev, nl_query: e.target.value }))}
                placeholder="Enter a descriptive name for your recipe..."
                className="!bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Recipe Type
                </label>
                <Select
                  value={formData.template_type}
                  onValueChange={(value) => setFormData(prev => ({ 
                    ...prev, 
                    template_type: value as keyof typeof RECIPE_TYPES 
                  }))}
                >
                  <SelectTrigger className="!bg-neutral-900 border-neutral-700 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(RECIPE_TYPES).map(([key, type]) => (
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
                  Complexity Level
                </label>
                <Select
                  value={formData.complexity_level}
                  onValueChange={(value) => setFormData(prev => ({ 
                    ...prev, 
                    complexity_level: value as typeof COMPLEXITY_LEVELS[number]
                  }))}
                >
                  <SelectTrigger className="!bg-neutral-900 border-neutral-700 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COMPLEXITY_LEVELS.map((level) => (
                      <SelectItem key={level} value={level}>
                        <span className="capitalize">{level}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Estimated Execution Time (minutes)
              </label>
              <Input
                type="number"
                min="0"
                value={formData.execution_time_estimate}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  execution_time_estimate: parseInt(e.target.value) || 0 
                }))}
                placeholder="0"
                className="!bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Catalog Type
                </label>
                <Input
                  value={formData.catalog_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, catalog_type: e.target.value }))}
                  placeholder="e.g., workflow, automation"
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
                  placeholder="e.g., data-processing, api-integration"
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
                  placeholder="e.g., customer-data-pipeline"
                  className="!bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recipe Creation Methods */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <CardTitle>Recipe Creation</CardTitle>
            <CardDescription>
              Create your recipe using natural language or manual step building
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'natural' | 'manual')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="natural" className="flex items-center gap-2">
                  <Wand2 className="h-4 w-4" />
                  Natural Language
                </TabsTrigger>
                <TabsTrigger value="manual" className="flex items-center gap-2">
                  <Layers className="h-4 w-4" />
                  Manual Steps
                </TabsTrigger>
              </TabsList>

              <TabsContent value="natural" className="space-y-4 mt-6">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-neutral-300">
                    Recipe Description
                  </label>
                  <Textarea
                    value={naturalLanguageText}
                    onChange={(e) => setNaturalLanguageText(e.target.value)}
                    placeholder="Describe your recipe in natural language. For example:
1. Load customer data from the database
2. Transform the data to JSON format  
3. Validate data integrity
4. Send notification email to admin"
                    className="min-h-[120px] !bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={isAnalyzing}
                  />
                </div>

                {!analysisResult && (
                  <Button 
                    type="button"
                    onClick={analyzeNaturalLanguage} 
                    disabled={isAnalyzing || !naturalLanguageText.trim()}
                    className="w-full"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Analyzing Recipe...
                      </>
                    ) : (
                      <>
                        <Wand2 className="h-4 w-4 mr-2" />
                        Analyze Recipe
                      </>
                    )}
                  </Button>
                )}

                {isAnalyzing && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">Parsing recipe steps...</span>
                    </div>
                    <Progress value={analysisProgress} />
                  </div>
                )}

                {analysisResult && (
                  <div className="space-y-4 border-t border-neutral-700 pt-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-white">Analysis Results</h4>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="border-neutral-500 text-neutral-300">
                          {analysisResult.totalSteps} steps
                        </Badge>
                        <Badge variant="outline" className="border-neutral-500 text-neutral-300">
                          {analysisResult.recipeType}
                        </Badge>
                        <Badge variant="outline" className="border-neutral-500 text-neutral-300">
                          ~{analysisResult.estimatedDuration}min
                        </Badge>
                      </div>
                    </div>

                    {/* Tool Status Summary */}
                    <div className="bg-neutral-800 rounded-lg p-3 border border-neutral-600">
                      <h5 className="text-sm font-medium text-white mb-2">Tool Status Summary</h5>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-400" />
                          <span className="text-neutral-300">
                            {analysisResult.steps.filter(s => s.mappedTool?.exists).length} tools available
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <AlertCircle className="h-4 w-4 text-orange-400" />
                          <span className="text-neutral-300">
                            {analysisResult.steps.filter(s => s.mappedTool?.needsCreation).length} tools need creation
                          </span>
                        </div>
                      </div>
                      {analysisResult.steps.filter(s => s.mappedTool?.needsCreation).length > 0 && (
                        <div className="mt-2 text-xs text-orange-300">
                          ⚠️ Some tools will need to be created before this recipe can be fully executed
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="font-medium text-neutral-300">Complexity</p>
                        <div className="flex items-center gap-2">
                          <Progress value={analysisResult.complexityScore * 100} className="flex-1" />
                          <span className="text-white">{Math.round(analysisResult.complexityScore * 100)}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="font-medium text-neutral-300">Required Capabilities</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {analysisResult.requiredCapabilities.map((cap) => (
                            <Badge key={cap} variant="secondary" className="text-xs bg-neutral-700 text-neutral-200">
                              {cap}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="font-medium text-neutral-300">Duration</p>
                        <p className="text-lg font-semibold text-white">{analysisResult.estimatedDuration} min</p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h5 className="font-medium flex items-center gap-2 text-white">
                        <Target className="h-4 w-4 text-blue-400" />
                        Extracted Steps
                      </h5>
                      
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {analysisResult.steps.map((step, index) => (
                          <div key={step.id} className="border border-neutral-600 rounded-lg p-3 bg-neutral-800">
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-sm font-medium text-white">
                                    {index + 1}. {step.name}
                                  </span>
                                  <Badge variant="outline" className="text-xs border-neutral-500 text-neutral-300">
                                    {step.stepType}
                                  </Badge>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => startRewriteStep(step.id, step.description)}
                                    className="h-5 px-1 text-xs text-blue-400 hover:text-blue-300"
                                    disabled={rewritingStepId === step.id}
                                  >
                                    <Edit3 className="h-3 w-3" />
                                  </Button>
                                </div>
                                
                                {rewritingStepId === step.id ? (
                                  <div className="space-y-2 mb-2">
                                    <Textarea
                                      value={rewriteText}
                                      onChange={(e) => setRewriteText(e.target.value)}
                                      placeholder="Rewrite the step description..."
                                      className="min-h-[60px] text-xs !bg-neutral-900 border-neutral-600 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                      disabled={isRewriting}
                                    />
                                    <div className="flex gap-2">
                                      <Button
                                        type="button"
                                        size="sm"
                                        onClick={() => handleRewriteStep(step.id, rewriteText)}
                                        disabled={isRewriting || !rewriteText.trim()}
                                        className="h-6 px-2 text-xs"
                                      >
                                        {isRewriting ? (
                                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                        ) : (
                                          <RefreshCw className="h-3 w-3 mr-1" />
                                        )}
                                        {isRewriting ? 'Rewriting...' : 'Rewrite'}
                                      </Button>
                                      <Button
                                        type="button"
                                        size="sm"
                                        variant="ghost"
                                        onClick={cancelRewriteStep}
                                        disabled={isRewriting}
                                        className="h-6 px-2 text-xs text-neutral-400 hover:text-neutral-300"
                                      >
                                        <X className="h-3 w-3 mr-1" />
                                        Cancel
                                      </Button>
                                    </div>
                                  </div>
                                ) : (
                                  <p className="text-xs text-neutral-300 mb-2 line-clamp-2">
                                    {step.description}
                                  </p>
                                )}
                                
                                {step.mappedTool ? (
                                  <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                      <Target className="h-3 w-3 text-blue-400" />
                                      <span className="text-xs font-medium text-neutral-200">
                                        {step.mappedTool.name} ({step.mappedTool.type})
                                      </span>
                                      <Badge 
                                        className={`text-xs ${getConfidenceColor(step.mappedTool.confidence)}`}
                                      >
                                        {Math.round(step.mappedTool.confidence * 100)}%
                                      </Badge>
                                    </div>
                                    
                                    {step.mappedTool.exists ? (
                                      <div className="flex items-center gap-2">
                                        <CheckCircle className="h-3 w-3 text-green-400" />
                                        <span className="text-xs text-neutral-300">
                                          Cache Entry ID: {step.mappedTool.cacheEntryId}
                                        </span>
                                        <Button
                                          type="button"
                                          size="sm"
                                          variant="ghost"
                                          onClick={() => handleViewTool(step.mappedTool!.cacheEntryId!)}
                                          className="h-6 px-2 text-xs text-blue-400 hover:text-blue-300"
                                        >
                                          <ExternalLink className="h-3 w-3 mr-1" />
                                          View Tool
                                        </Button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center gap-2">
                                        <AlertCircle className="h-3 w-3 text-orange-400" />
                                        <span className="text-xs text-orange-300">
                                          Tool needs to be created
                                        </span>
                                        <Button
                                          type="button"
                                          size="sm"
                                          variant="ghost"
                                          onClick={() => handleCreateTool(step.id, step.mappedTool)}
                                          className="h-6 px-2 text-xs text-orange-400 hover:text-orange-300"
                                        >
                                          <PlusCircle className="h-3 w-3 mr-1" />
                                          Create Tool
                                        </Button>
                                      </div>
                                    )}
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-2 text-neutral-400">
                                    <AlertTriangle className="h-3 w-3" />
                                    <span className="text-xs">No tool mapped</span>
                                  </div>
                                )}
                              </div>
                              
                              <div className="flex items-center gap-2">
                                {step.mappedTool && getConfidenceIcon(step.mappedTool.confidence)}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        type="button"
                        onClick={acceptAnalysisResult}
                        className="flex-1"
                      >
                        <Eye className="h-4 w-4 mr-2" />
                        Import Steps to Manual Editor
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setAnalysisResult(null)}
                        className="border-neutral-600"
                      >
                        Analyze Different Recipe
                      </Button>
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="manual" className="space-y-4 mt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Manual Step Builder</h4>
                    <p className="text-sm text-neutral-400">
                      Add and configure individual recipe steps
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addStep}
                    className="gap-2 border-neutral-600 text-neutral-300 hover:bg-neutral-700"
                  >
                    <Plus className="h-4 w-4" />
                    Add Step
                  </Button>
                </div>

                {formData.recipe_steps.length === 0 ? (
                  <div className="text-center py-8 text-neutral-400">
                    <Layers className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No steps added yet. Click "Add Step" to get started.</p>
                    {activeTab === 'manual' && (
                      <p className="text-xs mt-2">
                        Tip: Try the "Natural Language" tab for AI-powered step extraction!
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {formData.recipe_steps.map((step, index) => (
                      <div
                        key={step.id}
                        className="flex items-start gap-4 p-4 bg-neutral-900 rounded-lg border border-neutral-700"
                      >
                        <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-sm font-semibold">
                          {index + 1}
                        </div>
                        <div className="flex-1 space-y-3">
                          <div className="grid grid-cols-2 gap-4">
                            <Input
                              placeholder="Step name..."
                              value={step.name}
                              onChange={(e) => updateStep(index, 'name', e.target.value)}
                              className="!bg-neutral-800 border-neutral-600 text-white placeholder:text-neutral-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <Select
                              value={step.type}
                              onValueChange={(value) => updateStep(index, 'type', value)}
                            >
                              <SelectTrigger className="!bg-neutral-800 border-neutral-600 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="action">Action</SelectItem>
                                <SelectItem value="condition">Condition</SelectItem>
                                <SelectItem value="loop">Loop</SelectItem>
                                <SelectItem value="transform">Transform</SelectItem>
                                <SelectItem value="validation">Validation</SelectItem>
                                <SelectItem value="integration">Integration</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          
                          {step.description && (
                            <div className="text-xs text-neutral-400 bg-neutral-800 p-2 rounded border border-neutral-600">
                              {step.description}
                            </div>
                          )}
                          
                          {step.mappedTool && (
                            <div className="space-y-1">
                              <div className="flex items-center gap-2 text-xs">
                                <Target className="h-3 w-3 text-blue-400" />
                                <span className="text-neutral-300">Mapped to: {step.mappedTool.name}</span>
                                <Badge className={`text-xs ${getConfidenceColor(step.mappedTool.confidence)}`}>
                                  {Math.round(step.mappedTool.confidence * 100)}%
                                </Badge>
                              </div>
                              {step.mappedTool.exists ? (
                                <div className="flex items-center gap-2 text-xs">
                                  <CheckCircle className="h-3 w-3 text-green-400" />
                                  <span className="text-neutral-400">
                                    Cache Entry ID: {step.mappedTool.cacheEntryId}
                                  </span>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleViewTool(step.mappedTool!.cacheEntryId!)}
                                    className="h-5 px-1 text-xs text-blue-400 hover:text-blue-300"
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                  </Button>
                                </div>
                              ) : (
                                <div className="flex items-center gap-2 text-xs">
                                  <AlertCircle className="h-3 w-3 text-orange-400" />
                                  <span className="text-orange-300">Needs creation</span>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleCreateTool(step.id, step.mappedTool)}
                                    className="h-5 px-1 text-xs text-orange-400 hover:text-orange-300"
                                  >
                                    <PlusCircle className="h-3 w-3" />
                                  </Button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeStep(index)}
                          className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </form>
    </div>
  )
}