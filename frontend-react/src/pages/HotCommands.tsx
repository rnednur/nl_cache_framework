import { useState, useEffect } from "react"
import { Search, Filter, Star, Play, Edit3, Share, MoreVertical, X, Save, Loader2 } from "lucide-react"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Card } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../components/ui/dialog"
import { Label } from "../components/ui/label"
import { Textarea } from "../components/ui/textarea"
import { Switch } from "../components/ui/switch"
import { hotCommandsApi } from "../services/hotcommands-api"
import type { HotCommand } from "../services/hotcommands-api"
import { toast } from "react-hot-toast"

// Interface imported from hotcommands-api.ts

export default function HotCommands() {
  const [commands, setCommands] = useState<HotCommand[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedDomain, setSelectedDomain] = useState<string>("all")
  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [sortBy, setSortBy] = useState<string>("name")
  const [filterOpen, setFilterOpen] = useState(false)
  
  // Edit dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingCommand, setEditingCommand] = useState<HotCommand | null>(null)
  const [editForm, setEditForm] = useState({
    command_name: '',
    display_name: '',
    description: '',
    domain: '',
    category: '',
    tags: [] as string[],
    is_public: false
  })
  const [updating, setUpdating] = useState(false)
  
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

  // Load commands and metadata from API
  useEffect(() => {
    const loadCommands = async () => {
      try {
        // Load both user's commands and public commands
        const [myCommands, publicCommands] = await Promise.all([
          hotCommandsApi.getMyCommands(),
          hotCommandsApi.getPublicCommands()
        ])
        
        // Combine and deduplicate commands
        const allCommands = [...myCommands, ...publicCommands.filter(
          pub => !myCommands.find(my => my.id === pub.id)
        )]
        
        setCommands(allCommands)
      } catch (error) {
        console.error('Failed to load commands:', error)
        // Fallback to empty array on error
        setCommands([])
      }
    }

    const loadMetadata = async () => {
      try {
        setMetadataLoading(true)
        const meta = await hotCommandsApi.getHotCommandsMetadata()
        setMetadata(meta)
      } catch (error) {
        console.error('Failed to load metadata:', error)
        // Keep default empty arrays
      } finally {
        setMetadataLoading(false)
      }
    }

    loadCommands()
    loadMetadata()
  }, [])

  const filteredCommands = commands.filter(cmd => {
    const matchesSearch = !searchQuery || 
      cmd.command_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cmd.display_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cmd.description?.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesDomain = selectedDomain === "all" || cmd.domain === selectedDomain
    const matchesCategory = selectedCategory === "all" || cmd.category === selectedCategory
    
    return matchesSearch && matchesDomain && matchesCategory
  })

  const sortedCommands = [...filteredCommands].sort((a, b) => {
    switch (sortBy) {
      case "rating":
        return b.rating - a.rating
      case "usage":
        return b.usage_count - a.usage_count
      case "recent":
        return new Date(b.last_used || 0).getTime() - new Date(a.last_used || 0).getTime()
      default:
        return a.command_name.localeCompare(b.command_name)
    }
  })

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star 
        key={i} 
        className={`h-3 w-3 ${i < Math.round(rating) ? 'fill-yellow-400 text-yellow-400' : 'text-slate-600'}`} 
      />
    ))
  }

  const formatLastUsed = (dateStr?: string) => {
    if (!dateStr) return "Never"
    const date = new Date(dateStr)
    const now = new Date()
    const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const openEditDialog = (command: HotCommand) => {
    setEditingCommand(command)
    setEditForm({
      command_name: command.command_name,
      display_name: command.display_name || '',
      description: command.description || '',
      domain: command.domain || '',
      category: command.category || '',
      tags: command.tags || [],
      is_public: command.is_public
    })
    setEditDialogOpen(true)
  }

  const handleUpdateCommand = async () => {
    if (!editingCommand) return
    
    try {
      setUpdating(true)
      
      await hotCommandsApi.updateCommand(editingCommand.id, {
        command_name: editForm.command_name,
        display_name: editForm.display_name || undefined,
        description: editForm.description || undefined,
        domain: editForm.domain || undefined,
        category: editForm.category || undefined,
        tags: editForm.tags.length > 0 ? editForm.tags : undefined,
        is_public: editForm.is_public
      })
      
      // Update the command in the local state
      setCommands(prev => prev.map(cmd => 
        cmd.id === editingCommand.id 
          ? { ...cmd, ...editForm }
          : cmd
      ))
      
      toast.success('Command updated successfully!')
      setEditDialogOpen(false)
      setEditingCommand(null)
      
    } catch (error) {
      console.error('Error updating command:', error)
      toast.error('Failed to update command')
    } finally {
      setUpdating(false)
    }
  }

  const handleTagsChange = (tagsString: string) => {
    const tags = tagsString.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0)
    setEditForm(prev => ({ ...prev, tags }))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Hot Commands</h1>
          <p className="text-slate-400 mt-1">Manage your saved query shortcuts</p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700">
          + Create Command
        </Button>
      </div>

      {/* Search and Filters */}
      <Card className="bg-[#252547] border-[#3a3a5e] p-6">
        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search commands..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-[#1e1e38] border-[#3a3a5e] text-white placeholder-slate-400"
            />
          </div>

          {/* Filter Toggle */}
          <Button 
            variant="outline" 
            onClick={() => setFilterOpen(!filterOpen)}
            className="border-[#3a3a5e] text-slate-400 hover:text-white hover:bg-[#3a3a5e]"
          >
            <Filter className="h-4 w-4 mr-2" />
            Filter
          </Button>
        </div>

        {/* Expanded Filters */}
        {filterOpen && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Domain</label>
              <Select value={selectedDomain} onValueChange={setSelectedDomain}>
                <SelectTrigger className="bg-[#1e1e38] border-[#3a3a5e] text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                  <SelectItem value="all">All Domains</SelectItem>
                  {metadata.domains.map(domain => (
                    <SelectItem key={domain} value={domain}>{domain}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Category</label>
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="bg-[#1e1e38] border-[#3a3a5e] text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                  <SelectItem value="all">All Categories</SelectItem>
                  {metadata.categories.map(category => (
                    <SelectItem key={category} value={category}>{category}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Sort By</label>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="bg-[#1e1e38] border-[#3a3a5e] text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                  <SelectItem value="name">Name</SelectItem>
                  <SelectItem value="rating">Rating</SelectItem>
                  <SelectItem value="usage">Usage Count</SelectItem>
                  <SelectItem value="recent">Recently Used</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </Card>

      {/* Results Count */}
      <div className="flex justify-between items-center text-slate-400 text-sm">
        <span>{sortedCommands.length} commands found</span>
      </div>

      {/* Commands Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {sortedCommands.map((command) => (
          <Card key={command.id} className="bg-[#252547] border-[#3a3a5e] p-6 hover:bg-[#2a2a52] transition-colors">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <h3 className="text-lg font-semibold text-white truncate">
                    {command.display_name || command.command_name}
                  </h3>
                  {command.is_public && (
                    <Badge className="bg-green-600/20 text-green-400 text-xs">Public</Badge>
                  )}
                </div>
                <p className="text-slate-400 text-sm font-mono">/{command.command_name}</p>
              </div>
              
              <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-white">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </div>

            {/* Domain/Category */}
            <div className="flex items-center space-x-2 mb-3">
              <Badge variant="outline" className="text-xs text-slate-300 border-slate-600">
                {command.domain}/{command.category}
              </Badge>
            </div>

            {/* Description */}
            <p className="text-slate-300 text-sm mb-4 line-clamp-2">
              {command.description || "No description provided"}
            </p>

            {/* Rating and Stats */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-1">
                {renderStars(command.rating)}
                <span className="text-slate-400 text-xs ml-1">({command.rating_count})</span>
              </div>
              <div className="text-slate-400 text-xs">
                {command.usage_count} uses • {formatLastUsed(command.last_used)}
              </div>
            </div>

            {/* Tags */}
            {command.tags && command.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-4">
                {command.tags.slice(0, 3).map((tag, index) => (
                  <Badge key={index} className="bg-slate-700/50 text-slate-300 text-xs">
                    {tag}
                  </Badge>
                ))}
                {command.tags.length > 3 && (
                  <Badge className="bg-slate-700/50 text-slate-300 text-xs">
                    +{command.tags.length - 3}
                  </Badge>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex space-x-2">
              <Button className="flex-1 bg-blue-600 hover:bg-blue-700 text-sm">
                <Play className="h-3 w-3 mr-1" />
                Run
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => openEditDialog(command)}
                className="border-[#3a3a5e] text-slate-400 hover:text-white hover:bg-[#3a3a5e]"
              >
                <Edit3 className="h-3 w-3" />
              </Button>
              {command.user_id === 1 && ( // Current demo user ID
                <Button 
                  variant="outline" 
                  size="sm"
                  className="border-[#3a3a5e] text-slate-400 hover:text-white hover:bg-[#3a3a5e]"
                >
                  <Share className="h-3 w-3" />
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {sortedCommands.length === 0 && (
        <Card className="bg-[#252547] border-[#3a3a5e] p-12 text-center">
          <div className="text-slate-400 mb-4">
            <svg className="h-12 w-12 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2V9a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">No commands found</h3>
          <p className="text-slate-400 mb-6">
            {searchQuery ? 'Try adjusting your search criteria' : 'Create your first hot command to get started'}
          </p>
          <Button className="bg-blue-600 hover:bg-blue-700">
            + Create Command
          </Button>
        </Card>
      )}

      {/* Edit Command Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl bg-[#1e1e38] border-[#3a3a5e] text-white">
          <DialogHeader>
            <DialogTitle className="text-white">Edit Hot Command</DialogTitle>
            <DialogDescription className="text-slate-400">
              Update your hot command settings and properties
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Command Name */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="command_name" className="text-slate-300">Command Name *</Label>
                <Input
                  id="command_name"
                  value={editForm.command_name}
                  onChange={(e) => setEditForm(prev => ({ ...prev, command_name: e.target.value }))}
                  placeholder="my_command"
                  className="bg-[#252547] border-[#3a3a5e] text-white placeholder-slate-400"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Letters, numbers, and underscores only
                </p>
              </div>

              <div>
                <Label htmlFor="display_name" className="text-slate-300">Display Name</Label>
                <Input
                  id="display_name"
                  value={editForm.display_name}
                  onChange={(e) => setEditForm(prev => ({ ...prev, display_name: e.target.value }))}
                  placeholder="My Command"
                  className="bg-[#252547] border-[#3a3a5e] text-white placeholder-slate-400"
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <Label htmlFor="description" className="text-slate-300">Description</Label>
              <Textarea
                id="description"
                value={editForm.description}
                onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Command description..."
                rows={3}
                className="bg-[#252547] border-[#3a3a5e] text-white placeholder-slate-400"
              />
            </div>

            {/* Domain and Category */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="domain" className="text-slate-300">Domain</Label>
                <Select value={editForm.domain} onValueChange={(value) => setEditForm(prev => ({ ...prev, domain: value }))}>
                  <SelectTrigger className="bg-[#252547] border-[#3a3a5e] text-white">
                    <SelectValue placeholder="Select domain" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                    <SelectItem value="">Select domain...</SelectItem>
                    {metadata.domains.map(domain => (
                      <SelectItem key={domain} value={domain}>{domain}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="category" className="text-slate-300">Category</Label>
                <Select value={editForm.category} onValueChange={(value) => setEditForm(prev => ({ ...prev, category: value }))}>
                  <SelectTrigger className="bg-[#252547] border-[#3a3a5e] text-white">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                    <SelectItem value="">Select category...</SelectItem>
                    {metadata.categories.map(category => (
                      <SelectItem key={category} value={category}>{category}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Tags */}
            <div>
              <Label htmlFor="tags" className="text-slate-300">Tags (comma-separated)</Label>
              <Input
                id="tags"
                value={editForm.tags.join(', ')}
                onChange={(e) => handleTagsChange(e.target.value)}
                placeholder="tag1, tag2, tag3"
                className="bg-[#252547] border-[#3a3a5e] text-white placeholder-slate-400"
              />
            </div>

            {/* Public Switch */}
            <div className="flex items-center space-x-2">
              <Switch
                id="is_public"
                checked={editForm.is_public}
                onCheckedChange={(checked) => setEditForm(prev => ({ ...prev, is_public: checked }))}
              />
              <Label htmlFor="is_public" className="text-slate-300">Make command public</Label>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-4 border-t border-[#3a3a5e]">
              <Button 
                variant="outline" 
                onClick={() => setEditDialogOpen(false)}
                className="border-[#3a3a5e] text-slate-400 hover:text-white hover:bg-[#3a3a5e]"
              >
                <X className="h-4 w-4 mr-1" />
                Cancel
              </Button>
              <Button 
                onClick={handleUpdateCommand} 
                disabled={updating || !editForm.command_name}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {updating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-1" />
                    Update Command
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}