"use client"

import { useEffect, useState } from "react";
import api from "@/app/services/api";
import { SimpleCacheTooltip } from "./SimpleCacheTooltip";

interface CacheEntryListProps {
  entryIds: number[];
}

// Create a global cache for entries to improve performance across components
const globalEntryCache: Record<number, any> = {};

export function CacheEntryList({ entryIds }: CacheEntryListProps) {
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Use entryIds as a key for useEffect
  const entryIdsKey = entryIds.join(',');
  
  useEffect(() => {
    const fetchEntries = async () => {
      if (!entryIds.length) {
        setLoading(false);
        return;
      }
      
      // Check if we already have all entries in the cache
      let allCached = true;
      const cachedEntries: any[] = [];
      
      for (const id of entryIds) {
        if (globalEntryCache[id]) {
          cachedEntries.push(globalEntryCache[id]);
        } else {
          allCached = false;
          cachedEntries.push(null);
        }
      }
      
      // If all entries are cached, use them
      if (allCached) {
        console.log('Using cached entries for:', entryIds);
        setEntries(cachedEntries);
        setLoading(false);
        return;
      }
      
      setLoading(true);
      
      try {
        console.log('Fetching entries for:', entryIds);
        
        // For each entry ID, try to get it individually
        // This is not ideal, but it ensures we get as many entries as possible
        const results = await Promise.allSettled(
          entryIds.map(async (id) => {
            if (globalEntryCache[id]) {
              return globalEntryCache[id];
            }
            
            try {
              const entry = await api.getCacheEntry(id);
              globalEntryCache[id] = entry;
              return entry;
            } catch (err) {
              console.warn(`Failed to fetch entry ${id}:`, err);
              return null;
            }
          })
        );
        
        // Process results
        const loadedEntries = results.map((result, index) => {
          if (result.status === 'fulfilled') {
            return result.value;
          }
          console.warn(`Failed to load entry ${entryIds[index]}`);
          return null;
        });
        
        setEntries(loadedEntries);
      } catch (err) {
        console.error("Failed to fetch entries:", err);
        setError("Failed to load entry details");
      } finally {
        setLoading(false);
      }
    };
    
    fetchEntries();
  }, [entryIdsKey]);
  
  if (loading) {
    return <div className="text-neutral-400 text-sm py-2">Loading entries...</div>;
  }
  
  if (error) {
    return <div className="text-red-400 text-sm py-2">{error}</div>;
  }
  
  return (
    <div className="flex flex-wrap gap-1">
      {entryIds.map((id, index) => {
        const entry = entries[index];
        const isLoading = loading && !entry;
        
        // Create tooltip content based on entry data status
        const tooltipContent = isLoading ? (
          <div className="text-sm p-1">
            <p className="text-neutral-300 mb-1">Loading entry {id}...</p>
          </div>
        ) : entry ? (
          <div className="space-y-2 max-w-[300px] p-1">
            <div>
              <div className="text-neutral-400 text-xs mb-1">Query:</div>
              <div className="text-white text-sm">{entry.nl_query}</div>
            </div>
            
            <div>
              <div className="text-neutral-400 text-xs mb-1">Template Type:</div>
              <div className="text-white text-sm capitalize">{entry.template_type}</div>
            </div>
            
            <div>
              <div className="text-neutral-400 text-xs mb-1">Template:</div>
              <pre className="text-white text-xs bg-neutral-800 p-2 rounded-md overflow-auto max-h-[100px]">{entry.template}</pre>
            </div>
          </div>
        ) : (
          <div className="text-sm p-1">
            <p className="text-neutral-300 mb-1">Cache Entry ID: {id}</p>
            <p className="text-neutral-400 text-xs">Could not load details</p>
          </div>
        );
        
        return (
          <span key={id}>
            <SimpleCacheTooltip content={tooltipContent}>
              <a 
                href={`/cache-entries/${id}`} 
                className={`${isLoading 
                  ? 'text-gray-500' 
                  : entry 
                    ? 'text-blue-500 hover:text-blue-400' 
                    : 'text-red-500 hover:text-red-400'}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {id}
              </a>
            </SimpleCacheTooltip>
            {index < entryIds.length - 1 ? ', ' : ''}
          </span>
        );
      })}
    </div>
  );
} 