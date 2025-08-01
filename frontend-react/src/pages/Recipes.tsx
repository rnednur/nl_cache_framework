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
import { Badge } from '../components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  Search,
  Plus,
  Play,
  Settings,
  ChefHat,
  ListChecks,
  FileTemplate,
  Clock,
  Filter,
  Loader2,
  Users,
  TrendingUp,
  AlertCircle,
} from 'lucide-react'
import { api } from '../services/api'

interface Recipe {
  id: number
  nl_query: string
  template: string
  template_type: string
  recipe_steps?: Array<{
    id: string
    name: string
    type: string
    tool_id?: number
    depends_on?: string[]
  }>
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

const RECIPE_TYPES = {
  recipe: { label: 'Complete Recipe', icon: ChefHat, color: 'bg-purple-500' },
  recipe_step: { label: 'Recipe Step', icon: ListChecks, color: 'bg-blue-500' },
  recipe_template: { label: 'Recipe Template', icon: FileTemplate, color: 'bg-green-500' },
} as const

const COMPLEXITY_COLORS = {
  beginner: 'bg-green-500',
  intermediate: 'bg-yellow-500',
  advanced: 'bg-red-500',
} as const

const SUCCESS_RATE_COLOR = (rate?: number) => {
  if (!rate) return 'bg-gray-500'
  if (rate >= 90) return 'bg-green-500'
  if (rate >= 70) return 'bg-yellow-500'
  return 'bg-red-500'
}

export default function Recipes() {
  const navigate = useNavigate()
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [selectedComplexity, setSelectedComplexity] = useState<string>('all')
  const [filteredRecipes, setFilteredRecipes] = useState<Recipe[]>([])

  useEffect(() => {
    fetchRecipes()
  }, [])

  useEffect(() => {
    filterRecipes()
  }, [recipes, searchQuery, selectedType, selectedComplexity])

  const fetchRecipes = async () => {
    setLoading(true)
    setError(null)
    try {
      // Filter for recipe-specific template types
      const recipeTypes = ['recipe', 'recipe_step', 'recipe_template']
      const response = await api.getCacheEntries(1, 100, {
        template_type: recipeTypes.join(',')
      })
      setRecipes(response.items)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch recipes')
      toast.error('Failed to load recipes')
    } finally {
      setLoading(false)
    }
  }

  const filterRecipes = () => {
    let filtered = [...recipes]

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(recipe => 
        recipe.nl_query.toLowerCase().includes(query) ||
        recipe.template_type.toLowerCase().includes(query) ||
        recipe.complexity_level?.toLowerCase().includes(query)
      )
    }

    // Filter by recipe type
    if (selectedType !== 'all') {
      filtered = filtered.filter(recipe => recipe.template_type === selectedType)
    }

    // Filter by complexity level
    if (selectedComplexity !== 'all') {
      filtered = filtered.filter(recipe => recipe.complexity_level === selectedComplexity)
    }

    setFilteredRecipes(filtered)
  }

  const handleRecipeExecute = async (recipeId: number) => {
    try {
      toast.loading('Starting recipe execution...', { id: 'execute' })
      // This would call the recipe execution endpoint when implemented
      await new Promise(resolve => setTimeout(resolve, 2000)) // Placeholder
      toast.success('Recipe execution started', { id: 'execute' })
      fetchRecipes() // Refresh to get updated execution stats
    } catch (err: any) {
      toast.error('Recipe execution failed', { id: 'execute' })
    }
  }

  const getRecipeIcon = (templateType: string) => {
    const recipeType = RECIPE_TYPES[templateType as keyof typeof RECIPE_TYPES]
    if (recipeType) {
      const Icon = recipeType.icon
      return <Icon className="h-5 w-5" />
    }
    return <ChefHat className="h-5 w-5" />
  }

  const getRecipeTypeColor = (templateType: string) => {
    return RECIPE_TYPES[templateType as keyof typeof RECIPE_TYPES]?.color || 'bg-gray-500'
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
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`
    return `${Math.floor(days / 30)} months ago`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading recipes...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 mb-4">{error}</p>
        <Button onClick={fetchRecipes}>Try Again</Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Recipe Hub</h1>
          <p className="text-muted-foreground mt-1">
            Create and execute multi-step automation workflows
          </p>
        </div>
        <Button onClick={() => navigate('/recipes/new')} className="gap-2">
          <Plus className="h-4 w-4" />
          New Recipe
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search recipes by name, type, or complexity..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={selectedType} onValueChange={setSelectedType}>
              <SelectTrigger className="w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Recipe Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="recipe">Complete Recipes</SelectItem>
                <SelectItem value="recipe_step">Recipe Steps</SelectItem>
                <SelectItem value="recipe_template">Recipe Templates</SelectItem>
              </SelectContent>
            </Select>
            <Select value={selectedComplexity} onValueChange={setSelectedComplexity}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Complexity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="beginner">Beginner</SelectItem>
                <SelectItem value="intermediate">Intermediate</SelectItem>
                <SelectItem value="advanced">Advanced</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Recipes Grid */}
      {filteredRecipes.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8">
            <ChefHat className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              {recipes.length === 0 
                ? "No recipes found. Create your first recipe to get started."
                : "No recipes match your current filters."
              }
            </p>
            {recipes.length === 0 && (
              <Button 
                onClick={() => navigate('/recipes/new')} 
                className="mt-4 gap-2"
              >
                <Plus className="h-4 w-4" />
                Create Recipe
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredRecipes.map((recipe) => (
            <Card 
              key={recipe.id} 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => navigate(`/recipes/${recipe.id}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${getRecipeTypeColor(recipe.template_type)}`}>
                      {getRecipeIcon(recipe.template_type)}
                    </div>
                    <div>
                      <CardTitle className="text-base line-clamp-1">
                        {recipe.nl_query}
                      </CardTitle>
                      <CardDescription className="capitalize">
                        {RECIPE_TYPES[recipe.template_type as keyof typeof RECIPE_TYPES]?.label || recipe.template_type}
                      </CardDescription>
                    </div>
                  </div>
                  {recipe.complexity_level && (
                    <div className="flex items-center gap-2">
                      <div 
                        className={`w-3 h-3 rounded-full ${getComplexityColor(recipe.complexity_level)}`}
                        title={`Complexity: ${recipe.complexity_level}`}
                      />
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {/* Recipe Stats */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  {recipe.execution_time_estimate && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      <span>{formatExecutionTime(recipe.execution_time_estimate)}</span>
                    </div>
                  )}
                  {recipe.execution_count !== undefined && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Users className="h-3 w-3" />
                      <span>{recipe.execution_count} runs</span>
                    </div>
                  )}
                  {recipe.success_rate !== undefined && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <TrendingUp className="h-3 w-3" />
                      <span>{Math.round(recipe.success_rate)}% success</span>
                    </div>
                  )}
                  {recipe.recipe_steps && recipe.recipe_steps.length > 0 && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <ListChecks className="h-3 w-3" />
                      <span>{recipe.recipe_steps.length} steps</span>
                    </div>
                  )}
                </div>

                {/* Success Rate Indicator */}
                {recipe.success_rate !== undefined && (
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-muted-foreground mb-1">
                      <span>Success Rate</span>
                      <span>{Math.round(recipe.success_rate)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${SUCCESS_RATE_COLOR(recipe.success_rate)}`}
                        style={{ width: `${recipe.success_rate}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Required Tools */}
                {recipe.required_tools && recipe.required_tools.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-muted-foreground mb-2">Required Tools</p>
                    <div className="flex flex-wrap gap-1">
                      {recipe.required_tools.slice(0, 3).map((toolId, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          Tool #{toolId}
                        </Badge>
                      ))}
                      {recipe.required_tools.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{recipe.required_tools.length - 3}
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* Last executed */}
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                  <span>Last run: {formatLastExecuted(recipe.last_executed)}</span>
                  <span className="capitalize">{recipe.status}</span>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  {recipe.template_type === 'recipe' && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 gap-2"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRecipeExecute(recipe.id)
                      }}
                    >
                      <Play className="h-3 w-3" />
                      Execute
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/recipes/${recipe.id}/edit`)
                    }}
                  >
                    <Settings className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}