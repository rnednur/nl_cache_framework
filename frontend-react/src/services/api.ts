// API base URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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
  is_confident?: boolean;
  considered_entries?: number[];
  response?: string;
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
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
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
        throw new Error(`HTTP error! status: ${response.status}`);
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
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error updating cache entry:', error);
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
      console.error('Error deleting cache entry:', error);
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
      
      if (templateType) {
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
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching cache stats:', error);
      throw error;
    }
  },

  // Get catalog values
  async getCatalogValues(): Promise<CatalogValues> {
    try {
      const response = await fetch(`${API_BASE}/v1/catalog/values`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching catalog values:', error);
      throw error;
    }
  },

  // Test cache entry
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
      console.error('Error testing cache entry:', error);
      throw error;
    }
  },

  // Apply entity substitution
  async applyEntitySubstitution(id: number, entityValues: Record<string, any>): Promise<any> {
    try {
      const response = await fetch(`${API_BASE}/v1/cache/${id}/substitute`, {
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
      console.error('Error applying entity substitution:', error);
      throw error;
    }
  },

  // Search cache entries
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
      const params = new URLSearchParams({
        nl_query,
        threshold: threshold.toString(),
        limit: limit.toString(),
      });
      
      if (template_type) {
        params.append('template_type', template_type);
      }
      
      if (catalog_type) {
        params.append('catalog_type', catalog_type);
      }
      
      if (catalog_subtype) {
        params.append('catalog_subtype', catalog_subtype);
      }
      
      if (catalog_name) {
        params.append('catalog_name', catalog_name);
      }
      
      const response = await fetch(`${API_BASE}/v1/cache/search?${params}`);
      
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
  async getUsageLogs(page: number = 1, pageSize: number = 20): Promise<{ items: UsageLog[], total: number }> {
    


    try {
      const response = await fetch(`${API_BASE}/v1/usage_logs?page=${page}&page_size=${pageSize}&order_by=timestamp&order_desc=true`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Raw usage logs API response:", data.total_count);
      
      // Handle different API response formats
      if (data && Array.isArray(data.items)) {
        return { items: data.items, total: data.total_count || data.items.length };
      
      } else if (data && Array.isArray(data.logs)) {
        console.log("Usage logs-isArray:", data.total_count || data.logs.length );
    
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

  // Complete request
  async complete(request: CompleteRequest): Promise<CompleteResponse> {
    try {
      const response = await fetch(`${API_BASE}/v1/complete`, {
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
      console.error('Error completing request:', error);
      throw error;
    }
  },

  // Upload CSV
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
      formData.append('template_type', templateType);
      
      if (catalogType) {
        formData.append('catalog_type', catalogType);
      }
      
      if (catalogSubtype) {
        formData.append('catalog_subtype', catalogSubtype);
      }
      
      if (catalogName) {
        formData.append('catalog_name', catalogName);
      }
      
      const response = await fetch(`${API_BASE}/v1/upload/csv`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error uploading CSV:', error);
      throw error;
    }
  },

  // Upload Swagger
  async uploadSwagger(
    swaggerUrl: string, 
    templateType: string = 'api',
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string
  ): Promise<CsvUploadResponse> {
    try {
      const response = await fetch(`${API_BASE}/v1/upload/swagger`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          swagger_url: swaggerUrl,
          template_type: templateType,
          catalog_type: catalogType,
          catalog_subtype: catalogSubtype,
          catalog_name: catalogName,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error uploading Swagger:', error);
      throw error;
    }
  },

  // Generate reasoning trace
  async generateReasoningTrace(nl_query: string, template: string, template_type: string): Promise<string> {
    try {
      const response = await fetch(`${API_BASE}/v1/generate/reasoning_trace`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nl_query, template, template_type }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return data.reasoning_trace;
    } catch (error) {
      console.error('Error generating reasoning trace:', error);
      throw error;
    }
  },

  // Get compatible cache entries
  async getCompatibleCacheEntries(
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string,
    excludeIds: number[] = []
  ): Promise<CacheItem[]> {
    try {
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
      
      const response = await fetch(`${API_BASE}/v1/cache/compatible?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching compatible cache entries:', error);
      throw error;
    }
  },

  // Get bulk cache entries
  async getBulkCacheEntries(ids: number[]): Promise<CacheItem[]> {
    try {
      const response = await fetch(`${API_BASE}/v1/cache/bulk?ids=${ids.join(',')}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching bulk cache entries:', error);
      throw error;
    }
  },

  // Generate workflow from natural language
  async generateWorkflowFromNL(request: GenerateWorkflowRequest): Promise<GenerateWorkflowResponse> {
    try {
      const response = await fetch(`${API_BASE}/v1/workflow/generate`, {
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
      console.error('Error generating workflow:', error);
      throw error;
    }
  },
};

export default api; 