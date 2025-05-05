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
  tags?: string[];
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

// Create cache entry interface
export interface CacheEntryCreate {
  nl_query: string;
  template: string;
  template_type: string;
  reasoning_trace?: string;
  is_template: boolean;
  entity_replacements?: Record<string, any>;
  tags?: string[];
  catalog_type?: string;
  catalog_subtype?: string;
  catalog_name?: string;
  status?: string;
}

// API service for cache management
const api = {
  // Get all cache entries with optional filtering
  async getCacheEntries(
    page: number = 1, 
    pageSize: number = 10,
    templateType?: string,
    searchQuery?: string
  ): Promise<{ items: CacheItem[], total: number }> {
    try {
      let url = `${API_BASE}/v1/cache?page=${page}&page_size=${pageSize}`;
      
      if (templateType) {
        url += `&template_type=${encodeURIComponent(templateType)}`;
      }
      
      if (searchQuery) {
        url += `&search_query=${encodeURIComponent(searchQuery)}`;
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
      const response = await fetch(`${API_BASE}/v1/cache/${id}`);
      
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
  async getCacheStats(templateType?: string): Promise<CacheStats> {
    try {
      let url = `${API_BASE}/v1/cache/stats`;
      
      if (templateType && templateType !== 'all') {
        url += `?template_type=${encodeURIComponent(templateType)}`;
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
  async getUsageLogs(page: number = 1, pageSize: number = 10): Promise<{ items: any[], total: number }> {
    try {
      const response = await fetch(`${API_BASE}/v1/usage_logs?page=${page}&page_size=${pageSize}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching usage logs:', error);
      throw error;
    }
  },
};

export default api; 