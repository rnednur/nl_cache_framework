// Hot Commands API service for ThinkForge integration
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Hot Commands interfaces
export interface HotCommand {
  id: number;
  command_name: string;
  display_name?: string;
  description?: string;
  query_text: string;
  query_type: string;
  domain?: string;
  category?: string;
  tags: string[];
  parameters: Record<string, any>;
  status: string;
  is_public: boolean;
  is_template: boolean;
  usage_count: number;
  success_rate: number;
  avg_execution_time?: number;
  last_used?: string;
  rating: number;
  rating_count: number;
  output_format: string;
  created_at: string;
  updated_at: string;
  user_id: number;
  cache_entry_id?: number;
  source_template_type?: string;
  source_reasoning?: string;
  source_tags?: Record<string, any>;
  source_execution_stats?: Record<string, any>;
}

export interface Space {
  id: number;
  name: string;
  display_name?: string;
  description?: string;
  space_type: string;
  content_type: string;
  is_active: boolean;
  content_data?: Record<string, any>;
  content_metadata: Record<string, any>;
  domain?: string;
  category?: string;
  tags: string[];
  is_public: boolean;
  view_count: number;
  share_count: number;
  last_accessed?: string;
  created_at: string;
  updated_at: string;
  owner_id: number;
}

export interface CommandSuggestion {
  command_name: string;
  display_name?: string;
  description?: string;
  similarity_score: number;
  usage_count: number;
  rating: number;
}

export interface DashboardStats {
  total_commands: number;
  total_executions: number;
  avg_success_rate: number;
  recent_activity: Array<{
    command_name: string;
    execution_count: number;
    last_executed: string;
  }>;
  popular_commands: HotCommand[];
  domains_used: Array<{
    domain: string;
    count: number;
  }>;
}

// Cache Entry interfaces
export interface CacheEntry {
  id: number;
  nl_query: string;
  template_type: string;
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
  reasoning_trace?: string;
  tags?: Record<string, any>;
  execution_count: number;
  success_rate: number;
  complexity_level?: string;
  health_status?: string;
  last_executed?: string;
  created_at: string;
  updated_at: string;
  has_hot_command: boolean;
  hot_command_name?: string;
  hot_command_id?: number;
}

export interface CacheEntryDetail {
  id: number;
  nl_query: string;
  template: string;
  template_type: string;
  is_template: boolean;
  entity_replacements?: Record<string, any>;
  reasoning_trace?: string;
  tags?: Record<string, any>;
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
  status: string;
  tool_capabilities?: string[];
  execution_config?: Record<string, any>;
  health_status?: string;
  recipe_steps?: any[];
  required_tools?: number[];
  execution_time_estimate?: number;
  complexity_level?: string;
  success_rate?: number;
  last_executed?: string;
  execution_count?: number;
  created_at: string;
  updated_at: string;
  has_hot_command: boolean;
  hot_command?: any;
}

export interface ExecuteCommandRequest {
  command: string;
  parameters?: Record<string, any>;
  domain?: string;
  category?: string;
  session_id?: string;
}

export interface ExecuteCommandResponse {
  success: boolean;
  data?: any;
  message?: string;
  error?: string;
  execution_time_ms: number;
  result_rows?: number;
  sql_query?: string;
  metadata: Record<string, any>;
}

// API functions
export const hotCommandsApi = {
  // Hot Commands CRUD
  async getMyCommands(params?: {
    domain?: string;
    category?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<HotCommand[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain) queryParams.set('domain', params.domain);
    if (params?.category) queryParams.set('category', params.category);
    if (params?.status) queryParams.set('status', params.status);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const response = await fetch(`${API_BASE}/api/hot-commands/my?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch hot commands');
    return response.json();
  },

  async getPublicCommands(params?: {
    domain?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }): Promise<HotCommand[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain) queryParams.set('domain', params.domain);
    if (params?.category) queryParams.set('category', params.category);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const response = await fetch(`${API_BASE}/api/hot-commands/public?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch public hot commands');
    return response.json();
  },

  async createCommand(command: {
    command_name: string;
    display_name?: string;
    description?: string;
    query_text: string;
    query_type?: string;
    domain?: string;
    category?: string;
    tags?: string[];
    parameters?: Record<string, any>;
    is_public?: boolean;
  }): Promise<HotCommand> {
    const response = await fetch(`${API_BASE}/api/hot-commands`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    });
    if (!response.ok) throw new Error('Failed to create hot command');
    return response.json();
  },

  async getCommand(id: number): Promise<HotCommand> {
    const response = await fetch(`${API_BASE}/api/hot-commands/${id}`);
    if (!response.ok) throw new Error('Failed to fetch hot command');
    return response.json();
  },

  async updateCommand(id: number, updates: Partial<HotCommand>): Promise<HotCommand> {
    const response = await fetch(`${API_BASE}/api/hot-commands/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update hot command');
    return response.json();
  },

  async deleteCommand(id: number): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/api/hot-commands/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete hot command');
    return response.json();
  },

  // Command execution
  async executeCommand(request: ExecuteCommandRequest): Promise<ExecuteCommandResponse> {
    const response = await fetch(`${API_BASE}/api/execute-command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error('Failed to execute command');
    return response.json();
  },

  async getCommandSuggestions(query: string, params?: {
    domain?: string;
    limit?: number;
  }): Promise<CommandSuggestion[]> {
    const queryParams = new URLSearchParams({ query });
    if (params?.domain) queryParams.set('domain', params.domain);
    if (params?.limit) queryParams.set('limit', params.limit.toString());

    const response = await fetch(`${API_BASE}/api/command-suggestions?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch command suggestions');
    return response.json();
  },

  // Spaces management
  async getMySpaces(params?: {
    space_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<Space[]> {
    const queryParams = new URLSearchParams();
    if (params?.space_type) queryParams.set('space_type', params.space_type);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const response = await fetch(`${API_BASE}/api/spaces/my?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch spaces');
    return response.json();
  },

  async createSpace(space: {
    name: string;
    display_name?: string;
    description?: string;
    space_type?: string;
    content_type?: string;
    content_data?: Record<string, any>;
    domain?: string;
    category?: string;
    tags?: string[];
    is_public?: boolean;
  }): Promise<Space> {
    const response = await fetch(`${API_BASE}/api/spaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(space),
    });
    if (!response.ok) throw new Error('Failed to create space');
    return response.json();
  },

  // Analytics
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await fetch(`${API_BASE}/api/analytics/dashboard`);
    if (!response.ok) throw new Error('Failed to fetch dashboard stats');
    return response.json();
  },

  // Cache Entry Integration
  async getAvailableCacheEntries(params?: {
    template_type?: string;
    catalog_type?: string;
    catalog_subtype?: string;
    limit?: number;
    offset?: number;
  }): Promise<CacheEntry[]> {
    const queryParams = new URLSearchParams();
    if (params?.template_type) queryParams.set('template_type', params.template_type);
    if (params?.catalog_type) queryParams.set('catalog_type', params.catalog_type);
    if (params?.catalog_subtype) queryParams.set('catalog_subtype', params.catalog_subtype);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const response = await fetch(`${API_BASE}/api/cache-entries/available?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch cache entries');
    return response.json();
  },

  async getCacheEntryDetails(id: number): Promise<CacheEntryDetail> {
    const response = await fetch(`${API_BASE}/api/cache-entries/${id}/details`);
    if (!response.ok) throw new Error('Failed to fetch cache entry details');
    return response.json();
  },

  async createHotCommandFromCache(request: {
    cache_entry_id: number;
    command_name: string;
    display_name?: string;
    description?: string;
    is_public?: boolean;
    tags?: string[];
  }): Promise<HotCommand> {
    const response = await fetch(`${API_BASE}/api/cache-entries/create-command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error('Failed to create hot command from cache entry');
    return response.json();
  },

  async getHotCommandsMetadata(): Promise<{
    domains: string[];
    categories: string[];
    tags: string[];
    query_types: string[];
    template_types: string[];
  }> {
    const response = await fetch(`${API_BASE}/api/hot-commands/metadata`);
    if (!response.ok) throw new Error('Failed to fetch hot commands metadata');
    return response.json();
  },
};

export default hotCommandsApi;