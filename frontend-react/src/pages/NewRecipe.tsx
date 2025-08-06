import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { Badge } from '../components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import { CatalogSelect } from '../components/ui/CatalogSelect'
import {
  ArrowLeft,
  Plus,
  Save,
  Loader2,
  RefreshCw,
  Trash2,
  AlertCircle,
  Sparkles,
} from 'lucide-react'
import api from '../services/api'

interface RecipeStep {
  id: string
  name: string
  type: string
  depends_on: string[]
}

interface RecipeFormData {
  nl_query: string
  template_type: string
  complexity_level: string
  execution_time_estimate: number
  catalog_type: string
  catalog_subtype: string
  catalog_name: string
  recipe_steps: RecipeStep[]
  required_tools: number[]
}

const STORAGE_KEY = 'recipe-form-draft'

export default function NewRecipe() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [analysisResults, setAnalysisResults] = useState<any>(null)
  const [formData, setFormData] = useState<RecipeFormData>({
    nl_query: '',
    template_type: 'recipe',
    complexity_level: 'easy', // Changed from 'beginner' to 'easy'
    execution_time_estimate: 10, // Default to 10 minutes
    catalog_type: '',
    catalog_subtype: '',
    catalog_name: '',
    recipe_steps: [] as RecipeStep[],
    required_tools: [] as number[],
  })

  // Load saved form data on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsedData = JSON.parse(saved)
        setFormData(parsedData)
        setHasUnsavedChanges(true)
        toast.success('Restored your previous draft')
      } catch (error) {
        console.error('Failed to restore saved form data:', error)
        localStorage.removeItem(STORAGE_KEY)
      }
    }
  }, [])

  // Save form data to localStorage on changes
  useEffect(() => {
    const timer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(formData))
    }, 1000) // Debounce saves
    
    return () => clearTimeout(timer)
  }, [formData])

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?'
        return 'You have unsaved changes. Are you sure you want to leave?'
      }
    }

    if (hasUnsavedChanges) {
      window.addEventListener('beforeunload', handleBeforeUnload)
      return () => window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [hasUnsavedChanges])

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
      localStorage.removeItem(STORAGE_KEY) // Clear saved draft
      setHasUnsavedChanges(false)
      navigate(`/recipes/${createdRecipe.id}`)
    } catch (error: any) {
      toast.error(`Failed to create recipe: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // AI-powered recipe analysis
  const handleAnalyzeRecipe = async () => {
    if (!formData.nl_query.trim()) {
      toast.error('Please enter a recipe description first')
      return
    }

    setAnalyzing(true)
    try {
      const analysisResponse = await fetch('http://localhost:8000/v1/recipes/analyze-natural-language', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipe_text: formData.nl_query,
          recipe_name: formData.nl_query,
          similarity_threshold: 0.6,
          max_matches_per_step: 5,
          catalog_type: formData.catalog_type || 'tmforum',
          catalog_subtype: formData.catalog_subtype || 'openai'
        })
      })

      if (!analysisResponse.ok) {
        throw new Error('Analysis failed')
      }

      const analysis = await analysisResponse.json()
      setAnalysisResults(analysis)
      
      // Auto-populate form with analysis results
      if (analysis.steps && analysis.steps.length > 0) {
        const generatedSteps = analysis.steps.map((step: any, index: number) => ({
          id: `step-${index + 1}`,
          name: step.name,
          type: step.step_type || 'action',
          depends_on: []
        }))
        
        setFormData(prev => ({
          ...prev,
          recipe_steps: generatedSteps,
          complexity_level: analysis.complexity_score > 0.7 ? 'hard' : analysis.complexity_score > 0.4 ? 'medium' : 'easy'
        }))
      }
      
      toast.success(`Analysis complete! Found ${analysis.total_steps} steps`)
      setHasUnsavedChanges(true)
    } catch (error: any) {
      toast.error(`Analysis failed: ${error.message}`)
      console.error('Analysis error:', error)
    } finally {
      setAnalyzing(false)
    }
  }

  // Clear form and start over
  const handleClearForm = () => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm('Are you sure you want to clear all form data? This cannot be undone.')
      if (!confirmed) return
    }
    
    setFormData({
      nl_query: '',
      template_type: 'recipe',
      complexity_level: 'easy',
      execution_time_estimate: 10,
      catalog_type: '',
      catalog_subtype: '',
      catalog_name: '',
      recipe_steps: [],
      required_tools: [],
    })
    setAnalysisResults(null)
    localStorage.removeItem(STORAGE_KEY)
    setHasUnsavedChanges(false)
    toast.success('Form cleared')
  }

  // Update form data and mark as changed
  const updateFormData = (updates: Partial<RecipeFormData>) => {
    setFormData(prev => ({ ...prev, ...updates }))
    setHasUnsavedChanges(true)
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/recipes')}
            className="hover:bg-neutral-700"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold text-white">Create New Recipe</h1>
            <p className="text-neutral-400 mt-1">Multi-step automation workflow</p>
          </div>
        </div>
        <Button onClick={handleSubmit} disabled={loading} className="gap-2">
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {loading ? 'Creating...' : 'Create Recipe'}
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <CardTitle className="text-white">Basic Information</CardTitle>
            <CardDescription className="text-neutral-300">
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
                onChange={(e) => updateFormData({ nl_query: e.target.value })}
                placeholder="Enter a descriptive name for your recipe..."
                className="bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400"
                required
              />
            </div>

            {/* Recipe Description with AI Analysis */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-neutral-300">
                  Recipe Description
                </label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAnalyzeRecipe}
                    disabled={analyzing || !formData.nl_query.trim()}
                    className="gap-2 border-emerald-600 text-emerald-300 hover:bg-emerald-900/20"
                  >
                    {analyzing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                    {analyzing ? 'Analyzing...' : 'Analyze with AI'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleClearForm}
                    className="gap-2 border-red-600 text-red-300 hover:bg-red-900/20"
                  >
                    <Trash2 className="h-4 w-4" />
                    Clear All
                  </Button>
                </div>
              </div>
              <Textarea
                value={formData.nl_query}
                onChange={(e) => updateFormData({ nl_query: e.target.value })}
                placeholder="Describe what you want your recipe to do. For example: 'can you listen To Topic Delete Event'"
                className="bg-neutral-900 border-neutral-700 text-white placeholder:text-neutral-400 min-h-[120px]"
                rows={4}
              />
              {hasUnsavedChanges && (
                <div className="flex items-center gap-2 mt-2 text-xs text-amber-400">
                  <AlertCircle className="h-3 w-3" />
                  Draft saved automatically
                </div>
              )}
              {analysisResults && (
                <div className="mt-3 p-3 bg-emerald-900/20 border border-emerald-700 rounded-md">
                  <div className="flex items-center gap-2 text-emerald-300 text-sm font-medium mb-2">
                    <Sparkles className="h-4 w-4" />
                    Analysis Results
                  </div>
                  <div className="text-xs text-neutral-300">
                    <p>✅ Found {analysisResults.total_steps || 0} steps</p>
                    <p>✅ Complexity: {formData.complexity_level}</p>
                    <p>✅ Estimated time: ~{analysisResults.estimated_duration || 2} minutes</p>
                    {analysisResults.steps?.[0]?.suggestions && (
                      <p>💡 {analysisResults.steps[0].suggestions[0]}</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Recipe Type
                </label>
                <Select
                  value={formData.template_type}
                  onValueChange={(value) => updateFormData({ template_type: value })}
                >
                  <SelectTrigger className="bg-neutral-900 border-neutral-700 text-white">
                    <SelectValue placeholder="Select recipe type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="recipe">Complete Recipe</SelectItem>
                    <SelectItem value="recipe_step">Recipe Step</SelectItem>
                    <SelectItem value="recipe_template">Recipe Template</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Complexity Level
                </label>
                <Select
                  value={formData.complexity_level}
                  onValueChange={(value) => updateFormData({ complexity_level: value })}
                >
                  <SelectTrigger className="bg-neutral-900 border-neutral-700 text-white">
                    <SelectValue placeholder="Select complexity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="easy">Easy</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="hard">Hard</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>



            <div className="grid grid-cols-3 gap-4">
              <div>
                <CatalogSelect
                  catalogField="catalog_type"
                  label="Catalog Type"
                  value={formData.catalog_type}
                  onValueChange={(value) => updateFormData({ catalog_type: value || "", catalog_subtype: "", catalog_name: "" })}
                  placeholder="e.g., workflow, automation"
                  className="bg-neutral-900 border-neutral-700 text-white"
                  allowCustom={true}
                />
              </div>

              <div>
                <CatalogSelect
                  catalogField="catalog_subtype"
                  label="Catalog Subtype"
                  value={formData.catalog_subtype}
                  onValueChange={(value) => updateFormData({ catalog_subtype: value || "", catalog_name: "" })}
                  placeholder="e.g., data-processing, api-integration"
                  className="bg-neutral-900 border-neutral-700 text-white"
                  allowCustom={true}
                />
              </div>

              <div>
                <CatalogSelect
                  catalogField="catalog_name"
                  label="Catalog Name"
                  value={formData.catalog_name}
                  onValueChange={(value) => updateFormData({ catalog_name: value || "" })}
                  placeholder="e.g., customer-data-pipeline"
                  className="bg-neutral-900 border-neutral-700 text-white"
                  allowCustom={true}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recipe Steps */}
        <Card className="bg-neutral-800 border-neutral-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-white">Recipe Steps</CardTitle>
                <CardDescription className="text-neutral-300">
                  Define the steps that make up your recipe
                </CardDescription>
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
          </CardHeader>
          <CardContent className="space-y-4">
            {formData.recipe_steps.length === 0 ? (
              <div className="text-center py-8 text-neutral-400">
                <p>No steps added yet. Click "Add Step" to get started.</p>
              </div>
            ) : (
              formData.recipe_steps.map((step, index) => (
                <Card key={step.id} className="bg-neutral-900 border-neutral-600">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <Badge variant="secondary" className="bg-neutral-700 text-neutral-300">
                        Step {index + 1}
                      </Badge>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeStep(index)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                      >
                        Remove
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-300 mb-2">
                          Step Name
                        </label>
                        <Input
                          value={step.name}
                          onChange={(e) => updateStep(index, 'name', e.target.value)}
                          placeholder="Enter step name..."
                          className="bg-neutral-800 border-neutral-600 text-white placeholder:text-neutral-400"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-300 mb-2">
                          Step Type
                        </label>
                        <Select
                          value={step.type}
                          onValueChange={(value) => updateStep(index, 'type', value)}
                        >
                          <SelectTrigger className="bg-neutral-800 border-neutral-600 text-white">
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="action">Action</SelectItem>
                            <SelectItem value="condition">Condition</SelectItem>
                            <SelectItem value="transform">Transform</SelectItem>
                            <SelectItem value="validate">Validate</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/recipes')}
            className="border-neutral-600 text-neutral-300 hover:bg-neutral-700"
          >
            Cancel
          </Button>
          <Button type="submit" disabled={loading} className="gap-2">
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {loading ? 'Creating...' : 'Create Recipe'}
          </Button>
        </div>
      </form>
    </div>
  )
} 