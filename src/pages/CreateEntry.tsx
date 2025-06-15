import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import api, { CatalogValues } from '@/services/api'
import { Save, ArrowLeft, Plus, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface FormData {
  nl_query: string
  template_type: string
  template: string
  catalog_type: string
  catalog_subtype: string
  catalog_name: string
  tags: string[]
  status: string
  similarity_threshold: number
}

export default function CreateEntry() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: []
  })
  const [tagInput, setTagInput] = useState('')
  const [formData, setFormData] = useState<FormData>({
    nl_query: '',
    template_type: 'sql',
    template: '',
    catalog_type: '',
    catalog_subtype: '',
    catalog_name: '',
    tags: [],
    status: 'active',
    similarity_threshold: 0.85
  })

  const fetchCatalogValues = async () => {
    try {
      const values = await api.getCatalogValues()
      setCatalogValues(values)
    } catch (error) {
      console.error('Error fetching catalog values:', error)
    }
  }

  useEffect(() => {
    fetchCatalogValues()
  }, [])

  const handleInputChange = (field: keyof FormData, value: string | number | string[]) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const addTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      handleInputChange('tags', [...formData.tags, tagInput.trim()])
      setTagInput('')
    }
  }

  const removeTag = (tagToRemove: string) => {
    handleInputChange('tags', formData.tags.filter(tag => tag !== tagToRemove))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.nl_query.trim()) {
      toast.error('Natural language query is required')
      return
    }
    
    if (!formData.template.trim()) {
      toast.error('Template is required')
      return
    }

    try {
      setLoading(true)
      
      const submissionData = {
        ...formData,
        catalog_type: formData.catalog_type || null,
        catalog_subtype: formData.catalog_subtype || null,
        catalog_name: formData.catalog_name || null,
      }

      await api.createCacheEntry(submissionData)
      toast.success('Cache entry created successfully!')
      navigate('/cache-entries')
    } catch (error: any) {
      console.error('Error creating entry:', error)
      toast.error(error.response?.data?.detail || 'Failed to create cache entry')
    } finally {
      setLoading(false)
    }
  }

  const getTemplateHelperText = () => {
    switch (formData.template_type) {
      case 'sql':
        return 'Enter your SQL query template here. You can use placeholders like {variable} for dynamic values.'
      case 'api':
        return 'Enter your API endpoint URL or configuration. Include parameters and headers as needed.'
      case 'url':
        return 'Enter your URL template with dynamic parameters.'
      default:
        return 'Enter your template here.'
    }
  }

  const getTemplateExample = () => {
    switch (formData.template_type) {
      case 'sql':
        return 'SELECT * FROM customers WHERE city = \'{city}\' AND status = \'active\''
      case 'api':
        return 'GET /api/customers?city={city}&status=active'
      case 'url':
        return 'https://api.example.com/customers?city={city}'
      default:
        return ''
    }
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/cache-entries')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Entries
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-foreground">Create Cache Entry</h1>
          <p className="text-muted-foreground">Add a new cache entry with catalog information</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information Card */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="nl_query">Natural Language Query *</Label>
              <Textarea
                id="nl_query"
                placeholder="Enter the natural language query that users will ask..."
                value={formData.nl_query}
                onChange={(e) => handleInputChange('nl_query', e.target.value)}
                rows={3}
                required
              />
              <p className="text-sm text-muted-foreground mt-1">
                Example: "Get all customers from New York with active status"
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="template_type">Template Type *</Label>
                <Select
                  value={formData.template_type}
                  onValueChange={(value) => handleInputChange('template_type', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select template type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sql">SQL Query</SelectItem>
                    <SelectItem value="api">API Call</SelectItem>
                    <SelectItem value="url">URL Template</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="status">Status</Label>
                <Select
                  value={formData.status}
                  onValueChange={(value) => handleInputChange('status', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label htmlFor="template">Template *</Label>
              <Textarea
                id="template"
                placeholder={getTemplateExample()}
                value={formData.template}
                onChange={(e) => handleInputChange('template', e.target.value)}
                rows={6}
                required
              />
              <p className="text-sm text-muted-foreground mt-1">
                {getTemplateHelperText()}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Catalog Information Card */}
        <Card>
          <CardHeader>
            <CardTitle>Catalog Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="catalog_type">Catalog Type</Label>
                <Select
                  value={formData.catalog_type}
                  onValueChange={(value) => handleInputChange('catalog_type', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select catalog type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No catalog type</SelectItem>
                    {catalogValues.catalog_types.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="catalog_subtype">Catalog Subtype</Label>
                <Select
                  value={formData.catalog_subtype}
                  onValueChange={(value) => handleInputChange('catalog_subtype', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select catalog subtype" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No catalog subtype</SelectItem>
                    {catalogValues.catalog_subtypes.map((subtype) => (
                      <SelectItem key={subtype} value={subtype}>
                        {subtype}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="catalog_name">Catalog Name</Label>
                <Select
                  value={formData.catalog_name}
                  onValueChange={(value) => handleInputChange('catalog_name', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select catalog name" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No catalog name</SelectItem>
                    {catalogValues.catalog_names.map((name) => (
                      <SelectItem key={name} value={name}>
                        {name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Catalog information helps organize and filter cache entries. All fields are optional.
            </p>
          </CardContent>
        </Card>

        {/* Additional Settings Card */}
        <Card>
          <CardHeader>
            <CardTitle>Additional Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="similarity_threshold">Similarity Threshold</Label>
              <Input
                id="similarity_threshold"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={formData.similarity_threshold}
                onChange={(e) => handleInputChange('similarity_threshold', parseFloat(e.target.value) || 0)}
              />
              <p className="text-sm text-muted-foreground mt-1">
                Threshold for semantic similarity matching (0-1). Higher values require closer matches.
              </p>
            </div>

            <div>
              <Label htmlFor="tags">Tags</Label>
              <div className="space-y-2">
                <div className="flex gap-2">
                  <Input
                    id="tags"
                    placeholder="Enter a tag..."
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addTag()
                      }
                    }}
                  />
                  <Button type="button" variant="outline" onClick={addTag}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                
                {formData.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formData.tags.map((tag, index) => (
                      <div 
                        key={index}
                        className="inline-flex items-center gap-1 bg-secondary text-secondary-foreground px-2 py-1 rounded-md text-sm"
                      >
                        {tag}
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                          onClick={() => removeTag(tag)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Add tags to help categorize and search for this cache entry.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/cache-entries')}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Creating...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Create Entry
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
} 