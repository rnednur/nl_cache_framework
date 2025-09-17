import { useState, useEffect } from "react"
import { Share2, Eye, Users, Globe, Lock, MoreVertical, Plus, Clock, Calendar, ExternalLink, Settings, Play, Download } from "lucide-react"
import { Button } from "../components/ui/button"
import { Card } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs"
import spacesApi from "../services/spaces-api"
import type { Space, SpaceListResponse } from "../services/spaces-api"
import SpaceCreateForm from "../components/SpaceCreateForm"

export default function Spaces() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [activeTab, setActiveTab] = useState("my-spaces")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState(0)
  const [showCreateForm, setShowCreateForm] = useState(false)
  
  // Mock user ID - in real app this would come from auth context
  const currentUserId = 1

  // Load spaces based on active tab
  const loadSpaces = async (tab: string) => {
    setLoading(true)
    setError(null)
    
    try {
      let response: SpaceListResponse
      
      switch (tab) {
        case "my-spaces":
          response = await spacesApi.getMySpaces(currentUserId)
          break
        case "shared-with-me":
          response = await spacesApi.getSharedWithMe(currentUserId)
          break
        case "team-spaces":
          response = await spacesApi.getTeamSpaces()
          break
        default:
          response = await spacesApi.getSpaces()
      }
      
      setSpaces(response.spaces)
      setTotalCount(response.total)
    } catch (err) {
      console.error('Error loading spaces:', err)
      setError('Failed to load spaces. Please try again.')
      setSpaces([])
    } finally {
      setLoading(false)
    }
  }

  // Load spaces when component mounts or tab changes
  useEffect(() => {
    loadSpaces(activeTab)
  }, [activeTab])

  // Since we're loading filtered data from API, just return the spaces directly
  const getFilteredSpaces = (filter: string) => {
    return spaces; // API already returns filtered data based on activeTab
  }

  const getContentTypeIcon = (contentType: string) => {
    return spacesApi.getContentTypeIcon(contentType)
  }

  const getSpaceTypeIcon = (space: Space) => {
    if (space.is_public) {
      return <Globe className="h-4 w-4 text-green-400" />
    } else if (space.space_type === "team") {
      return <Users className="h-4 w-4 text-blue-400" />
    } else {
      return <Lock className="h-4 w-4 text-slate-400" />
    }
  }

  const formatDate = (dateStr: string) => {
    return spacesApi.formatRelativeTime(dateStr)
  }

  // Handle space actions
  const handleExecuteSpace = async (space: Space) => {
    try {
      setLoading(true)
      if (space.is_template) {
        // For templates, you'd typically open a parameter form first
        console.log('Template execution requires parameters')
        // TODO: Open parameter form modal
      } else {
        const result = await spacesApi.executeSpace(space.id, currentUserId)
        console.log('Space executed:', result)
        // TODO: Show execution results
      }
    } catch (error) {
      console.error('Error executing space:', error)
      setError('Failed to execute space')
    } finally {
      setLoading(false)
    }
  }

  const handleShareSpace = async (space: Space) => {
    // TODO: Open share modal
    console.log('Share space:', space.id)
  }

  const handleDeleteSpace = async (space: Space) => {
    if (confirm(`Are you sure you want to delete "${space.display_name || space.name}"?`)) {
      try {
        await spacesApi.deleteSpace(space.id, currentUserId)
        loadSpaces(activeTab) // Reload spaces
      } catch (error) {
        console.error('Error deleting space:', error)
        setError('Failed to delete space')
      }
    }
  }

  const SpaceCard = ({ space }: { space: Space }) => (
    <Card className="bg-[#252547] border-[#3a3a5e] p-6 hover:bg-[#2a2a52] transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start space-x-3 flex-1 min-w-0">
          <span className="text-2xl">{getContentTypeIcon(space.content_type)}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <h3 className="text-lg font-semibold text-white truncate">
                {space.display_name || space.name}
              </h3>
              {getSpaceTypeIcon(space)}
              {space.is_template && (
                <Badge className="bg-purple-600/20 text-purple-400 text-xs">
                  Template
                </Badge>
              )}
            </div>
            <p className="text-slate-400 text-sm font-mono">{space.name}</p>
          </div>
        </div>
        
        <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-white">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </div>

      {/* Content Type and Format */}
      <div className="flex items-center space-x-2 mb-3">
        <Badge variant="outline" className="text-xs text-slate-300 border-slate-600 capitalize">
          {spacesApi.formatContentType(space.content_type)}
        </Badge>
        {space.shared_with && space.shared_with.length > 0 && (
          <Badge className="bg-blue-600/20 text-blue-400 text-xs">
            Shared
          </Badge>
        )}
        {space.is_scheduled_active && (
          <Badge className="bg-orange-600/20 text-orange-400 text-xs">
            <Clock className="h-3 w-3 mr-1" />
            Scheduled
          </Badge>
        )}
        {space.external_url && (
          <Badge className="bg-green-600/20 text-green-400 text-xs">
            <ExternalLink className="h-3 w-3 mr-1" />
            Public
          </Badge>
        )}
      </div>

      {/* Description */}
      <p className="text-slate-300 text-sm mb-4 line-clamp-2">
        {space.description || "No description provided"}
      </p>

      {/* Enhanced Info */}
      <div className="mb-4 space-y-2">
        {/* Storage info */}
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>Storage: {space.storage_backend.toUpperCase()}</span>
          <span>{spacesApi.formatFileSize(space.storage_size_bytes)}</span>
        </div>
        
        {/* Execution info for templates */}
        {space.is_template && space.template_parameters && (
          <div className="text-xs text-slate-400">
            <span>{space.template_parameters.length} parameters</span>
          </div>
        )}
        
        {/* Schedule info */}
        {space.is_scheduled_active && space.next_execution && (
          <div className="flex items-center text-xs text-orange-400">
            <Calendar className="h-3 w-3 mr-1" />
            Next: {formatDate(space.next_execution)}
          </div>
        )}
      </div>

      {/* Domain and Category */}
      {(space.domain || space.category) && (
        <div className="flex items-center space-x-2 mb-3 text-xs text-slate-400">
          {space.domain && <span>Domain: {space.domain}</span>}
          {space.domain && space.category && <span>•</span>}
          {space.category && <span>Category: {space.category}</span>}
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-4 text-slate-400 text-xs">
          <div className="flex items-center space-x-1">
            <Eye className="h-3 w-3" />
            <span>{space.view_count}</span>
          </div>
          <div className="flex items-center space-x-1">
            <Share2 className="h-3 w-3" />
            <span>{space.share_count}</span>
          </div>
          <div className="flex items-center space-x-1">
            <Play className="h-3 w-3" />
            <span>{space.execution_count}</span>
          </div>
        </div>
        <div className="text-slate-400 text-xs">
          {formatDate(space.last_accessed || space.created_at)}
        </div>
      </div>

      {/* Tags */}
      {space.tags && space.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {space.tags.slice(0, 3).map((tag, index) => (
            <Badge key={index} className="bg-slate-700/50 text-slate-300 text-xs">
              {tag}
            </Badge>
          ))}
          {space.tags.length > 3 && (
            <Badge className="bg-slate-700/50 text-slate-300 text-xs">
              +{space.tags.length - 3}
            </Badge>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex space-x-2">
        <Button 
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-sm"
          onClick={() => handleExecuteSpace(space)}
          disabled={loading}
        >
          {space.is_template ? (
            <>
              <Settings className="h-3 w-3 mr-1" />
              Execute
            </>
          ) : (
            <>
              <Eye className="h-3 w-3 mr-1" />
              View
            </>
          )}
        </Button>
        <Button 
          variant="outline" 
          size="sm"
          className="border-[#3a3a5e] text-slate-400 hover:text-white hover:bg-[#3a3a5e]"
          onClick={() => handleShareSpace(space)}
        >
          <Share2 className="h-3 w-3" />
        </Button>
        {space.external_url && (
          <Button 
            variant="outline" 
            size="sm"
            className="border-[#3a3a5e] text-slate-400 hover:text-white hover:bg-[#3a3a5e]"
            onClick={() => window.open(space.external_url, '_blank')}
          >
            <ExternalLink className="h-3 w-3" />
          </Button>
        )}
      </div>
    </Card>
  )

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Spaces</h1>
            <p className="text-slate-400 mt-1">Manage your shared query results and data</p>
          </div>
        </div>
        <Card className="bg-[#252547] border-[#3a3a5e] p-12 text-center">
          <div className="text-red-400 mb-4">
            <Share2 className="h-12 w-12 mx-auto mb-4" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Error Loading Spaces</h3>
          <p className="text-slate-400 mb-6">{error}</p>
          <Button 
            className="bg-blue-600 hover:bg-blue-700"
            onClick={() => loadSpaces(activeTab)}
          >
            Try Again
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Spaces</h1>
          <p className="text-slate-400 mt-1">
            Manage your shared query results and data
            {totalCount > 0 && (
              <span className="text-slate-500"> • {totalCount} total spaces</span>
            )}
          </p>
        </div>
        <Button 
          className="bg-blue-600 hover:bg-blue-700"
          onClick={() => setShowCreateForm(true)}
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Space
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 bg-[#252547] border border-[#3a3a5e]">
          <TabsTrigger 
            value="my-spaces"
            className="data-[state=active]:bg-[#3a3a5e] data-[state=active]:text-white"
          >
            My Spaces
          </TabsTrigger>
          <TabsTrigger 
            value="shared-with-me"
            className="data-[state=active]:bg-[#3a3a5e] data-[state=active]:text-white"
          >
            Shared with Me
          </TabsTrigger>
          <TabsTrigger 
            value="team-spaces"
            className="data-[state=active]:bg-[#3a3a5e] data-[state=active]:text-white"
          >
            Team Spaces
          </TabsTrigger>
        </TabsList>

        {/* Loading State */}
        {loading && (
          <div className="mt-6">
            <Card className="bg-[#252547] border-[#3a3a5e] p-12 text-center">
              <div className="text-slate-400 mb-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto mb-4"></div>
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Loading Spaces...</h3>
              <p className="text-slate-400">Please wait while we fetch your spaces</p>
            </Card>
          </div>
        )}

        {/* Content for each tab */}
        {!loading && (
          <>
            <TabsContent value="my-spaces" className="mt-6">
              {getFilteredSpaces("my-spaces").length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                  {getFilteredSpaces("my-spaces").map((space) => (
                    <SpaceCard key={space.id} space={space} />
                  ))}
                </div>
              ) : (
                <Card className="bg-[#252547] border-[#3a3a5e] p-12 text-center">
                  <div className="text-slate-400 mb-4">
                    <Share2 className="h-12 w-12 mx-auto mb-4" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">No spaces yet</h3>
                  <p className="text-slate-400 mb-6">
                    Create your first space to save and share query results
                  </p>
                  <Button 
                    className="bg-blue-600 hover:bg-blue-700"
                    onClick={() => setShowCreateForm(true)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create Space
                  </Button>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="shared-with-me" className="mt-6">
              {getFilteredSpaces("shared-with-me").length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                  {getFilteredSpaces("shared-with-me").map((space) => (
                    <SpaceCard key={space.id} space={space} />
                  ))}
                </div>
              ) : (
                <Card className="bg-[#252547] border-[#3a3a5e] p-12 text-center">
                  <div className="text-slate-400 mb-4">
                    <Users className="h-12 w-12 mx-auto mb-4" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">No shared spaces</h3>
                  <p className="text-slate-400">
                    Spaces shared with you will appear here
                  </p>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="team-spaces" className="mt-6">
              {getFilteredSpaces("team-spaces").length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                  {getFilteredSpaces("team-spaces").map((space) => (
                    <SpaceCard key={space.id} space={space} />
                  ))}
                </div>
              ) : (
                <Card className="bg-[#252547] border-[#3a3a5e] p-12 text-center">
                  <div className="text-slate-400 mb-4">
                    <Globe className="h-12 w-12 mx-auto mb-4" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">No team spaces</h3>
                  <p className="text-slate-400">
                    Public and team spaces will appear here
                  </p>
                </Card>
              )}
            </TabsContent>
          </>
        )}
      </Tabs>

      {/* Create Space Form */}
      <SpaceCreateForm
        isOpen={showCreateForm}
        onClose={() => setShowCreateForm(false)}
        onSpaceCreated={() => loadSpaces(activeTab)}
        userId={currentUserId}
      />
    </div>
  )
}