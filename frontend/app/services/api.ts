// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Cache item interface based on backend API
export interface CacheItem {
  id: number;
  nl_query: string;
  template: string;
  template_type: string;
  is_template: boolean;
  reasoning_trace?: string;
  entity_replacements?: Record<string, any>;
  tags?: Record<string, string[]>;
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
  status: string;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

// Stats interface
export interface CacheStats {
  total_entries: number;
  by_template_type: Record<string, number>;
  recent_usage: Array<{
    date: string;
    count: number;
  }>;
  popular_entries: Array<{
    id: number;
    nl_query: string;
    usage_count: number;
  }>
}

// Usage log interface
export interface UsageLog {
  id: number;
  cache_entry_id?: number;
  timestamp: string; 
  prompt?: string;
  success_status: boolean;
  similarity_score: number;
  error_message?: string;
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
  llm_used: boolean;
}

// Complete request/response interfaces
export interface CompleteRequest {
  prompt: string;
  use_llm?: boolean;
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
  similarity_threshold?: number;
  limit?: number;
}

export interface CompleteResponse {
  cache_template: string;
  cache_hit: boolean;
  similarity_score: number;
  template_id?: number;
  cached_query?: string;
  user_query: string;
  updated_template?: string;
  llm_explanation?: string;
  warning?: string;
  considered_entries?: number[];  // Array of all considered cache entry IDs
  cache_entry_id?: number;  // ID of the matched cache entry
  is_confident?: boolean;  // Whether the LLM is confident in the response
}

// Create cache entry interface
export interface CacheEntryCreate {
  nl_query: string;
  template: string;
  template_type: string;
  reasoning_trace?: string;
  is_template: boolean;
  entity_replacements?: Record<string, any>;
  tags?: Record<string, string[]>;
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
  status?: string;
}

export interface CsvUploadResponse {
  status: string;
  processed: number;
  failed: number;
  results: Array<{
    id?: number;
    nl_query: string;
    status: 'success' | 'error';
    error?: string;
  }>;
}

// CatalogValues interface
export interface CatalogValues {
  catalog_types: string[];
  catalog_subtypes: string[];
  catalog_names: string[];
}

// Workflow generation request/response
export interface GenerateWorkflowRequest {
  nl_query: string;
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
}

export interface GenerateWorkflowResponse {
  nodes: any[];
  edges: any[];
  workflow_template: any;
  explanation: string;
}

// API service for cache management
const api = {
  // Get all cache entries with optional filtering
  async getCacheEntries(
    page: number = 1, 
    pageSize: number = 10,
    templateType?: string,
    searchQuery?: string,
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string,
    ids?: number[]
  ): Promise<{ items: CacheItem[], total: number }> {
    try {
      let url = `${API_BASE}/v1/cache?page=${page}&page_size=${pageSize}`;
      
      if (templateType) {
        url += `&template_type=${encodeURIComponent(templateType)}`;
      }
      
      if (searchQuery) {
        url += `&search_query=${encodeURIComponent(searchQuery)}`;
      }
      
      if (catalogType) {
        url += `&catalog_type=${encodeURIComponent(catalogType)}`;
      }
      
      if (catalogSubtype) {
        url += `&catalog_subtype=${encodeURIComponent(catalogSubtype)}`;
      }
      
      if (catalogName) {
        url += `&catalog_name=${encodeURIComponent(catalogName)}`;
      }
      
      // Add IDs filter if provided
      if (ids && ids.length > 0) {
        url += `&ids=${ids.join(',')}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching cache entries:', error);
      throw error;
    }
  },
  
  // Get a single cache entry by ID
  async getCacheEntry(id: number): Promise<CacheItem> {
    try {
      const url = `${API_BASE}/v1/cache/${id}`;
      console.log(`Fetching cache entry with ID ${id}`);
      
      // Using standard fetch instead of fetchWithDebug to avoid module resolution issues
      let data;
      try {
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        data = await response.json();
      } catch (error) {
        console.error(`Error fetching cache entry with ID ${id}:`, error);
        throw error;
      }
      
      // Add logging to see if catalog fields are missing
      if (data.catalog_type === undefined && data.catalog_subtype === undefined && data.catalog_name === undefined) {
        console.warn('Backend API does not include catalog fields in response');
      }
      
      console.log(`Successfully fetched cache entry ${id}:`, data);
      return data;
    } catch (error) {
      console.error(`Error fetching cache entry with ID ${id}:`, error);
      throw error;
    }
  },
  
  // Create a new cache entry
  async createCacheEntry(entry: CacheEntryCreate): Promise<CacheItem> {
    try {
      const response = await fetch(`${API_BASE}/v1/cache`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error creating cache entry:', error);
      throw error;
    }
  },
  
  // Update an existing cache entry
  async updateCacheEntry(id: number, entry: Partial<CacheEntryCreate>): Promise<CacheItem> {
    try {
      const response = await fetch(`${API_BASE}/v1/cache/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error updating cache entry with ID ${id}:`, error);
      throw error;
    }
  },
  
  // Delete a cache entry
  async deleteCacheEntry(id: number): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/v1/cache/${id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error(`Error deleting cache entry with ID ${id}:`, error);
      throw error;
    }
  },
  
  // Get cache statistics
  async getCacheStats(
    templateType?: string,
    catalogType?: string, 
    catalogSubtype?: string, 
    catalogName?: string
  ): Promise<CacheStats> {
    try {
      let url = `${API_BASE}/v1/cache/stats`;
      const params = new URLSearchParams();
      
      if (templateType && templateType !== 'all') {
        params.append('template_type', templateType);
      }
      
      if (catalogType) {
        params.append('catalog_type', catalogType);
      }
      
      if (catalogSubtype) {
        params.append('catalog_subtype', catalogSubtype);
      }
      
      if (catalogName) {
        params.append('catalog_name', catalogName);
      }
      
      // Add query parameters if any exist
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        // If we get a 422 error, provide fallback data
        if (response.status === 422) {
          console.warn('Server returned 422 for stats endpoint, using fallback data');
          return {
            total_entries: 0,
            by_template_type: {
              sql: 0,
              api: 0,
              url: 0,
              workflow: 0
            },
            recent_usage: [],
            popular_entries: []
          };
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching cache stats:', error);
      // Return fallback data on any error
      return {
        total_entries: 0,
        by_template_type: {
          sql: 0,
          api: 0,
          url: 0,
          workflow: 0
        },
        recent_usage: [],
        popular_entries: []
      };
    }
  },
  
  // Get catalog values for filtering
  async getCatalogValues(): Promise<CatalogValues> {
    try {
      const response = await fetch(`${API_BASE}/v1/catalog/values`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching catalog values:', error);
      // Return empty lists on error
      return {
        catalog_types: [],
        catalog_subtypes: [],
        catalog_names: []
      };
    }
  },
  
  // Test a cache entry
  async testCacheEntry(id: number): Promise<any> {
    try {
      const response = await fetch(`${API_BASE}/v1/cache/${id}/test`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error testing cache entry with ID ${id}:`, error);
      throw error;
    }
  },
  
  // Apply entity substitution to a template
  async applyEntitySubstitution(id: number, entityValues: Record<string, any>): Promise<any> {
    try {
      const response = await fetch(`${API_BASE}/v1/cache/${id}/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ entity_values: entityValues }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error applying entity substitution to cache entry with ID ${id}:`, error);
      throw error;
    }
  },

  // Search cache entries with similarity search
  async searchCacheEntries(
    nl_query: string,
    template_type?: string,
    threshold: number = 0.7,
    limit: number = 5,
    catalog_type?: string,
    catalog_subtype?: string,
    catalog_name?: string
  ): Promise<CacheItem[]> {
    try {
      let url = `${API_BASE}/v1/cache/search?nl_query=${encodeURIComponent(nl_query)}`;
      
      if (template_type) {
        url += `&template_type=${encodeURIComponent(template_type)}`;
      }
      
      if (catalog_type) {
        url += `&catalog_type=${encodeURIComponent(catalog_type)}`;
      }
      
      if (catalog_subtype) {
        url += `&catalog_subtype=${encodeURIComponent(catalog_subtype)}`;
      }
      
      if (catalog_name) {
        url += `&catalog_name=${encodeURIComponent(catalog_name)}`;
      }
      
      url += `&threshold=${threshold}&limit=${limit}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error searching cache entries:', error);
      throw error;
    }
  },

  // Get usage logs
  async getUsageLogs(page: number = 1, pageSize: number = 10): Promise<{ items: UsageLog[], total: number }> {
    try {
      const response = await fetch(`${API_BASE}/v1/usage_logs?page=${page}&page_size=${pageSize}&order_by=timestamp&order_desc=true`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Raw usage logs API response:", data);
      
      // Handle different API response formats
      if (data && Array.isArray(data.items)) {
        return data;
      } else if (data && Array.isArray(data.logs)) {
        return { items: data.logs, total: data.total_count || data.logs.length };
      } else if (data && Array.isArray(data)) {
        // If response is just an array
        return { items: data, total: data.length };
      } else {
        console.warn("Unexpected usage logs API response format:", data);
        return { items: [], total: 0 };
      }
    } catch (error) {
      console.error('Error fetching usage logs:', error);
      return { items: [], total: 0 }; // Return empty result instead of throwing
    }
  },
  
  // Process a completion request
  async complete(request: CompleteRequest): Promise<CompleteResponse> {
    try {
      // Build URL with query parameters
      let url = `${API_BASE}/v1/complete`;
      const params = new URLSearchParams();
      
      if (request.use_llm) {
        params.append('use_llm', 'true');
      }
      
      if (request.catalog_type) {
        params.append('catalog_type', request.catalog_type);
      }
      
      if (request.catalog_subtype) {
        params.append('catalog_subtype', request.catalog_subtype);
      }
      
      if (request.catalog_name) {
        params.append('catalog_name', request.catalog_name);
      }
      
      if (request.similarity_threshold) {
        params.append('similarity_threshold', request.similarity_threshold.toString());
      }
      
      if (request.limit) {
        params.append('limit', request.limit.toString());
      }
      
      // Add query parameters if any
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      // Add timeout handling
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: request.prompt }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error: any) {
      console.error('Error with completion request:', error);
      
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. The server took too long to respond.');
      }
      
      throw error;
    }
  },

  // Upload CSV file to create cache entries
  async uploadCsv(
    file: File, 
    templateType: string = 'sql',
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string
  ): Promise<CsvUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Build URL with query parameters
      let url = `${API_BASE}/v1/upload/csv?template_type=${encodeURIComponent(templateType)}`;
      
      // Add catalog parameters if provided
      if (catalogType) {
        url += `&catalog_type=${encodeURIComponent(catalogType)}`;
      }
      if (catalogSubtype) {
        url += `&catalog_subtype=${encodeURIComponent(catalogSubtype)}`;
      }
      if (catalogName) {
        url += `&catalog_name=${encodeURIComponent(catalogName)}`;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error uploading CSV file:', error);
      throw error;
    }
  },

  // Upload Swagger URL to generate API templates
  async uploadSwagger(
    swaggerUrl: string, 
    templateType: string = 'api',
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string
  ): Promise<CsvUploadResponse> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30-second timeout
      
      // Create request body with all parameters
      const requestBody: any = { 
        swagger_url: swaggerUrl 
      };
      
      // Add catalog parameters if provided
      if (catalogType) {
        requestBody.catalog_type = catalogType;
      }
      if (catalogSubtype) {
        requestBody.catalog_subtype = catalogSubtype;
      }
      if (catalogName) {
        requestBody.catalog_name = catalogName;
      }
      
      const response = await fetch(`${API_BASE}/v1/upload/swagger`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error: any) {
      console.error('Error uploading Swagger URL:', error);
      
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. The server took too long to respond.');
      }
      
      throw error;
    }
  },
  
  // Generate reasoning trace using LLM
  async generateReasoningTrace(nl_query: string, template: string, template_type: string): Promise<string> {
    try {
      const response = await fetch(`${API_BASE}/v1/generate/reasoning_trace`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nl_query,
          template,
          template_type
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return data.reasoning_trace;
    } catch (error) {
      console.error('Error generating reasoning trace:', error);
      throw error;
    }
  },

  // Get compatible cache entries for workflow steps
  async getCompatibleCacheEntries(
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string,
    excludeIds: number[] = []
  ): Promise<CacheItem[]> {
    try {
      let url = `${API_BASE}/v1/cache/compatible`;
      
      const params = new URLSearchParams();
      
      if (catalogType) {
        params.append('catalog_type', catalogType);
      }
      
      if (catalogSubtype) {
        params.append('catalog_subtype', catalogSubtype);
      }
      
      if (catalogName) {
        params.append('catalog_name', catalogName);
      }
      
      if (excludeIds.length > 0) {
        params.append('exclude_ids', excludeIds.join(','));
      }
      
      // Only add the '?' if we have parameters
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching compatible cache entries:', error);
      return []; // Return empty array on error
    }
  },

  // Get bulk cache entries by ID
  async getBulkCacheEntries(ids: number[]): Promise<CacheItem[]> {
    if (!ids || ids.length === 0) return [];
    
    try {
      console.log(`Fetching multiple cache entries: ${ids.join(', ')}`);
      
      // Use the existing getCacheEntries method with a high page size to include all IDs
      const result = await this.getCacheEntries(1, Math.max(ids.length, 50), undefined, undefined, undefined, undefined, undefined, ids);
      
      console.log(`Fetched ${result.items.length} of ${ids.length} requested entries`);
      return result.items;
    } catch (error) {
      console.error('Error fetching bulk cache entries:', error);
      return [];
    }
  },

  // Generate a workflow from natural language
  async generateWorkflowFromNL(request: GenerateWorkflowRequest): Promise<GenerateWorkflowResponse> {
    try {
      const response = await fetch(`${API_BASE}/v1/workflows/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error generating workflow from NL:', error);
      throw error;
    }
  },
};

export default api; 