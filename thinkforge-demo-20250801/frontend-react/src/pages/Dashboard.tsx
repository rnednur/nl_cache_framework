import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PlusCircle, Database, Code, Globe, Workflow, Search, Hash, Terminal, Layers, Command, Brain } from "lucide-react"
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts"
import api, { type CacheStats, type CatalogValues, type UsageLog } from "@/services/api"
import { Link, useLocation } from "react-router-dom"

export default function Dashboard() {
  const [stats, setStats] = useState<CacheStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [usageLogs, setUsageLogs] = useState<UsageLog[]>([])
  const [logsLoading, setLogsLoading] = useState(true)
  const [catalogType, setCatalogType] = useState("all")
  const [catalogSubtype, setCatalogSubtype] = useState("all") 
  const [catalogName, setCatalogName] = useState("all")
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({ 
    catalog_types: [], 
    catalog_subtypes: [], 
    catalog_names: [] 
  })
  const location = useLocation()

  useEffect(() => {
    const fetchCatalogValues = async () => {
      try {
        const values = await api.getCatalogValues()
        setCatalogValues(values)
      } catch (err) {
        console.error("Failed to fetch catalog values", err)
        // Set fallback mock data if API fails
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
    const fetchStats = async () => {
      setLoading(true)
      try {
        const data = await api.getCacheStats(
          undefined,
          catalogType === "all" ? undefined : catalogType,
          catalogSubtype === "all" ? undefined : catalogSubtype,
          catalogName === "all" ? undefined : catalogName
        )
        setStats(data)
      } catch (error) {
        console.error("Failed to fetch cache stats:", error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchStats()
  }, [catalogType, catalogSubtype, catalogName])

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLogsLoading(true)
        const data = await api.getUsageLogs(1, 10)
        setUsageLogs(data.items)
      } catch (err) {
        console.error("Failed to fetch usage logs", err)
      } finally {
        setLogsLoading(false)
      }
    }
    fetchLogs()
  }, [])

  const handleApplyFilters = () => {
    // Filters will be applied automatically via useEffect when state changes
  }

  const getTemplateIcon = (type: string) => {
    switch (type) {
      case 'sql': return <Database className="h-5 w-5" />
      case 'api': return <Code className="h-5 w-5" />
      case 'url': return <Globe className="h-5 w-5" />
      case 'workflow': return <Workflow className="h-5 w-5" />
      case 'graphql': return <Search className="h-5 w-5" />
      case 'regex': return <Hash className="h-5 w-5" />
      case 'script': return <Terminal className="h-5 w-5" />
      case 'nosql': return <Layers className="h-5 w-5" />
      case 'cli': return <Command className="h-5 w-5" />
      case 'reasoning_steps': return <Brain className="h-5 w-5" />
      default: return <Database className="h-5 w-5" />
    }
  }

  const count = (type: string) => stats?.by_template_type?.[type] ?? 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Dashboard Overview</h1>
        </div>
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Dashboard Overview</h1>
      </div>
      
      {/* Catalog Filters */}
      <Card className="bg-card border-border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-card-foreground">Catalog Filters</CardTitle>
          <CardDescription className="text-muted-foreground">
            Filter dashboard statistics by catalog
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="w-full sm:w-1/3">
              <label className="text-xs text-muted-foreground block mb-1">Catalog Type</label>
              <Select
                value={catalogType}
                onValueChange={(value) => {
                  setCatalogType(value)
                  setCatalogSubtype("all")
                  setCatalogName("all")
                }}
              >
                <SelectTrigger className="bg-secondary border-border text-secondary-foreground">
                  <SelectValue placeholder="Select catalog type" />
                </SelectTrigger>
                <SelectContent className="bg-secondary border-border text-secondary-foreground">
                  <SelectItem value="all" className="text-secondary-foreground">All Types</SelectItem>
                  {catalogValues.catalog_types.map((type) => (
                    <SelectItem key={type} value={type} className="text-secondary-foreground">
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="w-full sm:w-1/3">
              <label className="text-xs text-muted-foreground block mb-1">Catalog Subtype</label>
              <Select
                value={catalogSubtype}
                onValueChange={(value) => {
                  setCatalogSubtype(value)
                  setCatalogName("all")
                }}
              >
                <SelectTrigger className="bg-secondary border-border text-secondary-foreground">
                  <SelectValue placeholder="Select catalog subtype" />
                </SelectTrigger>
                <SelectContent className="bg-secondary border-border text-secondary-foreground">
                  <SelectItem value="all" className="text-secondary-foreground">All Subtypes</SelectItem>
                  {catalogValues.catalog_subtypes.map((subtype) => (
                    <SelectItem key={subtype} value={subtype} className="text-secondary-foreground">
                      {subtype}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="w-full sm:w-1/3">
              <label className="text-xs text-muted-foreground block mb-1">Catalog Name</label>
              <Select
                value={catalogName}
                onValueChange={setCatalogName}
              >
                <SelectTrigger className="bg-secondary border-border text-secondary-foreground">
                  <SelectValue placeholder="Select catalog name" />
                </SelectTrigger>
                <SelectContent className="bg-secondary border-border text-secondary-foreground">
                  <SelectItem value="all" className="text-secondary-foreground">All Names</SelectItem>
                  {catalogValues.catalog_names.map((name) => (
                    <SelectItem key={name} value={name} className="text-secondary-foreground">
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="w-full sm:w-auto flex items-end">
              <Button 
                onClick={handleApplyFilters}
                className="bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white w-full sm:w-auto"
              >
                Apply Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Statistics Grid */}
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Cache Entries */}
        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">Total Cache Entries</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{stats?.total_entries || 0}</div>
            <p className="text-xs text-muted-foreground">Across all template types</p>
          </CardContent>
        </Card>

        {/* SQL Templates */}
        {count("sql") > 0 && (
        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">SQL Templates</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{count("sql")}</div>
            <p className="text-xs text-muted-foreground">SQL query templates</p>
          </CardContent>
        </Card>)}

        {/* API Templates */}
        {count("api") > 0 && (
        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">API Templates</CardTitle>
            <Code className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{count("api")}</div>
            <p className="text-xs text-muted-foreground">API call templates</p>
          </CardContent>
        </Card>)}

        {/* URL Templates */}
        {count("url") > 0 && (
          <Card className="bg-card border-border shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-card-foreground">URL Templates</CardTitle>
              <Globe className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-card-foreground">
                {count("url")}
              </div>
              <p className="text-xs text-muted-foreground">URL templates</p>
            </CardContent>
          </Card>
        )}
      
      {/* More Template Types Grid */}
      {count("workflow") > 0 && (
        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">Workflow Templates</CardTitle>
            <Workflow className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{count("workflow")}</div>
            <p className="text-xs text-muted-foreground">Workflow templates</p>
          </CardContent>
        </Card>
      )}

        {/* GraphQL Templates */}
        {count("graphql") > 0 && (
        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">GraphQL Templates</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{count("graphql")}</div>
            <p className="text-xs text-muted-foreground">GraphQL query templates</p>
          </CardContent>
        </Card>)}

        {/* Regex Templates */}
        {count("regex") > 0 && (
          <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">Regex Templates</CardTitle>
            <Hash className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{count("regex")}</div>
            <p className="text-xs text-muted-foreground">Regular expression templates</p>
          </CardContent>
        </Card>)}

        {/* Script Templates */}
        {count("script") > 0 && (
          <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">Script Templates</CardTitle>
            <Terminal className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{count("script")}</div>
            <p className="text-xs text-muted-foreground">Script templates</p>
          </CardContent>
        </Card>)}

      </div>

      {/* Additional Template Cards */}
      {/* NoSQL Templates */}
      {count("nosql") > 0 && (
        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-card-foreground">NoSQL Templates</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-card-foreground">{count("nosql")}</div>
            <p className="text-xs text-muted-foreground">NoSQL query templates</p>
          </CardContent>
        </Card>
      )}

      {/* CLI Templates */}
      {count("cli") > 0 && (
        <Card className="bg-card border-border shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-card-foreground">CLI Templates</CardTitle>
          <Command className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-card-foreground">{count("cli")}</div>
          <p className="text-xs text-muted-foreground">Command-line interface templates</p>
        </CardContent>
      </Card>)}

      {/* Prompt Templates */}
      {count("prompt") > 0 && (
        <Card className="bg-card border-border shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-card-foreground">Prompt Templates</CardTitle>
          <Code className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-card-foreground">{count("prompt")}</div>
          <p className="text-xs text-muted-foreground">LLM prompt templates</p>
        </CardContent>
      </Card>)}

      {/* Reasoning Steps */}
      {count("reasoning_steps") > 0 && (
        <Card className="bg-card border-border shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-card-foreground">Reasoning Steps</CardTitle>
          <Brain className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-card-foreground">{count("reasoning_steps")}</div>
          <p className="text-xs text-muted-foreground">Reasoning process templates</p>
        </CardContent>
      </Card>)}

      {/* Recent Statistics and Usage Logs */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Recent Statistics */}
        <Card className="bg-card border-border shadow-sm">
          <CardHeader>
            <CardTitle className="text-card-foreground">Recent Statistics</CardTitle>
            <CardDescription className="text-muted-foreground">Cache entry usage over time</CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.recent_usage && stats.recent_usage.length > 0 ? (
              <div className="h-96">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.recent_usage} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#94A3B8" }} />
                    <YAxis tick={{ fontSize: 12, fill: "#94A3B8" }} />
                    <Tooltip wrapperClassName="text-sm" cursor={{ fill: "#1e293b" }} contentStyle={{ background: "#1e1e38", border: "1px solid #334155" }} />
                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No recent usage data available</p>
            )}
          </CardContent>
        </Card>

        {/* Recent Usage Logs */}
        <Card className="bg-card border-border shadow-sm">
          <CardHeader>
            <CardTitle className="text-card-foreground">Recent Usage Logs</CardTitle>
            <CardDescription className="text-muted-foreground">Latest interactions with the cache</CardDescription>
          </CardHeader>
          <CardContent>
            {logsLoading ? (
              <p className="text-muted-foreground text-sm">Loading logs...</p>
            ) : usageLogs.length === 0 ? (
              <p className="text-muted-foreground text-sm">No recent logs</p>
            ) : (
              <div className="space-y-4">
                {/* View all link at top */}
                <div className="pb-2 border-b border-border">
                  <Link to="/usage-logs" className="text-blue-400 hover:underline text-sm flex items-center gap-1">
                    View all usage logs <span className="translate-y-[1px]">→</span>
                  </Link>
                </div>

                {/* Scrollable logs container */}
                <div className="space-y-4 max-h-80 overflow-y-auto pr-2">
                  {usageLogs.map((log) => (
                    <div key={log.id} className="flex justify-between gap-4 border-b border-border pb-3 last:border-b-0">
                      {/* Left – prompt & timestamp */}
                      <div className="max-w-[75%]">
                        <Link
                          to={`/cache-entries/${log.cache_entry_id ?? ''}`}
                          className="text-blue-400 hover:underline block truncate"
                          title={log.prompt}
                          state={{ from: location.pathname }}
                        >
                          {log.prompt}
                        </Link>
                        <span className="text-xs text-muted-foreground mt-1 block">
                          {new Date(log.timestamp).toLocaleString()}
                        </span>
                      </div>

                      {/* Right – badges */}
                      <div className="flex flex-col items-end gap-1 whitespace-nowrap">
                        {/* Success / Error */}
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${log.success_status ? 'bg-green-600/20 text-green-400' : 'bg-red-600/20 text-red-400'}`}>{log.success_status ? 'Success' : 'Error'}</span>

                        {/* Similarity Score */}
                        {typeof log.similarity_score === 'number' && (
                          <span className="bg-secondary/30 text-secondary-foreground px-2 py-0.5 rounded text-xs font-medium">
                            Score: {(log.similarity_score * 100).toFixed(1)}%
                          </span>
                        )}

                        {/* LLM Enhanced */}
                        {log.llm_used && (
                          <span className="bg-indigo-700/20 text-indigo-400 px-2 py-0.5 rounded text-xs font-medium flex items-center gap-1">
                            {/* simple info icon */}
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10c0 4.418-3.582 8-8 8s-8-3.582-8-8 3.582-8 8-8 8 3.582 8 8zm-8 3a1 1 0 110-2 1 1 0 010 2zm1-6a1 1 0 00-2 0v4a1 1 0 002 0V7z" clipRule="evenodd" />
                            </svg>
                            LLM Enhanced
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Popular Cache Entries - COMMENTED OUT */}
        {/* <Card className="bg-card border-border shadow-sm">
          <CardHeader>
            <CardTitle className="text-card-foreground">Popular Cache Entries</CardTitle>
            <CardDescription className="text-muted-foreground">Most frequently used cache entries</CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.popular_entries && stats.popular_entries.length > 0 ? (
              <div className="space-y-3">
                {stats.popular_entries.slice(0, 5).map((entry) => (
                  <div key={entry.id} className="flex justify-between text-sm items-start">
                    <Link to={`/cache-entries/${entry.id}`} className="text-blue-400 hover:underline truncate mr-2" title={entry.nl_query}>
                      {entry.nl_query.length > 80 ? entry.nl_query.substring(0, 80) + "..." : entry.nl_query}
                    </Link>
                    <span className="text-muted-foreground font-medium whitespace-nowrap">{entry.usage_count} uses</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No popular entries found</p>
            )}
          </CardContent>
        </Card> */}
      </div>
    </div>
  )
} 