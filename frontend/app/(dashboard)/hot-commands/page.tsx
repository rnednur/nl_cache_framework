'use client'

import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Textarea } from '../../components/ui/textarea'
import { Switch } from '../../components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../../components/ui/dialog'
import {
  Search,
  Database,
  Code,
  Activity,
  Calendar,
  TrendingUp,
  Users,
  Plus,
  ExternalLink,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Tag,
  Zap,
  FileText,
  Settings,
  Copy,
  Eye,
  Edit,
  Trash2,
  Globe,
  Lock
} from 'lucide-react'
import api from '../../services/api'

interface HotCommand {
  id: number
  command_name: string
  display_name?: string
  description?: string
  is_public: boolean
  tags?: string[]
  usage_count: number
  last_used?: string
  created_at: string
  updated_at: string
  cache_entry_id?: number
  source_template_type?: string
  source_reasoning?: string
  user_id: number
}

export default function HotCommandsPage() {
  const [commands, setCommands] = useState<HotCommand[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [visibilityFilter, setVisibilityFilter] = useState<string>('all')
  const [templateTypeFilter, setTemplateTypeFilter] = useState<string>('all')
  const [selectedCommand, setSelectedCommand] = useState<HotCommand | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [commandForm, setCommandForm] = useState({
    command_name: '',
    display_name: '',
    description: '',
    is_public: false,
    tags: [] as string[]
  })
  const [updating, setUpdating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  
  // Metadata state for dynamic dropdowns
  const [metadata, setMetadata] = useState<{
    domains: string[]
    categories: string[]
    tags: string[]
    query_types: string[]
    template_types: string[]
  }>({
    domains: [],
    categories: [],
    tags: [],
    query_types: [],
    template_types: []
  })
  const [metadataLoading, setMetadataLoading] = useState(true)
  const [dashboardStats, setDashboardStats] = useState<{
    total_commands: number
    total_executions: number
    avg_success_rate: number
    recent_activity: Array<{
      command_name: string
      execution_count: number
      last_executed: string
    }>
    popular_commands: Array<{
      id: number
      command_name: string
      usage_count: number
      success_rate: number
    }>
    domains_used: Array<{
      domain: string
      count: number
    }>
  } | null>(null)

  const fetchHotCommands = async () => {
    try {
      setLoading(true)
      const data = await api.getMyHotCommands()
      setCommands(data)
    } catch (error: any) {
      toast.error('Failed to load hot commands')
      console.error('Error loading hot commands:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchDashboardStats = async () => {
    try {
      const stats = await api.getHotCommandsDashboardStats()
      setDashboardStats(stats)
    } catch (error: any) {
      console.error('Error loading dashboard stats:', error)
      // Don't show error for stats, it's optional
    }
  }

  const handleEditCommand = async () => {
    if (!selectedCommand || !commandForm.command_name) {
      toast.error('Please fill in the command name')
      return
    }

    try {
      setUpdating(true)
      await api.updateHotCommand(selectedCommand.id, {
        command_name: commandForm.command_name,
        display_name: commandForm.display_name || undefined,
        description: commandForm.description || undefined,
        is_public: commandForm.is_public,
        tags: commandForm.tags.length > 0 ? commandForm.tags : undefined
      })

      toast.success(`Hot command "${commandForm.command_name}" updated successfully!`)
      setEditDialogOpen(false)
      setSelectedCommand(null)
      
      // Refresh the commands list
      await fetchHotCommands()
    } catch (error: any) {
      toast.error('Failed to update hot command')
      console.error('Error updating hot command:', error)
    } finally {
      setUpdating(false)
    }
  }

  const handleDeleteCommand = async () => {
    if (!selectedCommand) return

    try {
      setDeleting(true)
      await api.deleteHotCommand(selectedCommand.id)
      
      toast.success(`Hot command "${selectedCommand.command_name}" deleted successfully!`)
      setDeleteDialogOpen(false)
      setSelectedCommand(null)
      
      // Refresh the commands list
      await fetchHotCommands()
    } catch (error: any) {
      toast.error('Failed to delete hot command')
      console.error('Error deleting hot command:', error)
    } finally {
      setDeleting(false)
    }
  }

  const handleTagsChange = (tagsString: string) => {
    const tags = tagsString.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0)
    setCommandForm(prev => ({ ...prev, tags }))
  }

  const openEditDialog = (command: HotCommand) => {
    setSelectedCommand(command)
    setCommandForm({
      command_name: command.command_name,
      display_name: command.display_name || '',
      description: command.description || '',
      is_public: command.is_public,
      tags: command.tags || []
    })
    setEditDialogOpen(true)
  }

  const openDeleteDialog = (command: HotCommand) => {
    setSelectedCommand(command)
    setDeleteDialogOpen(true)
  }

  useEffect(() => {
    const loadData = async () => {
      await Promise.all([
        fetchHotCommands(),
        fetchDashboardStats(),
        loadMetadata()
      ])
    }
    loadData()
  }, [])
  
  const loadMetadata = async () => {
    try {
      setMetadataLoading(true)
      const meta = await api.getHotCommandsMetadata()
      setMetadata(meta)
    } catch (error: any) {
      console.error('Failed to load metadata:', error)
      // Keep default empty arrays - no hardcoded fallbacks
    } finally {
      setMetadataLoading(false)
    }
  }

  const filteredCommands = commands.filter(command => {
    const matchesSearch = !searchQuery || 
      command.command_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (command.display_name && command.display_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (command.description && command.description.toLowerCase().includes(searchQuery.toLowerCase()))
    
    const matchesVisibility = visibilityFilter === 'all' || 
      (visibilityFilter === 'public' && command.is_public) ||
      (visibilityFilter === 'private' && !command.is_public)
    
    const matchesTemplateType = templateTypeFilter === 'all' || 
      command.source_template_type === templateTypeFilter
    
    return matchesSearch && matchesVisibility && matchesTemplateType
  })

  const formatLastUsed = (lastUsed?: string) => {
    if (!lastUsed) return 'Never'
    const date = new Date(lastUsed)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 3600 * 24))
    
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days} days ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Hot Commands</h1>
          <p className="text-muted-foreground">
            Manage your Hot Commands and view usage analytics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-sm">
            {filteredCommands.length} commands
          </Badge>
          <Button onClick={() => window.location.href = '/cache-explorer'}>
            <Plus className="h-4 w-4 mr-1" />
            Create from Cache
          </Button>
        </div>
      </div>

      {/* Dashboard Stats */}
      {dashboardStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-blue-500" />
                <div>
                  <p className="text-sm text-muted-foreground">Total Commands</p>
                  <p className="text-2xl font-bold">{dashboardStats.total_commands}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-green-500" />
                <div>
                  <p className="text-sm text-muted-foreground">Total Executions</p>
                  <p className="text-2xl font-bold">{dashboardStats.total_executions}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-purple-500" />
                <div>
                  <p className="text-sm text-muted-foreground">Avg Success Rate</p>
                  <p className="text-2xl font-bold">{dashboardStats.avg_success_rate.toFixed(1)}%</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-orange-500" />
                <div>
                  <p className="text-sm text-muted-foreground">Domains Used</p>
                  <p className="text-2xl font-bold">{dashboardStats.domains_used.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search commands..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="visibility">Visibility</Label>
              <Select value={visibilityFilter} onValueChange={setVisibilityFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All visibility" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All visibility</SelectItem>
                  <SelectItem value="public">Public</SelectItem>
                  <SelectItem value="private">Private</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="template-type">Source Type</Label>
              <Select value={templateTypeFilter} onValueChange={setTemplateTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  {metadata.template_types.map(type => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Commands List */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2">Loading hot commands...</span>
          </div>
        ) : filteredCommands.length === 0 ? (
          <div className="text-center py-12">
            <Zap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No hot commands found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery || visibilityFilter || templateTypeFilter 
                ? 'Try adjusting your filters' 
                : 'Create your first hot command from cache entries'}
            </p>
            <Button onClick={() => window.location.href = '/cache-explorer'}>
              <Plus className="h-4 w-4 mr-1" />
              Browse Cache Entries
            </Button>
          </div>
        ) : (
          filteredCommands.map((command) => (
            <Card key={command.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-xs">
                        /{command.command_name}
                      </Badge>
                      {command.source_template_type && (
                        <Badge variant="secondary" className="text-xs">
                          {command.source_template_type}
                        </Badge>
                      )}
                      {command.is_public ? (
                        <Badge className="text-xs bg-blue-100 text-blue-800">
                          <Globe className="h-3 w-3 mr-1" />
                          Public
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          <Lock className="h-3 w-3 mr-1" />
                          Private
                        </Badge>
                      )}
                    </div>

                    <h3 className="text-lg font-semibold mb-2">
                      {command.display_name || command.command_name}
                    </h3>

                    {command.description && (
                      <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                        {command.description}
                      </p>
                    )}

                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Activity className="h-3 w-3" />
                        {command.usage_count} uses
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatLastUsed(command.last_used)}
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        Created {new Date(command.created_at).toLocaleDateString()}
                      </div>
                    </div>

                    {command.tags && command.tags.length > 0 && (
                      <div className="flex items-center gap-1 mt-2">
                        <Tag className="h-3 w-3" />
                        <div className="flex flex-wrap gap-1">
                          {command.tags.slice(0, 3).map(tag => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {command.tags.length > 3 && (
                            <span className="text-xs text-muted-foreground">
                              +{command.tags.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    {command.cache_entry_id && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.location.href = `/cache-entries/${command.cache_entry_id}`}
                      >
                        <ExternalLink className="h-4 w-4 mr-1" />
                        View Source
                      </Button>
                    )}
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(command)}
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openDeleteDialog(command)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Edit Command Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Hot Command</DialogTitle>
            <DialogDescription>
              Update your Hot Command settings
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="command_name">Command Name *</Label>
                <Input
                  id="command_name"
                  value={commandForm.command_name}
                  onChange={(e) => setCommandForm(prev => ({ ...prev, command_name: e.target.value }))}
                  placeholder="my_command"
                  pattern="^[a-zA-Z0-9_]+$"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Letters, numbers, and underscores only
                </p>
              </div>

              <div>
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  value={commandForm.display_name}
                  onChange={(e) => setCommandForm(prev => ({ ...prev, display_name: e.target.value }))}
                  placeholder="My Command"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={commandForm.description}
                onChange={(e) => setCommandForm(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Command description..."
                rows={3}
              />
            </div>

            <div>
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                value={commandForm.tags.join(', ')}
                onChange={(e) => handleTagsChange(e.target.value)}
                placeholder="tag1, tag2, tag3"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="is_public"
                checked={commandForm.is_public}
                onCheckedChange={(checked) => setCommandForm(prev => ({ ...prev, is_public: checked }))}
              />
              <Label htmlFor="is_public">Make command public</Label>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleEditCommand} disabled={updating || !commandForm.command_name}>
                {updating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <Edit className="h-4 w-4 mr-1" />
                    Update Command
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Command Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Hot Command</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedCommand?.command_name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteCommand} 
              disabled={deleting}
            >
              {deleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete Command
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}