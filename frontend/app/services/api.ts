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
  suggested_visualization?: string;
  database_name?: string;
  schema_name?: string;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

// Stats interface
export interface CacheStats {
  total_entries: number;
  entries_by_type: Record<string, number>;
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
  suggested_visualization?: string;
  database_name?: string;
  schema_name?: string;
  catalog_id?: number;
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
            entries_by_type: {
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
        entries_by_type: {
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
    catalog_id?: number
  ): Promise<CacheItem[]> {
    try {
      let url = `${API_BASE}/v1/cache/search?nl_query=${encodeURIComponent(nl_query)}`;
      
      if (template_type) {
        url += `&template_type=${encodeURIComponent(template_type)}`;
      }
      
      if (catalog_id) {
        url += `&catalog_id=${catalog_id}`;
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
};

export default api; 