// API service for spaces management in ThinkForge
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Space interfaces based on backend schemas
interface Space {
  id: number;
  name: string;
  display_name?: string;
  description?: string;
  space_type: 'personal' | 'team' | 'public' | 'temporary';
  content_type: 'query_result' | 'template' | 'visualization' | 'report' | 'dashboard' | 'dataset' | 'webpage';
  is_template: boolean;
  is_active: boolean;
  is_public: boolean;
  
  // Owner and metadata
  owner_id: number;
  created_at: string;
  updated_at: string;
  last_accessed?: string;
  
  // Content information
  storage_path?: string;
  storage_backend: 'local' | 's3' | 'gcs' | 'azure';
  storage_size_bytes: number;
  external_url?: string;
  
  // Template information
  template_parameters?: TemplateParameter[];
  template_schema?: any;
  base_query?: string;
  source_query?: string;
  
  // Categorization
  domain?: string;
  category?: string;
  tags: string[];
  
  // Usage stats
  view_count: number;
  share_count: number;
  execution_count: number;
  
  // Scheduling
  schedule_type: 'none' | 'interval' | 'cron' | 'webhook';
  schedule_config: any;
  next_execution?: string;
  last_execution?: string;
  is_scheduled_active: boolean;
  
  // Sharing
  shared_with?: number[];
  team_id?: string;
  
  // Expiration
  expires_at?: string;
  auto_cleanup: boolean;
  retention_days?: number;
}

interface TemplateParameter {
  name: string;
  type: string;
  required: boolean;
  description?: string;
  default_value?: any;
}

interface SpaceListResponse {
  spaces: Space[];
  total: number;
  skip: number;
  limit: number;
}

interface SpaceCreate {
  name: string;
  display_name?: string;
  description?: string;
  space_type?: 'personal' | 'team' | 'public' | 'temporary';
  content_type?: 'query_result' | 'template' | 'visualization' | 'report' | 'dashboard' | 'dataset' | 'webpage';
  domain?: string;
  category?: string;
  tags?: string[];
  is_public?: boolean;
  
  // Template functionality
  is_template?: boolean;
  template_parameters?: TemplateParameter[];
  template_schema?: any;
  base_query?: string;
  source_query?: string;
  
  // Content
  content_data?: any;
  content_metadata?: any;
  
  // Storage
  storage_backend?: 'local' | 's3' | 'gcs' | 'azure';
  
  // Scheduling
  schedule_type?: 'none' | 'interval' | 'cron' | 'webhook';
  schedule_config?: any;
  
  // Sharing
  shared_with?: number[];
  team_id?: string;
  
  // Expiration
  expires_at?: string;
  auto_cleanup?: boolean;
  retention_days?: number;
}

interface SpaceUpdate {
  display_name?: string;
  description?: string;
  space_type?: 'personal' | 'team' | 'public' | 'temporary';
  content_type?: 'query_result' | 'template' | 'visualization' | 'report' | 'dashboard' | 'dataset' | 'webpage';
  domain?: string;
  category?: string;
  tags?: string[];
  is_public?: boolean;
  
  // Template updates
  template_parameters?: TemplateParameter[];
  template_schema?: any;
  base_query?: string;
  source_query?: string;
  
  // Content updates
  content_data?: any;
  content_metadata?: any;
  
  // Scheduling updates
  schedule_type?: 'none' | 'interval' | 'cron' | 'webhook';
  schedule_config?: any;
  is_scheduled_active?: boolean;
  
  // Sharing updates
  shared_with?: number[];
  team_id?: string;
  
  // Expiration updates
  expires_at?: string;
  auto_cleanup?: boolean;
  retention_days?: number;
}

interface SpaceAccess {
  id: number;
  space_id: number;
  user_id: number;
  granted_by: number;
  access_level: 'view' | 'comment' | 'edit' | 'admin';
  is_active: boolean;
  access_count: number;
  last_accessed?: string;
  expires_at?: string;
  restrictions?: any;
  created_at: string;
}

interface SpaceShareRequest {
  user_id: number;
  access_level: 'view' | 'comment' | 'edit' | 'admin';
  expires_at?: string;
  restrictions?: any;
}

interface TemplateExecuteRequest {
  parameters: Record<string, any>;
  save_result?: boolean;
  result_name?: string;
  storage_backend?: 'local' | 's3' | 'gcs' | 'azure';
}

interface SpaceExecutionResult {
  execution_id: string;
  space_id: number;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  result_data?: any;
  error_message?: string;
  row_count?: number;
  storage_path?: string;
  public_url?: string;
  parameters_used?: Record<string, any>;
}

interface SpaceAnalytics {
  space_id: number;
  total_views: number;
  unique_viewers: number;
  total_executions: number;
  avg_execution_time_ms?: number;
  last_30_days_views: number;
  last_30_days_executions: number;
  top_parameters?: Array<{ parameter: string; usage_count: number; avg_value: string }>;
  performance_metrics?: Record<string, any>;
}

interface CacheToSpaceRequest {
  cache_id: number;
  space_name: string;
  display_name?: string;
  description?: string;
  make_template?: boolean;
  copy_content?: boolean;
}

interface SpaceFromCacheResponse {
  space: Space;
  cache_entry_id: number;
  conversion_notes: string[];
  template_created: boolean;
}

interface SpaceSearchRequest {
  query?: string;
  space_types?: ('personal' | 'team' | 'public' | 'temporary')[];
  content_types?: ('query_result' | 'template' | 'visualization' | 'report' | 'dashboard' | 'dataset' | 'webpage')[];
  domains?: string[];
  tags?: string[];
  is_template?: boolean;
  is_scheduled?: boolean;
  created_after?: string;
  created_before?: string;
  last_modified_after?: string;
  last_modified_before?: string;
  min_views?: number;
  max_views?: number;
  owner_ids?: number[];
  shared_with_me?: boolean;
  my_spaces?: boolean;
}

// Spaces API service
const spacesApi = {
  // Get all spaces with filtering and pagination
  async getSpaces(
    skip: number = 0,
    limit: number = 50,
    filters?: {
      space_type?: 'personal' | 'team' | 'public' | 'temporary';
      content_type?: 'query_result' | 'template' | 'visualization' | 'report' | 'dashboard' | 'dataset' | 'webpage';
      domain?: string;
      is_template?: boolean;
      is_public?: boolean;
      is_scheduled?: boolean;
      owner_id?: number;
      search?: string;
    },
    user_id?: number
  ): Promise<SpaceListResponse> {
    try {
      let url = `${API_BASE}/v1/spaces?skip=${skip}&limit=${limit}`;
      
      if (filters?.space_type) {
        url += `&space_type=${encodeURIComponent(filters.space_type)}`;
      }
      if (filters?.content_type) {
        url += `&content_type=${encodeURIComponent(filters.content_type)}`;
      }
      if (filters?.domain) {
        url += `&domain=${encodeURIComponent(filters.domain)}`;
      }
      if (filters?.is_template !== undefined) {
        url += `&is_template=${filters.is_template}`;
      }
      if (filters?.is_public !== undefined) {
        url += `&is_public=${filters.is_public}`;
      }
      if (filters?.is_scheduled !== undefined) {
        url += `&is_scheduled=${filters.is_scheduled}`;
      }
      if (filters?.owner_id) {
        url += `&owner_id=${filters.owner_id}`;
      }
      if (filters?.search) {
        url += `&search=${encodeURIComponent(filters.search)}`;
      }
      if (user_id) {
        url += `&user_id=${user_id}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching spaces:', error);
      throw error;
    }
  },

  // Get a single space by ID
  async getSpace(id: number, user_id?: number): Promise<Space> {
    try {
      let url = `${API_BASE}/v1/spaces/${id}`;
      if (user_id) {
        url += `?user_id=${user_id}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching space ${id}:`, error);
      throw error;
    }
  },

  // Create a new space
  async createSpace(space: SpaceCreate, user_id: number): Promise<Space> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces?user_id=${user_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(space),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error creating space:', error);
      throw error;
    }
  },

  // Update an existing space
  async updateSpace(id: number, space: SpaceUpdate, user_id: number): Promise<Space> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/${id}?user_id=${user_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(space),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error updating space ${id}:`, error);
      throw error;
    }
  },

  // Delete a space
  async deleteSpace(id: number, user_id: number, hard_delete: boolean = false): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/${id}?user_id=${user_id}&hard_delete=${hard_delete}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error(`Error deleting space ${id}:`, error);
      throw error;
    }
  },

  // Execute a space (regular execution)
  async executeSpace(id: number, user_id: number, parameters?: Record<string, any>): Promise<SpaceExecutionResult> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/${id}/execute?user_id=${user_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ parameters }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error executing space ${id}:`, error);
      throw error;
    }
  },

  // Execute a template space with parameters
  async executeTemplate(id: number, request: TemplateExecuteRequest, user_id: number): Promise<SpaceExecutionResult> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/${id}/execute-template?user_id=${user_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error executing template space ${id}:`, error);
      throw error;
    }
  },

  // Share a space with another user
  async shareSpace(id: number, shareRequest: SpaceShareRequest, user_id: number): Promise<SpaceAccess> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/${id}/share?user_id=${user_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(shareRequest),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error sharing space ${id}:`, error);
      throw error;
    }
  },

  // Revoke access to a space
  async revokeSpaceAccess(space_id: number, user_id: number, requester_id: number): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/${space_id}/share/${user_id}?requester_id=${requester_id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error(`Error revoking access to space ${space_id}:`, error);
      throw error;
    }
  },

  // Get analytics for a space
  async getSpaceAnalytics(id: number, user_id: number, days: number = 30): Promise<SpaceAnalytics> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/${id}/analytics?user_id=${user_id}&days=${days}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching analytics for space ${id}:`, error);
      throw error;
    }
  },

  // Create space from cache entry
  async createSpaceFromCache(request: CacheToSpaceRequest, user_id: number): Promise<SpaceFromCacheResponse> {
    try {
      const response = await fetch(`${API_BASE}/v1/spaces/from-cache?user_id=${user_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error creating space from cache:', error);
      throw error;
    }
  },

  // Advanced search for spaces
  async searchSpaces(
    searchRequest: SpaceSearchRequest,
    user_id?: number,
    skip: number = 0,
    limit: number = 50
  ): Promise<SpaceListResponse> {
    try {
      let url = `${API_BASE}/v1/spaces/search?skip=${skip}&limit=${limit}`;
      if (user_id) {
        url += `&user_id=${user_id}`;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchRequest),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error searching spaces:', error);
      throw error;
    }
  },

  // Get my spaces (spaces owned by user)
  async getMySpaces(user_id: number, skip: number = 0, limit: number = 50): Promise<SpaceListResponse> {
    return this.getSpaces(skip, limit, { owner_id: user_id }, user_id);
  },

  // Get spaces shared with me
  async getSharedWithMe(user_id: number, skip: number = 0, limit: number = 50): Promise<SpaceListResponse> {
    return this.searchSpaces({ shared_with_me: true }, user_id, skip, limit);
  },

  // Get team/public spaces
  async getTeamSpaces(skip: number = 0, limit: number = 50): Promise<SpaceListResponse> {
    return this.getSpaces(skip, limit, { 
      space_type: 'team',
      is_public: true 
    });
  },

  // Get template spaces
  async getTemplateSpaces(skip: number = 0, limit: number = 50): Promise<SpaceListResponse> {
    return this.getSpaces(skip, limit, { is_template: true });
  },

  // Get scheduled spaces
  async getScheduledSpaces(skip: number = 0, limit: number = 50): Promise<SpaceListResponse> {
    return this.getSpaces(skip, limit, { is_scheduled: true });
  },

  // Utility function to format space type display name
  formatSpaceType(spaceType: string): string {
    return spaceType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  },

  // Utility function to format content type display name
  formatContentType(contentType: string): string {
    return contentType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  },

  // Utility function to get content type icon
  getContentTypeIcon(contentType: string): string {
    const icons: Record<string, string> = {
      'query_result': '📊',
      'template': '📋',
      'visualization': '📈',
      'report': '📄',
      'dashboard': '📱',
      'dataset': '🗃️',
      'webpage': '🌐'
    };
    return icons[contentType] || '📊';
  },

  // Utility function to get space type color
  getSpaceTypeColor(spaceType: string): string {
    const colors: Record<string, string> = {
      'personal': 'text-blue-400',
      'team': 'text-green-400',
      'public': 'text-purple-400',
      'temporary': 'text-yellow-400'
    };
    return colors[spaceType] || 'text-gray-400';
  },

  // Utility function to format execution status
  formatExecutionStatus(status: string): { text: string; color: string } {
    const statusMap: Record<string, { text: string; color: string }> = {
      'completed': { text: 'Completed', color: 'text-green-400' },
      'failed': { text: 'Failed', color: 'text-red-400' },
      'running': { text: 'Running', color: 'text-blue-400' },
      'pending': { text: 'Pending', color: 'text-yellow-400' }
    };
    return statusMap[status] || { text: status, color: 'text-gray-400' };
  },

  // Utility function to format file size
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // Utility function to format relative time
  formatRelativeTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return diffMinutes <= 0 ? 'Just now' : `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) {
        return `${diffDays}d ago`;
      } else {
        return date.toLocaleDateString();
      }
    }
  }
};

// Explicit named exports for better module compatibility
export type {
  Space,
  TemplateParameter,
  SpaceListResponse,
  SpaceCreate,
  SpaceUpdate,
  SpaceAccess,
  SpaceShareRequest,
  TemplateExecuteRequest,
  SpaceExecutionResult,
  SpaceAnalytics,
  CacheToSpaceRequest,
  SpaceFromCacheResponse,
  SpaceSearchRequest
};

export default spacesApi;