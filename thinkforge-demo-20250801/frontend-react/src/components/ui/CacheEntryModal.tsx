import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./dialog";
import { Button } from "./button";
import { X, ExternalLink } from "lucide-react";
import api from "@/services/api";
import { Link } from "react-router-dom";
import { CacheBreadcrumbs } from "./CacheBreadcrumbs";

interface CacheEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  cacheEntryId: number | null;
  source?: {
    type: string;
    label: string;
    href: string;
  };
}

export function CacheEntryModal({ isOpen, onClose, cacheEntryId, source }: CacheEntryModalProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entry, setEntry] = useState<any>(null);

  useEffect(() => {
    if (isOpen && cacheEntryId) {
      setLoading(true);
      setError(null);
      const fetchEntry = async () => {
        try {
          const entry = await api.getCacheEntry(cacheEntryId);
          setEntry(entry);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to fetch cache entry");
        } finally {
          setLoading(false);
        }
      };
      fetchEntry();
    }
  }, [isOpen, cacheEntryId]);

  if (!isOpen || !cacheEntryId) return null;

  const breadcrumbItems = [
    { label: "Dashboard", href: "/dashboard" },
  ];
  if (source) {
    breadcrumbItems.push({ label: source.label, href: source.href });
  }
  breadcrumbItems.push({ label: `Cache Entry #${cacheEntryId}` });

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-y-auto bg-neutral-900 border-neutral-700 text-neutral-200">
        <DialogHeader>
          <CacheBreadcrumbs 
            items={breadcrumbItems}
            className="mb-3"
          />
          <DialogTitle className="text-xl font-bold flex items-center justify-between">
            <span>Cache Entry Details</span>
            <div className="flex gap-2">
              <a 
                href={`/cache-entries/${cacheEntryId}`} 
                target="_blank"
                className="inline-flex items-center text-sm font-medium text-blue-500 hover:text-blue-400"
                rel="noopener noreferrer"
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                Open in new tab
              </a>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={onClose}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex items-center justify-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-2">Loading entry...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-900/30 border border-red-700 rounded-md">
            {error}
          </div>
        ) : entry ? (
          <div className="space-y-6 p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-sm text-neutral-400">Catalog Type</label>
                <div className="text-neutral-200">{entry.catalog_type || "N/A"}</div>
              </div>
              <div className="space-y-1">
                <label className="text-sm text-neutral-400">Catalog Subtype</label>
                <div className="text-neutral-200">{entry.catalog_subtype || "N/A"}</div>
              </div>
              <div className="space-y-1">
                <label className="text-sm text-neutral-400">Catalog Name</label>
                <div className="text-neutral-200">{entry.catalog_name || "N/A"}</div>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm text-neutral-400">Natural Language Query</label>
              <div className="p-3 bg-neutral-800 border border-neutral-700 rounded-md">
                {entry.nl_query}
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm text-neutral-400">Template Type</label>
                <div className="text-neutral-200 capitalize">{entry.template_type}</div>
              </div>
              <div className="space-y-1">
                <label className="text-sm text-neutral-400">Status</label>
                <div className="text-neutral-200 capitalize">{entry.status}</div>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm text-neutral-400">Template</label>
              <pre className="p-3 bg-neutral-800 border border-neutral-700 rounded-md overflow-auto max-h-[200px] font-mono text-sm">
                {entry.template}
              </pre>
            </div>
            {entry.reasoning_trace && (
              <div className="space-y-1">
                <label className="text-sm text-neutral-400">Reasoning Trace</label>
                <pre className="p-3 bg-neutral-800 border border-neutral-700 rounded-md overflow-auto max-h-[200px] font-mono text-sm">
                  {entry.reasoning_trace}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 text-center">No data found</div>
        )}
      </DialogContent>
    </Dialog>
  );
} 