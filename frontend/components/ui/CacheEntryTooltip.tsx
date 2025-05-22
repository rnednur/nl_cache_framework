"use client"

import { useState, useEffect } from "react";
import api from "../../app/services/api";

interface CacheEntryTooltipProps {
  entryId: number;
  children: React.ReactNode;
}

// A cache to store fetched entries so we don't need to fetch them again
const entryCache: Record<number, any> = {};

export function CacheEntryTooltip({ entryId, children }: CacheEntryTooltipProps) {
  const [isHovering, setIsHovering] = useState(false);
  const [entryData, setEntryData] = useState<any>(entryCache[entryId] || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  // Pre-fetch entry data when component mounts or when hovering starts
  useEffect(() => {
    const fetchData = async () => {
      if (!entryCache[entryId] && !loading) {
        try {
          setLoading(true);
          console.log(`Fetching cache entry ${entryId}`);
          const data = await api.getCacheEntry(entryId);
          entryCache[entryId] = data;
          setEntryData(data);
          console.log(`Successfully fetched cache entry ${entryId}`, data);
        } catch (err) {
          console.error(`Error fetching cache entry ${entryId}:`, err);
          setError(`Failed to load entry ${entryId}`);
        } finally {
          setLoading(false);
        }
      }
    };
    
    // Fetch immediately when component mounts to have data ready
    fetchData();
    
    // Also fetch if data is not already available when hovering starts
    if (isHovering && !entryData && !entryCache[entryId]) {
      fetchData();
    }
  }, [entryId, loading, entryData, isHovering]);

  const handleMouseMove = (e: React.MouseEvent) => {
    // Calculate position to ensure tooltip stays within viewport
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const tooltipWidth = 400; // max width of tooltip
    const tooltipHeight = 350; // max height of tooltip
    
    let xPos = e.clientX + 10;
    let yPos = e.clientY + 10;
    
    // If tooltip would go off right edge, position it to the left of cursor
    if (xPos + tooltipWidth > viewportWidth - 20) {
      xPos = Math.max(20, e.clientX - tooltipWidth - 10);
    }
    
    // If tooltip would go off bottom edge, position it above cursor
    if (yPos + tooltipHeight > viewportHeight - 20) {
      yPos = Math.max(20, e.clientY - tooltipHeight - 10);
    }
    
    setPosition({ x: xPos, y: yPos });
  };

  const tooltipContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
          <span className="ml-2 text-neutral-400 text-sm">Loading cache entry {entryId}...</span>
        </div>
      );
    }
    
    if (error) {
      return <div className="text-red-400 text-sm py-2">{error}</div>;
    }
    
    if (!entryData) {
      return <div className="text-neutral-400 text-sm py-2">No data available for entry {entryId}</div>;
    }
    
    return (
      <div className="space-y-3">
        <div>
          <div className="text-neutral-400 text-xs mb-1">Query:</div>
          <div className="text-white text-sm">{entryData.nl_query}</div>
        </div>
        
        <div className="flex gap-4">
          <div className="flex-1">
            <div className="text-neutral-400 text-xs mb-1">Catalog Type:</div>
            <div className="text-white text-sm capitalize">{entryData.catalog_type || "N/A"}</div>
          </div>
          <div className="flex-1">
            <div className="text-neutral-400 text-xs mb-1">Created:</div>
            <div className="text-white text-sm">
              {entryData.created_at ? new Date(entryData.created_at).toLocaleString() : "N/A"}
            </div>
          </div>
        </div>
        
        <div className="flex gap-4">
          <div className="flex-1">
            <div className="text-neutral-400 text-xs mb-1">Subtype:</div>
            <div className="text-white text-sm capitalize">{entryData.catalog_subtype || "N/A"}</div>
          </div>
          <div className="flex-1">
            <div className="text-neutral-400 text-xs mb-1">Success Rate:</div>
            <div className="text-white text-sm">
              {entryData.success_count !== undefined && entryData.usage_count !== undefined
                ? `${Math.round((entryData.success_count / entryData.usage_count) * 100)}%`
                : "N/A"}
            </div>
          </div>
        </div>
        
        <div>
          <div className="text-neutral-400 text-xs mb-1">Template Type:</div>
          <div className="text-white text-sm capitalize">{entryData.template_type || "N/A"}</div>
        </div>
        
        <div>
          <div className="text-neutral-400 text-xs mb-1">Template:</div>
          <pre className="text-white text-xs bg-neutral-800 p-2 rounded-md overflow-auto max-h-[100px] whitespace-pre-wrap">{entryData.template}</pre>
        </div>
        
        <div className="pt-2 text-center text-xs text-blue-400">
          Click to view full details
        </div>
      </div>
    );
  };

  return (
    <div
      className="inline-block"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      onMouseMove={handleMouseMove}
    >
      {children}
      
      {isHovering && (
        <div 
          className="fixed z-[9999] bg-neutral-900 border border-blue-600 rounded-md shadow-lg p-4"
          style={{ 
            left: `${position.x}px`, 
            top: `${position.y}px`,
            maxWidth: "400px",
            maxHeight: "350px",
            overflow: "auto",
            boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)"
          }}
        >
          {tooltipContent()}
        </div>
      )}
    </div>
  );
} 