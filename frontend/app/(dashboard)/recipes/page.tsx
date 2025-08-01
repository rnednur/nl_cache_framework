'use client'

import { useState, useEffect } from 'react'
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
  Search,
  Plus,
  Play,
  Clock,
  Users,
  ChefHat,
  BookOpen,
  Layers,
  Filter,
  Loader2,
  TrendingUp,
  CheckCircle,
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
  execution_time_estimate?: number
  complexity_level?: string
  success_rate?: number
  last_executed?: string
  execution_count?: number
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

export default function Recipes() {
  const router = useRouter()
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
      const response = await api.getCacheEntries(1, 100, recipeTypes.join(','))
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
        recipe.recipe_steps?.some(step => step.name.toLowerCase().includes(query))
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
      toast.loading('Preparing recipe execution...', { id: 'execute' })
      // This would call an execution endpoint when implemented
      await new Promise(resolve => setTimeout(resolve, 1000)) // Placeholder
      toast.success('Recipe execution initiated', { id: 'execute' })
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
    return RECIPE_TYPES[templateType as keyof typeof RECIPE_TYPES]?.color || 'bg-neutral-500'
  }

  const getComplexityColor = (complexity?: string) => {
    return COMPLEXITY_COLORS[complexity as keyof typeof COMPLEXITY_COLORS] || 'bg-neutral-500'
  }

  const formatExecutionTime = (minutes?: number) => {
    if (!minutes) return 'Unknown'
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
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
          <p className="text-neutral-400 mt-1">
            Discover and execute workflow recipes and templates
          </p>
        </div>
        <Button onClick={() => router.push('/recipes/new')} className="gap-2">
          <Plus className="h-4 w-4" />
          Create Recipe
        </Button>
      </div>

      {/* Filters */}
      <Card className="bg-neutral-800 border-neutral-700">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-neutral-400" />
                <Input
                  placeholder="Search recipes by name, type, or steps..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-neutral-900 border-neutral-700"
                />
              </div>
            </div>
            <Select value={selectedType} onValueChange={setSelectedType}>
              <SelectTrigger className="w-48 bg-neutral-900 border-neutral-700">
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
              <SelectTrigger className="w-48 bg-neutral-900 border-neutral-700">
                <SelectValue placeholder="Complexity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Complexity</SelectItem>
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
        <Card className="bg-neutral-800 border-neutral-700">
          <CardContent className="text-center py-8">
            <ChefHat className="h-12 w-12 mx-auto text-neutral-400 mb-4" />
            <p className="text-neutral-400">
              {recipes.length === 0 
                ? "No recipes found. Create your first recipe to get started."
                : "No recipes match your current filters."
              }
            </p>
            {recipes.length === 0 && (
              <Button 
                onClick={() => router.push('/recipes/new')} 
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
              className="cursor-pointer hover:shadow-lg transition-shadow bg-neutral-800 border-neutral-700 hover:border-neutral-600"
              onClick={() => router.push(`/recipes/${recipe.id}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${getRecipeTypeColor(recipe.template_type)}`}>
                      {getRecipeIcon(recipe.template_type)}
                    </div>
                    <div>
                      <CardTitle className="text-base line-clamp-1 text-white">
                        {recipe.nl_query}
                      </CardTitle>
                      <CardDescription className="capitalize text-neutral-400">
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
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div className="text-center">
                    <div className="text-lg font-semibold text-white">
                      {recipe.recipe_steps?.length || 0}
                    </div>
                    <div className="text-xs text-neutral-400">Steps</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold text-white">
                      {recipe.required_tools?.length || 0}
                    </div>
                    <div className="text-xs text-neutral-400">Tools</div>
                  </div>
                </div>

                {/* Execution Time & Success Rate */}
                <div className="flex items-center justify-between text-xs text-neutral-400 mb-3">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{formatExecutionTime(recipe.execution_time_estimate)}</span>
                  </div>
                  {recipe.success_rate !== undefined && (
                    <div className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      <span>{Math.round(recipe.success_rate * 100)}% success</span>
                    </div>
                  )}
                </div>

                {/* Execution Stats */}
                <div className="flex items-center justify-between text-xs text-neutral-400 mb-3">
                  <span>Last run: {formatLastExecuted(recipe.last_executed)}</span>
                  <span>{recipe.execution_count || 0} executions</span>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 gap-2 border-neutral-600 text-neutral-300 hover:bg-neutral-700"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRecipeExecute(recipe.id)
                    }}
                  >
                    <Play className="h-3 w-3" />
                    Execute
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-neutral-600 text-neutral-300 hover:bg-neutral-700"
                    onClick={(e) => {
                      e.stopPropagation()
                      router.push(`/recipes/${recipe.id}`)
                    }}
                  >
                    <BookOpen className="h-3 w-3" />
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