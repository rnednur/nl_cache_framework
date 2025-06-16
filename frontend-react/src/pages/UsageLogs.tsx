import { useEffect, useState, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Clock, Filter, X, GripVertical } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SimpleCacheTooltip } from "@/components/ui/simple-cache-tooltip";
import api, { type UsageLog, type CatalogValues, type CacheItem } from "@/services/api";

// Cache entry hover tooltip component
function CacheEntryHoverTooltip({ entryId, children }: { entryId: number; children: React.ReactNode }) {
  const [entryData, setEntryData] = useState<CacheItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEntryData = async () => {
    if (entryData || loading) return; // Don't fetch if already have data or currently loading
    
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCacheEntry(entryId);
      setEntryData(data);
    } catch (err) {
      console.error(`Error fetching cache entry ${entryId}:`, err);
      setError(`Failed to load entry ${entryId}`);
    } finally {
      setLoading(false);
    }
  };

  const tooltipContent = loading ? (
    <div className="flex items-center justify-center py-4">
      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
      <span className="ml-2 text-neutral-400 text-sm">Loading...</span>
    </div>
  ) : error ? (
    <div className="text-red-400 text-sm py-2">{error}</div>
  ) : entryData ? (
    <div className="space-y-2 max-w-[400px]">
      <div>
        <div className="text-neutral-400 text-xs mb-1">Query:</div>
        <div className="text-white text-sm">{entryData.nl_query}</div>
      </div>
      <div>
        <div className="text-neutral-400 text-xs mb-1">Template:</div>
        <pre className="text-white text-xs bg-neutral-800 p-2 rounded-md overflow-auto max-h-[100px] whitespace-pre-wrap">{entryData.template}</pre>
      </div>
      <div className="pt-2 text-center text-xs text-blue-400">
        Click to view full details
      </div>
    </div>
  ) : (
    <div className="text-sm">
      <p className="text-neutral-300 mb-1">Cache Entry ID: {entryId}</p>
      <p className="text-neutral-400 text-xs">Hover to load details...</p>
    </div>
  );

  return (
    <div onMouseEnter={fetchEntryData}>
      <SimpleCacheTooltip content={tooltipContent}>
        {children}
      </SimpleCacheTooltip>
    </div>
  );
}

export default function UsageLogs() {
  const pageSize = 10;
  const [logs, setLogs] = useState<UsageLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({ catalog_types: [], catalog_subtypes: [], catalog_names: [] });
  const location = useLocation();
  const [filters, setFilters] = useState({
    status: "all",   // all | success | error
    llm: "all",      // all | yes | no
    confidence: "all", // all | high | low
    catalogType: "all",
    catalogSubtype: "all",
    catalogName: "all",
    startDate: "",   // YYYY-MM-DD format
    endDate: "",     // YYYY-MM-DD format
  });

  // Separate state for pending date filters (before applying)
  const [pendingDateFilters, setPendingDateFilters] = useState({
    startDate: "",
    endDate: "",
  });

  // Column widths
  const [columnWidths, setColumnWidths] = useState({
    time: 120,
    status: 60,
    prompt: 360,
    response: 180,
    similarity: 70,
    consideredEntries: 180,
    llmUsed: 60,
    confidence: 60,
  });

  const [isResizing, setIsResizing] = useState<string | null>(null);
  const [resizeStartX, setResizeStartX] = useState(0);
  const [resizeStartWidth, setResizeStartWidth] = useState(0);
  const tableRef = useRef<HTMLDivElement>(null);

  // Resize handlers
  const handleResizeStart = useCallback((column: string, e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(column);
    setResizeStartX(e.clientX);
    setResizeStartWidth(columnWidths[column as keyof typeof columnWidths]);
  }, [columnWidths]);

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return;
    
    const diff = e.clientX - resizeStartX;
    const newWidth = Math.max(20, resizeStartWidth + diff);
    
    setColumnWidths(prev => ({
      ...prev,
      [isResizing]: newWidth
    }));
  }, [isResizing, resizeStartX, resizeStartWidth]);

  const handleResizeEnd = useCallback(() => {
    setIsResizing(null);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleResizeMove);
      document.addEventListener('mouseup', handleResizeEnd);
      
      return () => {
        document.removeEventListener('mousemove', handleResizeMove);
        document.removeEventListener('mouseup', handleResizeEnd);
      };
    }
  }, [isResizing, handleResizeMove, handleResizeEnd]);

  // fetch catalog dropdown values once
  useEffect(() => {
    api.getCatalogValues().then(setCatalogValues).catch(() => {});
  }, []);

  // fetch logs whenever page changes
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const data = await api.getUsageLogs(page, pageSize);
        setLogs(data.items);
        setTotal(data.total);
        console.log("Usage logs:", data.total);
      } catch (err) {
        console.error("Failed to fetch usage logs", err);
        setLogs([]);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, [page]);

  // client-side filtering
  const filteredLogs = logs.filter((log) => {
    if (filters.status !== "all") {
      const success = log.success_status;
      if (filters.status === "success" && !success) return false;
      if (filters.status === "error" && success) return false;
    }
    if (filters.llm !== "all") {
      const yes = log.llm_used;
      if (filters.llm === "yes" && !yes) return false;
      if (filters.llm === "no" && yes) return false;
    }
    if (filters.confidence !== "all") {
      if (log.is_confident === undefined) return false;
      if (filters.confidence === "high" && !log.is_confident) return false;
      if (filters.confidence === "low" && log.is_confident) return false;
    }
    if (filters.catalogType !== "all" && log.catalog_type !== filters.catalogType) return false;
    if (filters.catalogSubtype !== "all" && log.catalog_subtype !== filters.catalogSubtype) return false;
    if (filters.catalogName !== "all" && log.catalog_name !== filters.catalogName) return false;
    
    // Date range filtering
    if (filters.startDate || filters.endDate) {
      const logDate = new Date(log.timestamp).toISOString().split('T')[0]; // Get YYYY-MM-DD format
      if (filters.startDate && logDate < filters.startDate) return false;
      if (filters.endDate && logDate > filters.endDate) return false;
    }
    
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const handleFilterChange = (field: string, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
    setPage(1);
  };

  const handlePendingDateChange = (field: string, value: string) => {
    setPendingDateFilters((prev) => ({ ...prev, [field]: value }));
  };

  const applyDateFilters = () => {
    setFilters((prev) => ({
      ...prev,
      startDate: pendingDateFilters.startDate,
      endDate: pendingDateFilters.endDate,
    }));
    setPage(1);
  };

  const clearDateFilters = () => {
    setPendingDateFilters({ startDate: "", endDate: "" });
    setFilters((prev) => ({ ...prev, startDate: "", endDate: "" }));
    setPage(1);
  };

  const clearAllFilters = () => {
    setFilters({
      status: "all",
      llm: "all", 
      confidence: "all",
      catalogType: "all",
      catalogSubtype: "all",
      catalogName: "all",
      startDate: "",
      endDate: "",
    });
    setPendingDateFilters({ startDate: "", endDate: "" });
  };

  const hasActiveFilters = Object.entries(filters).some(([key, value]) => {
    if (key === 'startDate' || key === 'endDate') {
      return value !== "";
    }
    return value !== "all";
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Usage Logs</h1>
        {hasActiveFilters && (
          <Button variant="outline" size="sm" onClick={clearAllFilters}>
            <X className="mr-1 h-3 w-3" />
            Clear Filters
          </Button>
        )}
      </div>

      {/* Date Range Filter */}
      <Card className="bg-card border-border shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-card-foreground">Time Period Filter</CardTitle>
          <CardDescription className="text-muted-foreground">Filter logs by date range</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1">
              <Label htmlFor="start-date" className="text-xs text-muted-foreground block mb-1">Start Date</Label>
              <input
                id="start-date"
                type="date"
                value={pendingDateFilters.startDate}
                onChange={(e) => handlePendingDateChange("startDate", e.target.value)}
                className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-secondary-foreground focus:outline-none focus:ring-2 focus:ring-[#3B4BF6] focus:border-transparent"
              />
            </div>
            <div className="flex-1">
              <Label htmlFor="end-date" className="text-xs text-muted-foreground block mb-1">End Date</Label>
              <input
                id="end-date"
                type="date"
                value={pendingDateFilters.endDate}
                onChange={(e) => handlePendingDateChange("endDate", e.target.value)}
                className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-secondary-foreground focus:outline-none focus:ring-2 focus:ring-[#3B4BF6] focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  const today = new Date().toISOString().split('T')[0];
                  setPendingDateFilters({ startDate: today, endDate: today });
                }}
              >
                Today
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  const today = new Date();
                  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                  setPendingDateFilters({ 
                    startDate: lastWeek.toISOString().split('T')[0], 
                    endDate: today.toISOString().split('T')[0] 
                  });
                }}
              >
                Last 7 Days
              </Button>
              <Button 
                onClick={applyDateFilters}
                size="sm"
                className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white"
                disabled={!pendingDateFilters.startDate && !pendingDateFilters.endDate}
              >
                Apply
              </Button>
              {(filters.startDate || filters.endDate) && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={clearDateFilters}
                >
                  Clear
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card className="bg-card border-border shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-card-foreground">Logs ({filteredLogs.length} of {total})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto max-w-full" ref={tableRef}>
            <Table style={{ minWidth: Object.values(columnWidths).reduce((a, b) => a + b, 0), maxWidth: '100%', tableLayout: 'fixed' }}>
              <TableHeader>
                <TableRow className="bg-secondary hover:bg-secondary">
                  <TableHead style={{ width: columnWidths.time }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Time</span>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('time', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.status }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Status</span>
                      <Select value={filters.status} onValueChange={(v) => handleFilterChange("status", v)}>
                        <SelectTrigger className="h-6 w-6 p-0 border-0 bg-transparent">
                          <Filter className="h-3 w-3" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All</SelectItem>
                          <SelectItem value="success">Success</SelectItem>
                          <SelectItem value="error">Error</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('status', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.prompt }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Prompt</span>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('prompt', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.response }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Response</span>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('response', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.similarity }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Similarity</span>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('similarity', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>

                  <TableHead style={{ width: columnWidths.consideredEntries }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Considered Entries</span>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('consideredEntries', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.llmUsed }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>LLM Used</span>
                      <Select value={filters.llm} onValueChange={(v) => handleFilterChange("llm", v)}>
                        <SelectTrigger className="h-6 w-6 p-0 border-0 bg-transparent">
                          <Filter className="h-3 w-3" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All</SelectItem>
                          <SelectItem value="yes">Yes</SelectItem>
                          <SelectItem value="no">No</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('llmUsed', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.confidence }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Confidence</span>
                      <Select value={filters.confidence} onValueChange={(v) => handleFilterChange("confidence", v)}>
                        <SelectTrigger className="h-6 w-6 p-0 border-0 bg-transparent">
                          <Filter className="h-3 w-3" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All</SelectItem>
                          <SelectItem value="high">High</SelectItem>
                          <SelectItem value="low">Low</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group border-r-2 border-transparent hover:border-blue-500"
                      onMouseDown={(e) => handleResizeStart('confidence', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell className="py-6 px-4 text-center" colSpan={8}>Loading…</TableCell></TableRow>
                ) : filteredLogs.length === 0 ? (
                  <TableRow><TableCell className="py-6 px-4 text-center" colSpan={8}>No logs found</TableCell></TableRow>
                ) : (
                  filteredLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell style={{ width: columnWidths.time, maxWidth: columnWidths.time }} className="whitespace-nowrap overflow-hidden">
                        {new Date(log.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell style={{ width: columnWidths.status, maxWidth: columnWidths.status }} className="overflow-hidden">
                        {log.success_status ? (
                          <span className="flex items-center gap-1 text-green-500"><CheckCircle2 className="h-4 w-4" /> Success</span>
                        ) : (
                          <span className="flex items-center gap-1 text-red-500"><XCircle className="h-4 w-4" /> Error</span>
                        )}
                      </TableCell>
                      <TableCell style={{ width: columnWidths.prompt, maxWidth: columnWidths.prompt }} className="truncate overflow-hidden relative group" title={log.prompt}>
                        <span className="block truncate">{log.prompt}</span>
                        {log.prompt && log.prompt.length > 50 && (
                          <div className="absolute left-0 top-full mt-1 bg-gray-900 text-white p-2 rounded shadow-lg z-50 max-w-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
                            <div className="text-xs whitespace-pre-wrap break-words">{log.prompt}</div>
                          </div>
                        )}
                      </TableCell>
                      <TableCell style={{ width: columnWidths.response, maxWidth: columnWidths.response }} className="truncate font-mono text-xs overflow-hidden relative group" title={log.response}>
                        <span className="block truncate">{log.response || "-"}</span>
                        {log.response && log.response.length > 20 && (
                          <div className="absolute left-0 top-full mt-1 bg-gray-900 text-white p-2 rounded shadow-lg z-50 max-w-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
                            <div className="text-xs font-mono whitespace-pre-wrap break-words">{log.response}</div>
                          </div>
                        )}
                      </TableCell>
                      <TableCell style={{ width: columnWidths.similarity, maxWidth: columnWidths.similarity }} className="overflow-hidden">
                        {(log.similarity_score * 100).toFixed(2)}%
                      </TableCell>

                                              <TableCell style={{ width: columnWidths.consideredEntries, maxWidth: columnWidths.consideredEntries }} className="overflow-hidden">
                          {log.considered_entries && log.considered_entries.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {log.considered_entries.map((entryId, index) => (
                                <span key={entryId}>
                                  <CacheEntryHoverTooltip entryId={entryId}>
                                    <Link 
                                      to={`/cache-entries/${entryId}`} 
                                      className="text-blue-400 hover:underline text-xs" 
                                      state={{ from: location.pathname }}
                                    >
                                      {entryId}
                                    </Link>
                                  </CacheEntryHoverTooltip>
                                  {index < (log.considered_entries?.length || 0) - 1 }
                                </span>
                              ))}
                            </div>
                          ) : "-"}
                        </TableCell>
                      <TableCell style={{ width: columnWidths.llmUsed, maxWidth: columnWidths.llmUsed }} className="overflow-hidden">
                        {log.llm_used ? <span className="bg-violet-600/20 text-violet-400 px-2 py-0.5 rounded-md text-xs">Yes</span> : <span className="text-muted-foreground text-xs">No</span>}
                      </TableCell>
                      <TableCell style={{ width: columnWidths.confidence, maxWidth: columnWidths.confidence }} className="overflow-hidden">
                        {log.is_confident !== undefined ? (
                          <span className={`px-2 py-0.5 rounded-md text-xs ${log.is_confident ? 'bg-green-600/20 text-green-400' : 'bg-yellow-600/20 text-yellow-400'}`}>
                            {log.is_confident ? 'High' : 'Low'}
                          </span>
                        ) : "-"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                Showing {pageSize} of {total} entries
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page <= 1}>
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= totalPages}>
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 