import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./dialog";
import { Button } from "@/app/components/ui/button";
import { X, ExternalLink, MapPin, Box, Tag, Clock, Database, Users, Copy, ChevronDown, ChevronUp } from "lucide-react";
import api, { CacheItem } from "@/app/services/api";
import Link from "next/link";
import { CacheBreadcrumbs } from "./CacheBreadcrumbs";
import { Node } from 'reactflow';

interface NodeDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  node: Node | null;
}

// Icon mapping for different template types
const getTemplateIcon = (templateType: string) => {
  const iconMap: Record<string, string> = {
    sql: '🗄️',
    api: '🌐',
    workflow: '⚡',
    script: '📜',
    url: '🔗',
    cli: '💻',
    prompt: '🤖',
    configuration: '⚙️',
    graphql: '📊',
    nosql: '🍃',
  }
  return iconMap[templateType] || '📋'
}

const getTemplateColor = (templateType: string) => {
  const colorMap: Record<string, string> = {
    sql: '#3b82f6',
    api: '#10b981',
    workflow: '#8b5cf6',
    script: '#f59e0b',
    url: '#06b6d4',
    cli: '#6b7280',
    prompt: '#ec4899',
    configuration: '#84cc16',
    graphql: '#f97316',
    nosql: '#14b8a6',
  }
  return colorMap[templateType] || '#6b7280'
}

export function NodeDetailModal({ isOpen, onClose, node }: NodeDetailModalProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cacheEntry, setCacheEntry] = useState<CacheItem | null>(null);
  const [isTemplateExpanded, setIsTemplateExpanded] = useState(false);
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  useEffect(() => {
    if (isOpen && node?.data?.cacheEntryId) {
      setLoading(true);
      setError(null);
      const fetchEntry = async () => {
        try {
          const entry = await api.getCacheEntry(node.data.cacheEntryId);
          setCacheEntry(entry);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to fetch cache entry");
        } finally {
          setLoading(false);
        }
      };
      fetchEntry();
    } else if (isOpen && node && !node.data?.cacheEntryId) {
      // Handle nodes without cache entries (like start node)
      setLoading(false);
      setCacheEntry(null);
      setError(null);
    }
  }, [isOpen, node]);

  if (!isOpen || !node) return null;

  // Prepare breadcrumbs
  const breadcrumbItems = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Visual Workflow", href: "/dashboard" },
    { label: `Node: ${node.data?.label || node.id}`, href: "#" },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[95vw] max-w-6xl max-h-[90vh] overflow-y-auto bg-neutral-900 border-neutral-700 text-neutral-200 p-0">
        <DialogHeader className="px-4 pt-4 pb-4 sm:px-6 sm:pt-6">
          <CacheBreadcrumbs 
            items={breadcrumbItems}
            className="mb-3"
          />
          <DialogTitle className="text-xl font-bold flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">
                {node.data?.templateType ? getTemplateIcon(node.data.templateType) : '📦'}
              </span>
              <span>Node Details</span>
            </div>
            <div className="flex gap-2">
              {node.data?.cacheEntryId && (
                <Link 
                  href={`/cache-entries/${node.data.cacheEntryId}`} 
                  target="_blank"
                  className="inline-flex items-center text-sm font-medium text-blue-500 hover:text-blue-400"
                >
                  <ExternalLink className="h-4 w-4 mr-1" />
                  Open cache entry
                </Link>
              )}
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

        <div className="space-y-6 px-4 pb-6 sm:px-6">
          {/* Node Information */}
          <div className="p-4 bg-neutral-800 border border-neutral-700 rounded-lg">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Box className="h-5 w-5" />
              Node Information
            </h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-sm text-neutral-400 flex items-center gap-1">
                  <Tag className="h-3 w-3" />
                  Node ID
                </label>
                <div className="text-neutral-200 font-mono text-sm bg-neutral-700 px-2 py-1 rounded">
                  {node.id}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-sm text-neutral-400 flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  Position
                </label>
                <div className="text-neutral-200 font-mono text-sm">
                  x: {Math.round(node.position.x)}, y: {Math.round(node.position.y)}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-sm text-neutral-400">Node Type</label>
                <div className="text-neutral-200 capitalize">
                  {node.type || 'default'}
                </div>
              </div>
            </div>

            <div className="mt-4 space-y-1">
              <label className="text-sm text-neutral-400">Node Label</label>
              <div className="p-3 bg-neutral-700 border border-neutral-600 rounded-md break-words">
                {node.data?.label || 'No label'}
              </div>
            </div>
          </div>

          {/* Cache Entry Details */}
          {node.data?.cacheEntryId && (
            <>
              {loading ? (
                <div className="flex items-center justify-center p-8 bg-neutral-800 border border-neutral-700 rounded-lg">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  <span className="ml-2">Loading cache entry...</span>
                </div>
              ) : error ? (
                <div className="p-4 bg-red-900/30 border border-red-700 rounded-md">
                  <p className="font-semibold">Error loading cache entry:</p>
                  <p>{error}</p>
                </div>
              ) : cacheEntry ? (
                <div className="p-4 bg-neutral-800 border border-neutral-700 rounded-lg">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Cache Entry Details
                  </h3>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                    <div className="space-y-1">
                      <label className="text-sm text-neutral-400">Cache ID</label>
                      <div className="text-neutral-200 font-mono text-sm bg-neutral-700 px-2 py-1 rounded">
                        #{cacheEntry.id}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm text-neutral-400">Template Type</label>
                      <div className="flex items-center gap-2">
                        <span className="text-sm px-2 py-1 rounded text-white" style={{ 
                          backgroundColor: getTemplateColor(cacheEntry.template_type)
                        }}>
                          {getTemplateIcon(cacheEntry.template_type)} {cacheEntry.template_type}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm text-neutral-400">Status</label>
                      <div className="text-neutral-200 capitalize">{cacheEntry.status}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                    <div className="space-y-1">
                      <label className="text-sm text-neutral-400">Catalog Type</label>
                      <div className="text-neutral-200">{cacheEntry.catalog_type || "N/A"}</div>
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm text-neutral-400">Catalog Subtype</label>
                      <div className="text-neutral-200">{cacheEntry.catalog_subtype || "N/A"}</div>
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm text-neutral-400">Catalog Name</label>
                      <div className="text-neutral-200">{cacheEntry.catalog_name || "N/A"}</div>
                    </div>
                  </div>
                  
                  <div className="space-y-1 mb-4">
                    <label className="text-sm text-neutral-400">Natural Language Query</label>
                    <div className="p-3 bg-neutral-700 border border-neutral-600 rounded-md break-words">
                      {cacheEntry.nl_query}
                    </div>
                  </div>
                  
                  <div className="space-y-1 mb-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-neutral-400">Template</label>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(cacheEntry.template)}
                          className="h-6 px-2 text-xs"
                        >
                          <Copy className="h-3 w-3 mr-1" />
                          Copy
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setIsTemplateExpanded(!isTemplateExpanded)}
                          className="h-6 px-2 text-xs"
                        >
                          {isTemplateExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                          {isTemplateExpanded ? 'Collapse' : 'Expand'}
                        </Button>
                      </div>
                    </div>
                    <div className={`transition-all duration-200 ${isTemplateExpanded ? 'max-h-none' : 'max-h-32'} overflow-hidden`}>
                      <pre className="p-3 bg-neutral-700 border border-neutral-600 rounded-md overflow-auto font-mono text-sm whitespace-pre-wrap break-all">
                        {cacheEntry.template}
                      </pre>
                    </div>
                  </div>
                  
                  {cacheEntry.reasoning_trace && (
                    <div className="space-y-1 mb-4">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-neutral-400">Reasoning Trace</label>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyToClipboard(cacheEntry.reasoning_trace)}
                            className="h-6 px-2 text-xs"
                          >
                            <Copy className="h-3 w-3 mr-1" />
                            Copy
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
                            className="h-6 px-2 text-xs"
                          >
                            {isReasoningExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                            {isReasoningExpanded ? 'Collapse' : 'Expand'}
                          </Button>
                        </div>
                      </div>
                      <div className={`transition-all duration-200 ${isReasoningExpanded ? 'max-h-none' : 'max-h-32'} overflow-hidden`}>
                        <pre className="p-3 bg-neutral-700 border border-neutral-600 rounded-md overflow-auto font-mono text-sm whitespace-pre-wrap break-words">
                          {cacheEntry.reasoning_trace}
                        </pre>
                      </div>
                    </div>
                  )}

                  {cacheEntry.usage_count !== undefined && (
                    <div className="space-y-1 mb-4">
                      <label className="text-sm text-neutral-400 flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        Usage Count
                      </label>
                      <div className="text-green-400 font-semibold">
                        Used {cacheEntry.usage_count} time{cacheEntry.usage_count !== 1 ? 's' : ''}
                      </div>
                    </div>
                  )}

                  {cacheEntry.created_at && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-neutral-600">
                      <div className="space-y-1">
                        <label className="text-sm text-neutral-400 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Created
                        </label>
                        <div className="text-neutral-200 text-sm">
                          {new Date(cacheEntry.created_at).toLocaleString()}
                        </div>
                      </div>
                      {cacheEntry.updated_at && (
                        <div className="space-y-1">
                          <label className="text-sm text-neutral-400 flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Updated
                          </label>
                          <div className="text-neutral-200 text-sm">
                            {new Date(cacheEntry.updated_at).toLocaleString()}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-4 bg-neutral-800 border border-neutral-700 rounded-lg text-center">
                  No cache entry found for this node
                </div>
              )}
            </>
          )}

          {/* Additional Node Metadata */}
          {node.data && Object.keys(node.data).filter(key => 
            !['label', 'cacheEntryId', 'templateType'].includes(key)
          ).length > 0 && (
            <div className="p-4 bg-neutral-800 border border-neutral-700 rounded-lg">
              <h3 className="text-lg font-semibold mb-4">Additional Node Data</h3>
              <pre className="p-3 bg-neutral-700 border border-neutral-600 rounded-md overflow-auto max-h-[200px] font-mono text-sm whitespace-pre-wrap break-words">
                {JSON.stringify(
                  Object.fromEntries(
                    Object.entries(node.data).filter(([key]) => 
                      !['label', 'cacheEntryId', 'templateType'].includes(key)
                    )
                  ), 
                  null, 
                  2
                )}
              </pre>
            </div>
          )}

          {/* Special handling for start node */}
          {node.id === 'start' && (
            <div className="p-4 bg-green-900/30 border border-green-700 rounded-lg">
              <h3 className="text-lg font-semibold mb-2 text-green-400">Start Node</h3>
              <p className="text-neutral-300">
                This is the workflow start node. All workflows begin here. You can connect other nodes to this one to define your workflow sequence.
              </p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}