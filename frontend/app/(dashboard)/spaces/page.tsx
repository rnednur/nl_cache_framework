'use client'

import { useState, useEffect } from "react"
import { Share2, Eye, Users, Globe, Lock, MoreVertical, Plus, Clock, Calendar, ExternalLink, Settings, Play } from "lucide-react"
import { Button } from "@/app/components/ui/button"
import { Card } from "@/app/components/ui/card"
import { Badge } from "@/app/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/app/components/ui/tabs"
import spacesApi from "@/app/services/spaces-api"
import type { Space, SpaceListResponse } from "@/app/services/spaces-api"
import SpaceCreateForm from "@/app/components/SpaceCreateForm"

export default function Spaces() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [activeTab, setActiveTab] = useState("my-spaces")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState(0)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [currentUserId] = useState(1) // Mock user ID

  const loadSpaces = async (tab: string) => {
    try {
      setLoading(true)
      setError(null)
      
      let response: SpaceListResponse
      
      switch (tab) {
        case 'my-spaces':
          response = await spacesApi.getMySpaces(currentUserId)
          break
        case 'shared':
          response = await spacesApi.getSharedWithMe(currentUserId)
          break
        case 'team':
          response = await spacesApi.getTeamSpaces()
          break
        case 'templates':
          response = await spacesApi.getTemplateSpaces()
          break
        default:
          response = await spacesApi.getMySpaces(currentUserId)
      }
      
      setSpaces(response.spaces)
      setTotalCount(response.total)
      
    } catch (err) {
      console.error('Error loading spaces:', err)
      setError('Failed to load spaces')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSpaces(activeTab)
  }, [activeTab])

  const handleTabChange = (tab: string) => {
    setActiveTab(tab)
  }

  const handleSpaceCreated = () => {
    setShowCreateForm(false)
    loadSpaces(activeTab)
  }

  const handleExecuteSpace = async (space: Space) => {
    try {
      const result = await spacesApi.executeSpace(space.id, currentUserId)
      console.log('Execution result:', result)
      // Handle execution result
    } catch (err) {
      console.error('Error executing space:', err)
    }
  }

  const formatRelativeTime = (dateString: string) => {
    return spacesApi.formatRelativeTime(dateString)
  }

  const getSpaceTypeIcon = (spaceType: string) => {
    switch (spaceType) {
      case 'personal':
        return <Lock className="h-4 w-4" />
      case 'team':
        return <Users className="h-4 w-4" />
      case 'public':
        return <Globe className="h-4 w-4" />
      case 'temporary':
        return <Clock className="h-4 w-4" />
      default:
        return <Lock className="h-4 w-4" />
    }
  }

  const getContentTypeIcon = (contentType: string) => {
    return spacesApi.getContentTypeIcon(contentType)
  }

  if (loading && spaces.length === 0) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-500">Loading spaces...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Spaces</h1>
          <p className="text-gray-600">Manage your shared workspaces and collaborative content</p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Space
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="my-spaces">My Spaces</TabsTrigger>
          <TabsTrigger value="shared">Shared With Me</TabsTrigger>
          <TabsTrigger value="team">Team Spaces</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {spaces.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <Share2 className="h-12 w-12 mx-auto" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No spaces found</h3>
              <p className="text-gray-500 mb-4">
                {activeTab === 'my-spaces' 
                  ? "You haven't created any spaces yet."
                  : "No spaces available in this category."
                }
              </p>
              {activeTab === 'my-spaces' && (
                <Button onClick={() => setShowCreateForm(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Space
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {spaces.map((space) => (
                <Card key={space.id} className="hover:shadow-lg transition-shadow">
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{getContentTypeIcon(space.content_type)}</span>
                        <div className="flex items-center space-x-1">
                          {getSpaceTypeIcon(space.space_type)}
                          <span className={`text-xs ${spacesApi.getSpaceTypeColor(space.space_type)}`}>
                            {spacesApi.formatSpaceType(space.space_type)}
                          </span>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </div>

                    <h3 className="font-semibold text-lg mb-2">
                      {space.display_name || space.name}
                    </h3>
                    
                    {space.description && (
                      <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                        {space.description}
                      </p>
                    )}

                    <div className="flex flex-wrap gap-1 mb-4">
                      {space.is_template && (
                        <Badge variant="secondary">Template</Badge>
                      )}
                      {space.is_public && (
                        <Badge variant="outline">Public</Badge>
                      )}
                      {space.tags?.slice(0, 2).map((tag) => (
                        <Badge key={tag} variant="outline">{tag}</Badge>
                      ))}
                      {space.tags && space.tags.length > 2 && (
                        <Badge variant="outline">+{space.tags.length - 2}</Badge>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                      <div className="flex items-center space-x-4">
                        <span className="flex items-center">
                          <Eye className="h-4 w-4 mr-1" />
                          {space.view_count}
                        </span>
                        <span className="flex items-center">
                          <Share2 className="h-4 w-4 mr-1" />
                          {space.share_count}
                        </span>
                      </div>
                      <span>{formatRelativeTime(space.updated_at)}</span>
                    </div>

                    <div className="flex space-x-2">
                      <Button 
                        size="sm" 
                        className="flex-1"
                        onClick={() => handleExecuteSpace(space)}
                      >
                        <Play className="h-4 w-4 mr-1" />
                        Execute
                      </Button>
                      <Button size="sm" variant="outline">
                        <Settings className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="outline">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {showCreateForm && (
        <SpaceCreateForm
          isOpen={showCreateForm}
          onClose={() => setShowCreateForm(false)}
          onSpaceCreated={handleSpaceCreated}
          userId={currentUserId}
        />
      )}
    </div>
  )
}