import axios from 'axios'
import { API_BASE_URL } from '@/config/env'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface CacheItem {
  id: number
  nl_query: string
  template_type: string
  template: string
  catalog_type?: string
  catalog_subtype?: string
  catalog_name?: string
  tags: string[] | null
  status: string
  usage_count: number
  last_used?: string
  created_at: string
  updated_at: string
  similarity_threshold: number
}

export interface CacheResponse {
  items: CacheItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface CatalogValues {
  catalog_types: string[]
  catalog_subtypes: string[]
  catalog_names: string[]
}

export interface CacheStats {
  total_entries: number
  total_usage: number
  avg_usage_per_entry: number
  most_used_template_type: string
  entries_by_template_type: Record<string, number>
  entries_by_status: Record<string, number>
  recent_entries: CacheItem[]
}

export interface CompletionMatch {
  score: number
  entry: CacheItem
}

export interface CompletionResult {
  query: string
  matches: CompletionMatch[]
  query_time: number
  method: string
  threshold: number
}

export interface CreateCacheEntryData {
  nl_query: string
  template_type: string
  template: string
  catalog_type?: string | null
  catalog_subtype?: string | null
  catalog_name?: string | null
  tags?: string[]
  status?: string
  similarity_threshold?: number
}

class ApiService {
  async getCacheEntries(
    page: number = 1, 
    pageSize: number = 10, 
    templateType?: string,
    search?: string,
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string
  ): Promise<CacheResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    })
    
    if (templateType) params.append('template_type', templateType)
    if (search) params.append('search', search)
    if (catalogType) params.append('catalog_type', catalogType)
    if (catalogSubtype) params.append('catalog_subtype', catalogSubtype)
    if (catalogName) params.append('catalog_name', catalogName)

    const response = await api.get(`/v1/cache?${params.toString()}`)
    return response.data
  }

  async getCacheEntry(id: number): Promise<CacheItem> {
    const response = await api.get(`/v1/cache/${id}`)
    return response.data
  }

  async createCacheEntry(data: CreateCacheEntryData): Promise<CacheItem> {
    const response = await api.post('/v1/cache', data)
    return response.data
  }

  async updateCacheEntry(id: number, data: Partial<CreateCacheEntryData>): Promise<CacheItem> {
    const response = await api.put(`/v1/cache/${id}`, data)
    return response.data
  }

  async deleteCacheEntry(id: number): Promise<void> {
    await api.delete(`/v1/cache/${id}`)
  }

  async getCatalogValues(): Promise<CatalogValues> {
    const response = await api.get('/v1/catalog/values')
    return response.data
  }

  async getCacheStats(): Promise<CacheStats> {
    const response = await api.get('/v1/cache/stats')
    return response.data
  }

  async completeQuery(
    query: string,
    catalogType?: string,
    catalogSubtype?: string,
    catalogName?: string,
    similarityThreshold: number = 0.85,
    limit: number = 5
  ): Promise<CompletionResult> {
    const params = new URLSearchParams({
      similarity_threshold: similarityThreshold.toString(),
      limit: limit.toString(),
    })
    
    if (catalogType) params.append('catalog_type', catalogType)
    if (catalogSubtype) params.append('catalog_subtype', catalogSubtype)
    if (catalogName) params.append('catalog_name', catalogName)

    const response = await api.post(`/v1/complete?${params.toString()}`, {
      query
    })
    return response.data
  }
}

export default new ApiService() 