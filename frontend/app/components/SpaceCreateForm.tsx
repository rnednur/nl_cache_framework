'use client'

import { useState } from "react"
import { X, Plus, Trash2, Save } from "lucide-react"
import { Button } from "./ui/button"
import { Card } from "./ui/card"
import { Input } from "./ui/input"
import { Label } from "./ui/label"
import { Textarea } from "./ui/textarea"
import { Switch } from "./ui/switch"
import { Badge } from "./ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./ui/dialog"
import spacesApi from "@/app/services/spaces-api"
import type { SpaceCreate, TemplateParameter } from "@/app/services/spaces-api"

interface SpaceCreateFormProps {
  isOpen: boolean
  onClose: () => void
  onSpaceCreated: () => void
  userId: number
  initialData?: Partial<SpaceCreate>
}

const SPACE_TYPES = [
  { value: 'personal', label: 'Personal', description: 'Private space for your own use' },
  { value: 'team', label: 'Team', description: 'Shared with specific team members' },
  { value: 'public', label: 'Public', description: 'Visible to everyone' },
  { value: 'temporary', label: 'Temporary', description: 'Auto-deleted after expiration' }
] as const

const CONTENT_TYPES = [
  { value: 'query_result', label: 'Query Result', description: 'SQL query results' },
  { value: 'template', label: 'Template', description: 'Reusable template' },
  { value: 'visualization', label: 'Visualization', description: 'Charts and graphs' },
  { value: 'report', label: 'Report', description: 'Generated report' },
  { value: 'dashboard', label: 'Dashboard', description: 'Interactive dashboard' },
  { value: 'dataset', label: 'Dataset', description: 'Raw data collection' },
  { value: 'webpage', label: 'Webpage', description: 'Web content' }
] as const

const STORAGE_BACKENDS = [
  { value: 'local', label: 'Local Storage' },
  { value: 's3', label: 'Amazon S3' },
  { value: 'gcs', label: 'Google Cloud Storage' },
  { value: 'azure', label: 'Azure Blob Storage' }
] as const

export default function SpaceCreateForm({ 
  isOpen, 
  onClose, 
  onSpaceCreated, 
  userId, 
  initialData = {} 
}: SpaceCreateFormProps) {
  const [formData, setFormData] = useState<SpaceCreate>({
    name: initialData.name || '',
    display_name: initialData.display_name || '',
    description: initialData.description || '',
    space_type: initialData.space_type || 'personal',
    content_type: initialData.content_type || 'query_result',
    domain: initialData.domain || '',
    category: initialData.category || '',
    tags: initialData.tags || [],
    is_public: initialData.is_public || false,
    is_template: initialData.is_template || false,
    template_parameters: initialData.template_parameters || [],
    storage_backend: initialData.storage_backend || 'local',
    auto_cleanup: initialData.auto_cleanup || false,
    retention_days: initialData.retention_days || undefined,
    ...initialData
  })

  const [tagInput, setTagInput] = useState('')
  const [parameterName, setParameterName] = useState('')
  const [parameterType, setParameterType] = useState('string')
  const [parameterRequired, setParameterRequired] = useState(false)
  const [parameterDescription, setParameterDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleInputChange = (field: keyof SpaceCreate, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags?.includes(tagInput.trim())) {
      const newTags = [...(formData.tags || []), tagInput.trim()]
      handleInputChange('tags', newTags)
      setTagInput('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    const newTags = formData.tags?.filter(tag => tag !== tagToRemove) || []
    handleInputChange('tags', newTags)
  }

  const handleAddParameter = () => {
    if (parameterName.trim()) {
      const newParam: TemplateParameter = {
        name: parameterName.trim(),
        type: parameterType,
        required: parameterRequired,
        description: parameterDescription.trim() || undefined
      }
      
      const newParameters = [...(formData.template_parameters || []), newParam]
      handleInputChange('template_parameters', newParameters)
      
      // Reset form
      setParameterName('')
      setParameterType('string')
      setParameterRequired(false)
      setParameterDescription('')
    }
  }

  const handleRemoveParameter = (index: number) => {
    const newParameters = formData.template_parameters?.filter((_, i) => i !== index) || []
    handleInputChange('template_parameters', newParameters)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.name.trim()) {
      setError('Space name is required')
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      await spacesApi.createSpace(formData, userId)
      onSpaceCreated()
      
    } catch (err) {
      console.error('Error creating space:', err)
      setError('Failed to create space. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Space</DialogTitle>
          <DialogDescription>
            Create a new collaborative workspace for sharing content and templates
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* Basic Information */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Basic Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Space Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="my-awesome-space"
                  required
                />
              </div>
              
              <div>
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  value={formData.display_name || ''}
                  onChange={(e) => handleInputChange('display_name', e.target.value)}
                  placeholder="My Awesome Space"
                />
              </div>
            </div>

            <div className="mt-4">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description || ''}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Describe what this space is for..."
                rows={3}
              />
            </div>
          </Card>

          {/* Space Configuration */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Configuration</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="space_type">Space Type</Label>
                <select
                  id="space_type"
                  value={formData.space_type}
                  onChange={(e) => handleInputChange('space_type', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md"
                >
                  {SPACE_TYPES.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label} - {type.description}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <Label htmlFor="content_type">Content Type</Label>
                <select
                  id="content_type"
                  value={formData.content_type}
                  onChange={(e) => handleInputChange('content_type', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md"
                >
                  {CONTENT_TYPES.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label} - {type.description}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <Label htmlFor="domain">Domain</Label>
                <Input
                  id="domain"
                  value={formData.domain || ''}
                  onChange={(e) => handleInputChange('domain', e.target.value)}
                  placeholder="analytics, finance, etc."
                />
              </div>
              
              <div>
                <Label htmlFor="category">Category</Label>
                <Input
                  id="category"
                  value={formData.category || ''}
                  onChange={(e) => handleInputChange('category', e.target.value)}
                  placeholder="reporting, dashboard, etc."
                />
              </div>
            </div>

            <div className="flex items-center space-x-6 mt-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="is_public"
                  checked={formData.is_public}
                  onCheckedChange={(checked) => handleInputChange('is_public', checked)}
                />
                <Label htmlFor="is_public">Public Space</Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Switch
                  id="is_template"
                  checked={formData.is_template}
                  onCheckedChange={(checked) => handleInputChange('is_template', checked)}
                />
                <Label htmlFor="is_template">Template Space</Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Switch
                  id="auto_cleanup"
                  checked={formData.auto_cleanup}
                  onCheckedChange={(checked) => handleInputChange('auto_cleanup', checked)}
                />
                <Label htmlFor="auto_cleanup">Auto Cleanup</Label>
              </div>
            </div>
          </Card>

          {/* Tags */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Tags</h3>
            
            <div className="flex flex-wrap gap-2 mb-4">
              {formData.tags?.map((tag) => (
                <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                  {tag}
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag)}
                    className="ml-1 hover:text-red-500"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
            
            <div className="flex gap-2">
              <Input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder="Add a tag..."
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
              />
              <Button type="button" onClick={handleAddTag} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </Card>

          {/* Template Parameters (only if is_template is true) */}
          {formData.is_template && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Template Parameters</h3>
              
              {formData.template_parameters && formData.template_parameters.length > 0 && (
                <div className="space-y-2 mb-4">
                  {formData.template_parameters.map((param, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div>
                        <span className="font-medium">{param.name}</span>
                        <span className="text-gray-500 ml-2">({param.type})</span>
                        {param.required && <span className="text-red-500 ml-1">*</span>}
                        {param.description && (
                          <div className="text-sm text-gray-600">{param.description}</div>
                        )}
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveParameter(index)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                <Input
                  value={parameterName}
                  onChange={(e) => setParameterName(e.target.value)}
                  placeholder="Parameter name"
                />
                <select
                  value={parameterType}
                  onChange={(e) => setParameterType(e.target.value)}
                  className="p-2 border border-gray-300 rounded-md"
                >
                  <option value="string">String</option>
                  <option value="number">Number</option>
                  <option value="boolean">Boolean</option>
                  <option value="date">Date</option>
                </select>
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={parameterRequired}
                    onCheckedChange={setParameterRequired}
                  />
                  <Label>Required</Label>
                </div>
                <Button type="button" onClick={handleAddParameter} size="sm">
                  <Plus className="h-4 w-4" />
                  Add
                </Button>
              </div>
              
              <Input
                value={parameterDescription}
                onChange={(e) => setParameterDescription(e.target.value)}
                placeholder="Parameter description (optional)"
                className="mt-2"
              />
            </Card>
          )}

          {/* Storage Configuration */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Storage</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="storage_backend">Storage Backend</Label>
                <select
                  id="storage_backend"
                  value={formData.storage_backend}
                  onChange={(e) => handleInputChange('storage_backend', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md"
                >
                  {STORAGE_BACKENDS.map(backend => (
                    <option key={backend.value} value={backend.value}>
                      {backend.label}
                    </option>
                  ))}
                </select>
              </div>
              
              {formData.auto_cleanup && (
                <div>
                  <Label htmlFor="retention_days">Retention Days</Label>
                  <Input
                    id="retention_days"
                    type="number"
                    value={formData.retention_days || ''}
                    onChange={(e) => handleInputChange('retention_days', parseInt(e.target.value) || undefined)}
                    placeholder="30"
                    min="1"
                  />
                </div>
              )}
            </div>
          </Card>

          {/* Form Actions */}
          <div className="flex justify-end space-x-4 pt-6 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
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
                  Create Space
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}