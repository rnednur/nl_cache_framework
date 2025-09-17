import { useState } from "react"
import { X, Plus, Trash2, Calendar, Clock, Globe, Save } from "lucide-react"
import { Button } from "./ui/button"
import { Card } from "./ui/card"
import { Input } from "./ui/input"
import { Label } from "./ui/label"
import { Textarea } from "./ui/textarea"
import { Select } from "./ui/select"
import { Switch } from "./ui/switch"
import { Badge } from "./ui/badge"
import { Dialog } from "./ui/dialog"
import spacesApi from "../services/spaces-api"
import type { SpaceCreate, TemplateParameter } from "../services/spaces-api"

interface SpaceCreateFormProps {
  isOpen: boolean
  onClose: () => void
  onSpaceCreated: () => void
  userId: number
  initialData?: Partial<SpaceCreate>
}

export default function SpaceCreateForm({ 
  isOpen, 
  onClose, 
  onSpaceCreated, 
  userId,
  initialData 
}: SpaceCreateFormProps) {
  const [formData, setFormData] = useState<SpaceCreate>({
    name: initialData?.name || "",
    display_name: initialData?.display_name || "",
    description: initialData?.description || "",
    space_type: initialData?.space_type || "personal",
    content_type: initialData?.content_type || "query_result",
    domain: initialData?.domain || "",
    category: initialData?.category || "",
    tags: initialData?.tags || [],
    is_public: initialData?.is_public || false,
    is_template: initialData?.is_template || false,
    template_parameters: initialData?.template_parameters || [],
    base_query: initialData?.base_query || "",
    source_query: initialData?.source_query || "",
    storage_backend: initialData?.storage_backend || "local",
    schedule_type: initialData?.schedule_type || "none",
    schedule_config: initialData?.schedule_config || {},
    auto_cleanup: initialData?.auto_cleanup || false,
    retention_days: initialData?.retention_days || undefined
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tagInput, setTagInput] = useState("")
  const [newParameter, setNewParameter] = useState<TemplateParameter>({
    name: "",
    type: "string",
    required: true,
    description: ""
  })

  const handleInputChange = (field: keyof SpaceCreate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags?.includes(tagInput.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...(prev.tags || []), tagInput.trim()]
      }))
      setTagInput("")
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags?.filter(tag => tag !== tagToRemove) || []
    }))
  }

  const handleAddParameter = () => {
    if (newParameter.name.trim()) {
      setFormData(prev => ({
        ...prev,
        template_parameters: [
          ...(prev.template_parameters || []),
          { ...newParameter }
        ]
      }))
      setNewParameter({
        name: "",
        type: "string",
        required: true,
        description: ""
      })
    }
  }

  const handleRemoveParameter = (index: number) => {
    setFormData(prev => ({
      ...prev,
      template_parameters: prev.template_parameters?.filter((_, i) => i !== index) || []
    }))
  }

  const handleScheduleConfigChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      schedule_config: {
        ...prev.schedule_config,
        [field]: value
      }
    }))
  }

  const validateForm = (): string | null => {
    if (!formData.name.trim()) {
      return "Space name is required"
    }
    
    if (formData.name.length > 100) {
      return "Space name must be 100 characters or less"
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(formData.name)) {
      return "Space name can only contain letters, numbers, underscores, and hyphens"
    }

    if (formData.is_template && (!formData.base_query || !formData.base_query.trim())) {
      return "Template spaces require a base query"
    }

    if (formData.schedule_type === "cron" && !formData.schedule_config?.cron_expression) {
      return "CRON schedule requires a CRON expression"
    }

    if (formData.schedule_type === "interval" && !formData.schedule_config?.interval_minutes) {
      return "Interval schedule requires interval minutes"
    }

    if (formData.schedule_type === "webhook" && !formData.schedule_config?.webhook_url) {
      return "Webhook schedule requires a webhook URL"
    }

    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setLoading(true)
    setError(null)

    try {
      await spacesApi.createSpace(formData, userId)
      onSpaceCreated()
      onClose()
    } catch (err) {
      console.error('Error creating space:', err)
      setError('Failed to create space. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
        <Card className="bg-[#252547] border-[#3a3a5e] w-full max-w-4xl max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Create New Space</h2>
                <p className="text-slate-400 mt-1">Set up a new space to store and share your data</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {error && (
              <div className="bg-red-900/20 border border-red-500/50 text-red-400 p-3 rounded-lg mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic Information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="name" className="text-white">Space Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    placeholder="my_space_name"
                    className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                    required
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Use lowercase letters, numbers, underscores, and hyphens only
                  </p>
                </div>

                <div>
                  <Label htmlFor="display_name" className="text-white">Display Name</Label>
                  <Input
                    id="display_name"
                    value={formData.display_name}
                    onChange={(e) => handleInputChange('display_name', e.target.value)}
                    placeholder="My Space Name"
                    className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="description" className="text-white">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  placeholder="Describe what this space contains..."
                  className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                  rows={3}
                />
              </div>

              {/* Space Configuration */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <Label htmlFor="space_type" className="text-white">Space Type</Label>
                  <select
                    id="space_type"
                    value={formData.space_type}
                    onChange={(e) => handleInputChange('space_type', e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#3a3a5e] text-white rounded-md p-2"
                  >
                    <option value="personal">Personal</option>
                    <option value="team">Team</option>
                    <option value="public">Public</option>
                    <option value="temporary">Temporary</option>
                  </select>
                </div>

                <div>
                  <Label htmlFor="content_type" className="text-white">Content Type</Label>
                  <select
                    id="content_type"
                    value={formData.content_type}
                    onChange={(e) => handleInputChange('content_type', e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#3a3a5e] text-white rounded-md p-2"
                  >
                    <option value="query_result">Query Result</option>
                    <option value="template">Template</option>
                    <option value="visualization">Visualization</option>
                    <option value="report">Report</option>
                    <option value="dashboard">Dashboard</option>
                    <option value="dataset">Dataset</option>
                    <option value="webpage">Webpage</option>
                  </select>
                </div>

                <div>
                  <Label htmlFor="storage_backend" className="text-white">Storage Backend</Label>
                  <select
                    id="storage_backend"
                    value={formData.storage_backend}
                    onChange={(e) => handleInputChange('storage_backend', e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#3a3a5e] text-white rounded-md p-2"
                  >
                    <option value="local">Local</option>
                    <option value="s3">Amazon S3</option>
                    <option value="gcs">Google Cloud Storage</option>
                    <option value="azure">Azure Blob Storage</option>
                  </select>
                </div>
              </div>

              {/* Domain and Category */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="domain" className="text-white">Domain</Label>
                  <Input
                    id="domain"
                    value={formData.domain}
                    onChange={(e) => handleInputChange('domain', e.target.value)}
                    placeholder="e.g., RAN, CustomerExperience"
                    className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                  />
                </div>

                <div>
                  <Label htmlFor="category" className="text-white">Category</Label>
                  <Input
                    id="category"
                    value={formData.category}
                    onChange={(e) => handleInputChange('category', e.target.value)}
                    placeholder="e.g., Capacity, RF, Mobility"
                    className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                  />
                </div>
              </div>

              {/* Tags */}
              <div>
                <Label className="text-white">Tags</Label>
                <div className="flex items-center space-x-2 mb-2">
                  <Input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    placeholder="Add a tag..."
                    className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                  />
                  <Button type="button" onClick={handleAddTag} size="sm">
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {formData.tags?.map((tag, index) => (
                    <Badge 
                      key={index} 
                      className="bg-slate-700/50 text-slate-300 text-xs cursor-pointer"
                      onClick={() => handleRemoveTag(tag)}
                    >
                      {tag} <X className="h-3 w-3 ml-1" />
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex items-center justify-between">
                  <Label className="text-white">Public Space</Label>
                  <Switch
                    checked={formData.is_public}
                    onCheckedChange={(checked) => handleInputChange('is_public', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label className="text-white">Template Space</Label>
                  <Switch
                    checked={formData.is_template}
                    onCheckedChange={(checked) => handleInputChange('is_template', checked)}
                  />
                </div>
              </div>

              {/* Template Configuration */}
              {formData.is_template && (
                <div className="space-y-4 border border-[#3a3a5e] rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-white">Template Configuration</h3>
                  
                  <div>
                    <Label htmlFor="base_query" className="text-white">Base Query *</Label>
                    <Textarea
                      id="base_query"
                      value={formData.base_query}
                      onChange={(e) => handleInputChange('base_query', e.target.value)}
                      placeholder="SELECT * FROM table WHERE date = {start_date} AND region = {region}"
                      className="bg-[#1a1a2e] border-[#3a3a5e] text-white font-mono"
                      rows={4}
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      Use {"{parameter_name}"} for template parameters
                    </p>
                  </div>

                  <div>
                    <Label className="text-white">Template Parameters</Label>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-2">
                      <Input
                        value={newParameter.name}
                        onChange={(e) => setNewParameter(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Parameter name"
                        className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                      />
                      <select
                        value={newParameter.type}
                        onChange={(e) => setNewParameter(prev => ({ ...prev, type: e.target.value }))}
                        className="bg-[#1a1a2e] border border-[#3a3a5e] text-white rounded-md p-2"
                      >
                        <option value="string">String</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>
                        <option value="date">Date</option>
                      </select>
                      <Input
                        value={newParameter.description}
                        onChange={(e) => setNewParameter(prev => ({ ...prev, description: e.target.value }))}
                        placeholder="Description"
                        className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                      />
                      <Button type="button" onClick={handleAddParameter} size="sm">
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    <div className="space-y-2">
                      {formData.template_parameters?.map((param, index) => (
                        <div key={index} className="flex items-center justify-between bg-[#1a1a2e] p-2 rounded">
                          <div className="flex items-center space-x-2">
                            <span className="text-white font-mono">{param.name}</span>
                            <Badge className="bg-blue-600/20 text-blue-400 text-xs">
                              {param.type}
                            </Badge>
                            {param.required && (
                              <Badge className="bg-red-600/20 text-red-400 text-xs">
                                Required
                              </Badge>
                            )}
                            {param.description && (
                              <span className="text-slate-400 text-sm">{param.description}</span>
                            )}
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveParameter(index)}
                            className="text-red-400 hover:text-red-300"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Scheduling Configuration */}
              <div className="space-y-4 border border-[#3a3a5e] rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white">Scheduling (Optional)</h3>
                
                <div>
                  <Label htmlFor="schedule_type" className="text-white">Schedule Type</Label>
                  <select
                    id="schedule_type"
                    value={formData.schedule_type}
                    onChange={(e) => handleInputChange('schedule_type', e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#3a3a5e] text-white rounded-md p-2"
                  >
                    <option value="none">No Scheduling</option>
                    <option value="interval">Interval</option>
                    <option value="cron">CRON Expression</option>
                    <option value="webhook">Webhook</option>
                  </select>
                </div>

                {formData.schedule_type === 'interval' && (
                  <div>
                    <Label htmlFor="interval_minutes" className="text-white">Interval (minutes)</Label>
                    <Input
                      id="interval_minutes"
                      type="number"
                      value={formData.schedule_config?.interval_minutes || ''}
                      onChange={(e) => handleScheduleConfigChange('interval_minutes', parseInt(e.target.value))}
                      placeholder="60"
                      className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                      min="1"
                      max="10080"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      Execute every N minutes (1-10080)
                    </p>
                  </div>
                )}

                {formData.schedule_type === 'cron' && (
                  <div>
                    <Label htmlFor="cron_expression" className="text-white">CRON Expression</Label>
                    <Input
                      id="cron_expression"
                      value={formData.schedule_config?.cron_expression || ''}
                      onChange={(e) => handleScheduleConfigChange('cron_expression', e.target.value)}
                      placeholder="0 9 * * 1"
                      className="bg-[#1a1a2e] border-[#3a3a5e] text-white font-mono"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      Example: "0 9 * * 1" = Every Monday at 9 AM
                    </p>
                  </div>
                )}

                {formData.schedule_type === 'webhook' && (
                  <div>
                    <Label htmlFor="webhook_url" className="text-white">Webhook URL</Label>
                    <Input
                      id="webhook_url"
                      value={formData.schedule_config?.webhook_url || ''}
                      onChange={(e) => handleScheduleConfigChange('webhook_url', e.target.value)}
                      placeholder="https://api.example.com/webhooks/trigger"
                      className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                    />
                  </div>
                )}
              </div>

              {/* Cleanup Configuration */}
              <div className="space-y-4 border border-[#3a3a5e] rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white">Cleanup (Optional)</h3>
                
                <div className="flex items-center justify-between">
                  <Label className="text-white">Auto Cleanup</Label>
                  <Switch
                    checked={formData.auto_cleanup}
                    onCheckedChange={(checked) => handleInputChange('auto_cleanup', checked)}
                  />
                </div>

                {formData.auto_cleanup && (
                  <div>
                    <Label htmlFor="retention_days" className="text-white">Retention Days</Label>
                    <Input
                      id="retention_days"
                      type="number"
                      value={formData.retention_days || ''}
                      onChange={(e) => handleInputChange('retention_days', parseInt(e.target.value))}
                      placeholder="30"
                      className="bg-[#1a1a2e] border-[#3a3a5e] text-white"
                      min="1"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      Number of days to keep the space before automatic cleanup
                    </p>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end space-x-4 pt-6">
                <Button
                  type="button"
                  variant="outline"
                  onClick={onClose}
                  className="border-[#3a3a5e] text-slate-400 hover:text-white"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-700"
                  disabled={loading}
                >
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
          </div>
        </Card>
      </div>
    </Dialog>
  )
}