"use client"

import { useState, useEffect } from "react";
import api from "@/app/services/api";

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

  // Pre-fetch entry data when component mounts
  useEffect(() => {
    if (!entryCache[entryId] && !loading && !entryData) {
      const fetchData = async () => {
        try {
          setLoading(true);
          const data = await api.getCacheEntry(entryId);
          entryCache[entryId] = data;
          setEntryData(data);
        } catch (err) {
          console.error(`Error fetching cache entry ${entryId}:`, err);
          setError(`Failed to load entry ${entryId}`);
        } finally {
          setLoading(false);
        }
      };
      
      fetchData();
    }
  }, [entryId, loading, entryData]);

  const handleMouseMove = (e: React.MouseEvent) => {
    // Calculate position to ensure tooltip stays within viewport
    const viewportWidth = window.innerWidth;
    const tooltipWidth = 400; // max width of tooltip
    
    let xPos = e.clientX + 10;
    // If tooltip would go off right edge, position it to the left of cursor
    if (xPos + tooltipWidth > viewportWidth) {
      xPos = e.clientX - tooltipWidth - 10;
    }
    
    setPosition({ 
      x: xPos, 
      y: e.clientY + 10 
    });
  };

  const tooltipContent = () => {
    if (loading) {
      return <div className="text-neutral-400 text-sm py-2">Loading entry {entryId}...</div>;
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
        
        <div>
          <div className="text-neutral-400 text-xs mb-1">Template Type:</div>
          <div className="text-white text-sm capitalize">{entryData.template_type}</div>
        </div>
        
        <div>
          <div className="text-neutral-400 text-xs mb-1">Template:</div>
          <pre className="text-white text-xs bg-neutral-800 p-2 rounded-md overflow-auto max-h-[100px]">{entryData.template}</pre>
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
          className="fixed z-50 bg-neutral-900 border border-neutral-700 rounded-md shadow-lg p-4"
          style={{ 
            left: `${position.x}px`, 
            top: `${position.y}px`,
            maxWidth: "400px",
            maxHeight: "300px",
            overflow: "auto"
          }}
        >
          {tooltipContent()}
        </div>
      )}
    </div>
  );
} 