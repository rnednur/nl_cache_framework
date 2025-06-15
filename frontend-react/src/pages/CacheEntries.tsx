import { useState, useEffect, useRef, useCallback } from "react"
import { Link, useParams, useNavigate, Routes, Route, useLocation } from "react-router-dom"
import { PlusCircle, Edit, Trash2, Search, Filter, X, GripVertical } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import api, { type CacheItem, type CatalogValues } from "@/services/api"
import toast from "react-hot-toast"
import { CacheEntryForm } from "@/components/CacheEntryForm"

export default function CacheEntriesRoutes() {
  return (
    <Routes>
      <Route path="/cache-entries/create" element={<CreateCacheEntry />} />
      <Route path="/cache-entries/:id" element={<ViewCacheEntry />} />
      <Route path="/cache-entries/:id/edit" element={<EditCacheEntry />} />
      <Route path="/cache-entries" element={<CacheEntries />} />
    </Routes>
  )
}

function EditCacheEntry() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isGeneratingReasoning, setIsGeneratingReasoning] = useState(false)

  // Form state
  const [nlQuery, setNlQuery] = useState("")
  const [template, setTemplate] = useState("")
  const [templateType, setTemplateType] = useState("sql")
  const [reasoningTrace, setReasoningTrace] = useState("")
  const [catalogType, setCatalogType] = useState<string | undefined>(undefined)
  const [catalogSubtype, setCatalogSubtype] = useState<string | undefined>(undefined)
  const [catalogName, setCatalogName] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState("active")

  // Tags as string[] for now
  const [tags, setTags] = useState<string[]>([])
  const [tagNameInput, setTagNameInput] = useState("")

  useEffect(() => {
    async function fetchEntry() {
      setLoading(true)
      try {
        const entry = await api.getCacheEntry(Number(id))
        setNlQuery(entry.nl_query)
        setTemplate(entry.template)
        setTemplateType(entry.template_type)
        setReasoningTrace(entry.reasoning_trace || "")
        setCatalogType(entry.catalog_type || undefined)
        setCatalogSubtype(entry.catalog_subtype || undefined)
        setCatalogName(entry.catalog_name || undefined)
        setStatus(entry.status || "active")
        // Convert tags to string[] for now (TODO: support Record<string, string[]>)
        if (entry.tags) {
          if (Array.isArray(entry.tags)) {
            setTags(entry.tags)
          } else if (typeof entry.tags === "object") {
            setTags(Object.keys(entry.tags))
          }
        } else {
          setTags([])
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch cache entry")
      } finally {
        setLoading(false)
      }
    }
    fetchEntry()
  }, [id])

  const handleGenerateReasoning = async () => {
    if (!nlQuery.trim() || !template.trim()) {
      toast.error("Both Natural Language Query and Template are required to generate reasoning.")
      return
    }
    setIsGeneratingReasoning(true)
    try {
      const generated = await api.generateReasoningTrace(nlQuery, template, templateType)
      setReasoningTrace(generated)
      toast.success("AI has generated a reasoning trace for your query and template.")
    } catch (err: any) {
      toast.error(err.message || "An error occurred while generating reasoning.")
    } finally {
      setIsGeneratingReasoning(false)
    }
  }

  const addTag = (tag: string) => {
    if (!tag.trim() || tags.includes(tag.trim())) return
    setTags([...tags, tag.trim()])
    setTagNameInput("")
  }
  const removeTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag))
  }
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      addTag(tagNameInput)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nlQuery.trim() || !template.trim()) {
      setError("Natural Language Query and Template are required.")
      return
    }
    setSaving(true)
    setError(null)
    try {
      await api.updateCacheEntry(Number(id), {
        nl_query: nlQuery,
        template,
        template_type: templateType,
        is_template: true,
        tags: tags.length > 0 ? Object.fromEntries(tags.map(tag => [tag, ["default"]])) : undefined, // Convert to Record<string, string[]>
        reasoning_trace: reasoningTrace || undefined,
        catalog_type: catalogType?.trim() || undefined,
        catalog_subtype: catalogSubtype?.trim() || undefined,
        catalog_name: catalogName?.trim() || undefined,
        status,
      })
      toast.success("Cache entry updated successfully")
      navigate("/cache-entries")
    } catch (err: any) {
      setError(err.message || "Failed to update cache entry")
    } finally {
      setSaving(false)
    }
  }

  // Smart back navigation
  const handleBack = () => {
    if (location.state?.from) {
      navigate(location.state.from)
    } else if (window.history.length > 1) {
      navigate(-1)
    } else {
      navigate("/cache-entries")
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-[400px]"><div className="text-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div><p className="mt-2 text-sm text-gray-600">Loading cache entry...</p></div></div>
  }
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight px-2">Edit Cache Entry</h1>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="w-full  mx-auto px-2">
          {error && <div className="bg-red-50 text-red-600 p-4 rounded-md border border-red-200 text-sm mb-4">{error}</div>}
          <CacheEntryForm
            nlQuery={nlQuery}
            setNlQuery={setNlQuery}
            template={template}
            setTemplate={setTemplate}
            templateType={templateType}
            setTemplateType={setTemplateType}
            reasoningTrace={reasoningTrace}
            setReasoningTrace={setReasoningTrace}
            catalogType={catalogType}
            setCatalogType={setCatalogType}
            catalogSubtype={catalogSubtype}
            setCatalogSubtype={setCatalogSubtype}
            catalogName={catalogName}
            setCatalogName={setCatalogName}
            status={status}
            setStatus={setStatus}
            tags={tags}
            addTag={addTag}
            removeTag={removeTag}
            tagNameInput={tagNameInput}
            setTagNameInput={setTagNameInput}
            handleKeyDown={handleKeyDown}
            error={null}
            onGenerateReasoning={handleGenerateReasoning}
            isGeneratingReasoning={isGeneratingReasoning}
          >
            <div className="flex justify-end border-t pt-6 mt-6 px-6 pb-6 gap-4">
              <button type="button" className="px-6 py-2 rounded bg-gray-200 text-gray-800" onClick={handleBack}>Back</button>
              <button type="submit" className="px-6 py-2 rounded bg-blue-600 text-white" disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button>
            </div>
          </CacheEntryForm>
        </div>
      </form>
    </div>
  )
}

function CreateCacheEntry() {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isGeneratingReasoning, setIsGeneratingReasoning] = useState(false);
  const [nlQuery, setNlQuery] = useState("");
  const [template, setTemplate] = useState("");
  const [templateType, setTemplateType] = useState("sql");
  const [reasoningTrace, setReasoningTrace] = useState("");
  const [catalogType, setCatalogType] = useState<string | undefined>(undefined);
  const [catalogSubtype, setCatalogSubtype] = useState<string | undefined>(undefined);
  const [catalogName, setCatalogName] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState("active");
  const [tags, setTags] = useState<string[]>([]);
  const [tagNameInput, setTagNameInput] = useState("");

  // Smart back navigation
  const handleBack = () => {
    if (location.state?.from) {
      navigate(location.state.from);
    } else if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/cache-entries");
    }
  };

  const handleGenerateReasoning = async () => {
    if (!nlQuery.trim() || !template.trim()) {
      toast.error("Both Natural Language Query and Template are required to generate reasoning.");
      return;
    }
    setIsGeneratingReasoning(true);
    try {
      const generated = await api.generateReasoningTrace(nlQuery, template, templateType);
      setReasoningTrace(generated);
      toast.success("AI has generated a reasoning trace for your query and template.");
    } catch (err: any) {
      toast.error(err.message || "An error occurred while generating reasoning.");
    } finally {
      setIsGeneratingReasoning(false);
    }
  };

  const addTag = (tag: string) => {
    if (!tag.trim() || tags.includes(tag.trim())) return;
    setTags([...tags, tag.trim()]);
    setTagNameInput("");
  };
  const removeTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag(tagNameInput);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlQuery.trim() || !template.trim()) {
      setError("Natural Language Query and Template are required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.createCacheEntry({
        nl_query: nlQuery,
        template,
        template_type: templateType,
        is_template: true,
        tags: tags.length > 0 ? Object.fromEntries(tags.map(tag => [tag, ["default"]])) : undefined,
        reasoning_trace: reasoningTrace || undefined,
        catalog_type: catalogType?.trim() || undefined,
        catalog_subtype: catalogSubtype?.trim() || undefined,
        catalog_name: catalogName?.trim() || undefined,
        status,
      });
      toast.success("Cache entry created successfully");
      navigate("/cache-entries");
    } catch (err: any) {
      setError(err.message || "Failed to create cache entry");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight px-2">Create Cache Entry</h1>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="w-full mx-auto px-2">
          {error && <div className="bg-red-50 text-red-600 p-4 rounded-md border border-red-200 text-sm mb-4">{error}</div>}
          <CacheEntryForm
            nlQuery={nlQuery}
            setNlQuery={setNlQuery}
            template={template}
            setTemplate={setTemplate}
            templateType={templateType}
            setTemplateType={setTemplateType}
            reasoningTrace={reasoningTrace}
            setReasoningTrace={setReasoningTrace}
            catalogType={catalogType}
            setCatalogType={setCatalogType}
            catalogSubtype={catalogSubtype}
            setCatalogSubtype={setCatalogSubtype}
            catalogName={catalogName}
            setCatalogName={setCatalogName}
            status={status}
            setStatus={setStatus}
            tags={tags}
            addTag={addTag}
            removeTag={removeTag}
            tagNameInput={tagNameInput}
            setTagNameInput={setTagNameInput}
            handleKeyDown={handleKeyDown}
            error={null}
            onGenerateReasoning={handleGenerateReasoning}
            isGeneratingReasoning={isGeneratingReasoning}
          >
            <div className="flex justify-end border-t pt-6 mt-6 px-6 pb-6 gap-4">
              <button type="button" className="px-6 py-2 rounded bg-gray-200 text-gray-800" onClick={handleBack}>Back</button>
              <button type="submit" className="px-6 py-2 rounded bg-blue-600 text-white" disabled={loading}>{loading ? "Saving..." : "Create Entry"}</button>
            </div>
          </CacheEntryForm>
        </div>
      </form>
    </div>
  );
}

export function CacheEntries() {
  const [entries, setEntries] = useState<CacheItem[]>([])
  const [loading, setLoading] = useState(true)
  const [totalEntries, setTotalEntries] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const location = useLocation()
  
  // Search and similarity
  const [searchQuery, setSearchQuery] = useState("")
  const [searchInputValue, setSearchInputValue] = useState("")
  const [useSimilaritySearch, setUseSimilaritySearch] = useState(false)
  
  // Table filters
  const [templateTypeFilter, setTemplateTypeFilter] = useState<string>("all")
  const [catalogTypeFilter, setCatalogTypeFilter] = useState<string>("all")
  const [catalogSubtypeFilter, setCatalogSubtypeFilter] = useState<string>("all")
  const [catalogNameFilter, setCatalogNameFilter] = useState<string>("all")
  
  // Column widths
  const [columnWidths, setColumnWidths] = useState({
    query: 300,
    templateType: 130,
    catalogType: 130,
    catalogSubtype: 130,
    catalogName: 130,
    tags: 130,
    usageCount: 100,
    actions: 100
  })
  
  const [isResizing, setIsResizing] = useState<string | null>(null)
  const [resizeStartX, setResizeStartX] = useState(0)
  const [resizeStartWidth, setResizeStartWidth] = useState(0)
  
  const tableRef = useRef<HTMLDivElement>(null)
  
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({ 
    catalog_types: [], 
    catalog_subtypes: [], 
    catalog_names: [] 
  })

  // Resize handlers
  const handleResizeStart = useCallback((column: string, e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(column)
    setResizeStartX(e.clientX)
    setResizeStartWidth(columnWidths[column as keyof typeof columnWidths])
  }, [columnWidths])

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return
    
    const diff = e.clientX - resizeStartX
    const newWidth = Math.max(80, resizeStartWidth + diff) // Minimum width of 80px
    
    setColumnWidths(prev => ({
      ...prev,
      [isResizing]: newWidth
    }))
  }, [isResizing, resizeStartX, resizeStartWidth])

  const handleResizeEnd = useCallback(() => {
    setIsResizing(null)
  }, [])

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleResizeMove)
      document.addEventListener('mouseup', handleResizeEnd)
      
      return () => {
        document.removeEventListener('mousemove', handleResizeMove)
        document.removeEventListener('mouseup', handleResizeEnd)
      }
    }
  }, [isResizing, handleResizeMove, handleResizeEnd])

  useEffect(() => {
    const fetchCatalogValues = async () => {
      try {
        const values = await api.getCatalogValues()
        setCatalogValues(values)
      } catch (err) {
        console.error("Failed to fetch catalog values", err)
        setCatalogValues({ 
          catalog_types: [], 
          catalog_subtypes: [], 
          catalog_names: [] 
        })
      }
    }
    fetchCatalogValues()
  }, [])

  useEffect(() => {
    const fetchEntries = async () => {
      setLoading(true)
      try {
        let data
        if (useSimilaritySearch && searchQuery.trim()) {
          const similarEntries = await api.searchCacheEntries(
            searchQuery,
            templateTypeFilter === "all" ? undefined : templateTypeFilter,
            0.7,
            pageSize,
            catalogTypeFilter === "all" ? undefined : catalogTypeFilter,
            catalogSubtypeFilter === "all" ? undefined : catalogSubtypeFilter,
            catalogNameFilter === "all" ? undefined : catalogNameFilter
          )
          data = { items: similarEntries, total: similarEntries.length }
        } else {
          data = await api.getCacheEntries(
            currentPage,
            pageSize,
            templateTypeFilter === "all" ? undefined : templateTypeFilter,
            searchQuery || undefined,
            catalogTypeFilter === "all" ? undefined : catalogTypeFilter,
            catalogSubtypeFilter === "all" ? undefined : catalogSubtypeFilter,
            catalogNameFilter === "all" ? undefined : catalogNameFilter
          )
        }
        setEntries(data.items)
        setTotalEntries(data.total)
      } catch (error) {
        console.error("Failed to fetch cache entries:", error)
        toast.error("Failed to load cache entries")
      } finally {
        setLoading(false)
      }
    }

    fetchEntries()
  }, [currentPage, pageSize, templateTypeFilter, catalogTypeFilter, catalogSubtypeFilter, catalogNameFilter, searchQuery, useSimilaritySearch])

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [templateTypeFilter, catalogTypeFilter, catalogSubtypeFilter, catalogNameFilter, searchQuery])

  const totalPages = Math.ceil(totalEntries / pageSize)

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(searchInputValue)
  }

  const handleDeleteEntry = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this cache entry?")) {
      try {
        await api.deleteCacheEntry(id)
        toast.success("Cache entry deleted successfully")
        // Refresh entries
        const data = await api.getCacheEntries(currentPage, pageSize, templateTypeFilter === "all" ? undefined : templateTypeFilter, searchQuery || undefined)
        setEntries(data.items)
        setTotalEntries(data.total)
      } catch (error) {
        console.error(`Failed to delete cache entry with ID ${id}:`, error)
        toast.error("Failed to delete cache entry")
      }
    }
  }

  const clearAllFilters = () => {
    setTemplateTypeFilter("all")
    setCatalogTypeFilter("all")
    setCatalogSubtypeFilter("all")
    setCatalogNameFilter("all")
    setSearchQuery("")
    setSearchInputValue("")
  }

  const hasActiveFilters = templateTypeFilter !== "all" || catalogTypeFilter !== "all" || 
                          catalogSubtypeFilter !== "all" || catalogNameFilter !== "all" || 
                          searchQuery !== ""

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Cache Entries</h1>
        </div>
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Cache Entries</h1>
        <Link to="/cache-entries/create" state={{ from: location.pathname }}>
          <Button className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white">
            <PlusCircle className="mr-2 h-4 w-4" />
            Create Entry
          </Button>
        </Link>
      </div>

      {/* Search Section */}
      <Card className="bg-card border-border shadow-sm">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="similarity-search"
                checked={useSimilaritySearch}
                onCheckedChange={setUseSimilaritySearch}
              />
              <Label htmlFor="similarity-search" className="text-sm text-card-foreground whitespace-nowrap">
                Similarity Search
              </Label>
            </div>
            
            <form onSubmit={handleSearch} className="flex gap-2 flex-1">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search cache entries..."
                  className="pl-8 bg-secondary border-border text-secondary-foreground focus-visible:ring-[#3B4BF6] placeholder:text-muted-foreground"
                  value={searchInputValue}
                  onChange={(e) => setSearchInputValue(e.target.value)}
                />
              </div>
              <Button type="submit" className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white">
                Search
              </Button>
            </form>

            {hasActiveFilters && (
              <Button variant="outline" size="sm" onClick={clearAllFilters} className="whitespace-nowrap">
                <X className="mr-1 h-3 w-3" />
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Entries Table */}
      <Card className="bg-card border-border shadow-sm">
        <CardContent className="p-0">
          <div className="overflow-x-auto" ref={tableRef}>
            <Table style={{ minWidth: Object.values(columnWidths).reduce((a, b) => a + b, 0) }}>
              <TableHeader>
                <TableRow className="bg-secondary hover:bg-secondary">
                  <TableHead style={{ width: columnWidths.query }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Query</span>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-2 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group"
                      onMouseDown={(e) => handleResizeStart('query', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.templateType }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Template Type</span>
                      <Select value={templateTypeFilter} onValueChange={setTemplateTypeFilter}>
                        <SelectTrigger className="h-6 w-6 p-0 border-0 bg-transparent">
                          <Filter className="h-3 w-3" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Types</SelectItem>
                          <SelectItem value="sql">SQL</SelectItem>
                          <SelectItem value="url">URL</SelectItem>
                          <SelectItem value="api">API</SelectItem>
                          <SelectItem value="workflow">Workflow</SelectItem>
                          <SelectItem value="graphql">GraphQL</SelectItem>
                          <SelectItem value="regex">Regex</SelectItem>
                          <SelectItem value="script">Script</SelectItem>
                          <SelectItem value="nosql">NoSQL</SelectItem>
                          <SelectItem value="cli">CLI</SelectItem>
                          <SelectItem value="reasoning_steps">Reasoning Steps</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-2 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group"
                      onMouseDown={(e) => handleResizeStart('templateType', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.catalogType }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Catalog Type</span>
                      <Select value={catalogTypeFilter} onValueChange={setCatalogTypeFilter}>
                        <SelectTrigger className="h-6 w-6 p-0 border-0 bg-transparent">
                          <Filter className="h-3 w-3" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Types</SelectItem>
                          {catalogValues.catalog_types.map((type) => (
                            <SelectItem key={type} value={type}>{type}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-2 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group"
                      onMouseDown={(e) => handleResizeStart('catalogType', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.catalogSubtype }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Catalog Subtype</span>
                      <Select value={catalogSubtypeFilter} onValueChange={setCatalogSubtypeFilter}>
                        <SelectTrigger className="h-6 w-6 p-0 border-0 bg-transparent">
                          <Filter className="h-3 w-3" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Subtypes</SelectItem>
                          {catalogValues.catalog_subtypes.map((subtype) => (
                            <SelectItem key={subtype} value={subtype}>{subtype}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-2 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group"
                      onMouseDown={(e) => handleResizeStart('catalogSubtype', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.catalogName }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Catalog Name</span>
                      <Select value={catalogNameFilter} onValueChange={setCatalogNameFilter}>
                        <SelectTrigger className="h-6 w-6 p-0 border-0 bg-transparent">
                          <Filter className="h-3 w-3" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Names</SelectItem>
                          {catalogValues.catalog_names.map((name) => (
                            <SelectItem key={name} value={name}>{name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-2 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group"
                      onMouseDown={(e) => handleResizeStart('catalogName', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.tags }} className="relative">
                    <div className="flex items-center gap-2">
                      <span>Updated At</span>
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.usageCount }} className="relative text-center">
                    <div className="flex items-center gap-2 justify-center">
                      <span>Usage Count</span>
                    </div>
                    <div 
                      className="absolute right-0 top-0 w-2 h-full cursor-col-resize hover:bg-blue-500/20 flex items-center justify-center group"
                      onMouseDown={(e) => handleResizeStart('usageCount', e)}
                    >
                      <GripVertical className="h-3 w-3 text-muted-foreground group-hover:text-blue-500" />
                    </div>
                  </TableHead>
                  <TableHead style={{ width: columnWidths.actions }} className="text-right">
                    <span>Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => (
                  <TableRow key={entry.id}>
                      <TableCell style={{ width: columnWidths.query }}>
                        <div className="font-medium text-card-foreground pr-4 break-words">
                          <Link to={`/cache-entries/${entry.id}`} className="text-blue-400 hover:underline" state={{ from: location.pathname }}>
                            {entry.nl_query}
                          </Link>
                        </div>
                    </TableCell>
                    <TableCell style={{ width: columnWidths.templateType }}>
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-600 text-white">
                        {entry.template_type}
                      </span>
                    </TableCell>
                    <TableCell style={{ width: columnWidths.catalogType }} className="text-card-foreground">
                      {entry.catalog_type || "Not Specified"}
                    </TableCell>
                    <TableCell style={{ width: columnWidths.catalogSubtype }} className="text-card-foreground">
                      {entry.catalog_subtype || "Not Specified"}
                    </TableCell>
                    <TableCell style={{ width: columnWidths.catalogName }} className="text-card-foreground">
                      {entry.catalog_name || "Not Specified"}
                    </TableCell>
                    <TableCell style={{ width: columnWidths.tags }} className="text-muted-foreground">
                      <div>
                        {entry.updated_at ? new Date(entry.updated_at).toLocaleString() : "-"}
                      </div>
                    </TableCell>
                    <TableCell style={{ width: columnWidths.usageCount }} className="text-card-foreground text-center">
                      {entry.usage_count}
                    </TableCell>
                    <TableCell style={{ width: columnWidths.actions }}>
                      <div className="flex items-center justify-end gap-1">
                        <Link to={`/cache-entries/${entry.id}`} state={{ from: location.pathname }}>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <Edit className="h-4 w-4" />
                          </Button>
                        </Link>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleDeleteEntry(entry.id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                Showing {pageSize} of {totalEntries} entries
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handlePreviousPage} disabled={currentPage <= 1}>
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {currentPage} of {totalPages || 1}
              </span>
              <Button variant="outline" size="sm" onClick={handleNextPage} disabled={currentPage >= totalPages}>
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ViewCacheEntry() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [entry, setEntry] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Smart back navigation
  const handleBack = () => {
    if (location.state?.from) {
      navigate(location.state.from);
    } else if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/cache-entries");
    }
  };

  useEffect(() => {
    const fetchEntry = async () => {
      try {
        const data = await api.getCacheEntry(Number(id));
        setEntry(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch cache entry");
      } finally {
        setLoading(false);
      }
    };
    fetchEntry();
  }, [id]);

  if (loading) {
    return <div className="flex items-center justify-center min-h-[400px]"><div className="animate-spin h-8 w-8 border-b-2 border-blue-500 mr-2"></div>Loading entry...</div>;
  }

  if (error || !entry) {
    return <div className="p-4 text-red-500">{error || "Entry not found"}</div>;
  }

  return (
    <div className="space-y-6 px-2">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Cache Entry #{id}</h1>
        <Button onClick={() => navigate(`/cache-entries/${id}/edit`)} variant="outline">Edit</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
          <CardDescription>Overview of cache entry</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label className="text-neutral-400 text-sm">Catalog Type</Label>
              <p>{entry.catalog_type || "N/A"}</p>
            </div>
            <div>
              <Label className="text-neutral-400 text-sm">Catalog Subtype</Label>
              <p>{entry.catalog_subtype || "N/A"}</p>
            </div>
            <div>
              <Label className="text-neutral-400 text-sm">Catalog Name</Label>
              <p>{entry.catalog_name || "N/A"}</p>
            </div>
          </div>

          <div>
            <Label className="text-neutral-400 text-sm">Natural Language Query</Label>
            <div className="p-3 bg-neutral-800 rounded border border-neutral-700 mt-1 whitespace-pre-wrap">{entry.nl_query}</div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label className="text-neutral-400 text-sm">Template Type</Label>
              <p className="capitalize mt-1">{entry.template_type}</p>
            </div>
            <div>
              <Label className="text-neutral-400 text-sm">Status</Label>
              <p className="capitalize mt-1">{entry.status}</p>
            </div>
          </div>

          <div>
            <Label className="text-neutral-400 text-sm">Template</Label>
            <pre className="p-3 bg-neutral-800 rounded border border-neutral-700 mt-1 whitespace-pre-wrap overflow-auto max-h-[200px]">{entry.template}</pre>
          </div>

          {entry.reasoning_trace && (
            <div>
              <Label className="text-neutral-400 text-sm">Reasoning Trace</Label>
              <pre className="p-3 bg-neutral-800 rounded border border-neutral-700 mt-1 whitespace-pre-wrap overflow-auto max-h-[200px]">{entry.reasoning_trace}</pre>
            </div>
          )}

          <div className="flex justify-end border-t pt-6 mt-6 px-6 pb-6 gap-4">
            <button type="button" className="px-6 py-2 rounded bg-gray-200 text-gray-800" onClick={handleBack}>Back</button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 