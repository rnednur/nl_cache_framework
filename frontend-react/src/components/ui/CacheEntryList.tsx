import { useEffect, useState } from "react";
import api from "@/services/api";

interface CacheEntryListProps {
  entryIds: number[];
}

const globalEntryCache: Record<number, any> = {};

export function CacheEntryList({ entryIds }: CacheEntryListProps) {
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const entryIdsKey = entryIds.join(",");

  useEffect(() => {
    const fetchEntries = async () => {
      if (!entryIds.length) {
        setLoading(false);
        return;
      }
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
      if (allCached) {
        setEntries(cachedEntries);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
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
              return null;
            }
          })
        );
        const loadedEntries = results.map((result, index) => {
          if (result.status === "fulfilled") {
            return result.value;
          }
          return null;
        });
        setEntries(loadedEntries);
      } catch (err) {
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
          <span key={id} title={entry ? entry.nl_query : undefined}>
            <a 
              href={`/cache-entries/${id}`} 
              className={
                isLoading
                  ? "text-gray-500"
                  : entry
                  ? "text-blue-500 hover:text-blue-400"
                  : "text-red-500 hover:text-red-400"
              }
              target="_blank"
              rel="noopener noreferrer"
            >
              {id}
            </a>
            {index < entryIds.length - 1 ? ", " : ""}
          </span>
        );
      })}
    </div>
  );
} 