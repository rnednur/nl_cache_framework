"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { 
  BarChart2, 
  Database, 
  FileText, 
  Code, 
  PlusCircle,
  ArrowRight,
  Brain,
  Filter,
  Home
} from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/app/components/ui/card"
import { PageHeader } from "@/app/components/ui/PageHeader"
import { Button } from "@/app/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { Label } from "@/app/components/ui/label"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import api, { CacheStats, UsageLog, CatalogValues } from "@/app/services/api"

export default function Dashboard() {
  const [stats, setStats] = useState<CacheStats | null>(null)
  const [usageLogs, setUsageLogs] = useState<UsageLog[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [logsLoading, setLogsLoading] = useState(true)
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({
    catalog_types: [],
    catalog_subtypes: [],
    catalog_names: []
  })
  const [catalogFilters, setCatalogFilters] = useState({
    catalog_type: "",
    catalog_subtype: "",
    catalog_name: ""
  })
  const [tempFilters, setTempFilters] = useState({
    catalog_type: "",
    catalog_subtype: "",
    catalog_name: ""
  })
  const [catalogLoading, setCatalogLoading] = useState(true)
  
  useEffect(() => {
    const fetchCatalogValues = async () => {
      try {
        const data = await api.getCatalogValues()
        setCatalogValues(data)
      } catch (error) {
        console.error("Failed to fetch catalog values:", error)
      } finally {
        setCatalogLoading(false)
      }
    }
    
    fetchCatalogValues()
  }, [])
  
  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Pass catalog filters if selected
        const data = await api.getCacheStats(
          undefined, // templateType is undefined
          catalogFilters.catalog_type || undefined, 
          catalogFilters.catalog_subtype || undefined, 
          catalogFilters.catalog_name || undefined
        )
        setStats(data)
      } catch (error) {
        console.error("Failed to fetch stats:", error)
      } finally {
        setLoading(false)
      }
    }
    
    const fetchLogs = async () => {
      try {
        const data = await api.getUsageLogs(1, 5)
        console.log("Processed usage logs:", data.items)
        setUsageLogs(data.items || [])
      } catch (error) {
        console.error("Failed to fetch usage logs:", error)
        setUsageLogs([])
      } finally {
        setLogsLoading(false)
      }
    }
    
    fetchStats()
    fetchLogs()
  }, [catalogFilters])
  
  const handleTempFilterChange = (field: string, value: string) => {
    setTempFilters(prev => ({
      ...prev,
      [field]: value === "all" ? "" : value
    }))
  }
  
  const applyFilters = () => {
    setCatalogFilters(tempFilters)
    setLoading(true)
  }
  
  const clearFilters = () => {
    const emptyFilters = {
      catalog_type: "",
      catalog_subtype: "",
      catalog_name: ""
    }
    setTempFilters(emptyFilters)
    setCatalogFilters(emptyFilters)
    setLoading(true)
  }
  
  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard Overview"
        description="Monitor your cache performance and system statistics"
        icon={Home}
      />
      
      {/* Catalog Filters */}
      <Card className="workflow-card bg-card border-2 border-card-border">
        <CardHeader className="pb-3">
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-foreground">Catalog Filters</CardTitle>
              <CardDescription className="text-muted-foreground">
                Filter dashboard statistics by catalog
              </CardDescription>
            </div>
            {(catalogFilters.catalog_type !== "" || catalogFilters.catalog_subtype !== "" || catalogFilters.catalog_name !== "") && (
              <Button variant="outline" onClick={clearFilters} size="sm" className="ml-auto border-border hover:bg-input hover:text-foreground text-foreground">
                Clear Filters
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="catalog-type" className="mb-2 block text-sm font-medium text-foreground">Catalog Type</Label>
              <Select 
                value={tempFilters.catalog_type} 
                onValueChange={(value) => handleTempFilterChange("catalog_type", value)}
              >
                <SelectTrigger id="catalog-type" className="w-full bg-input border-border text-foreground">
                  <SelectValue placeholder="Select catalog type" />
                </SelectTrigger>
                <SelectContent className="bg-input border-border text-foreground">
                  <SelectItem value="all" className="text-foreground">All catalog types</SelectItem>
                  {catalogValues.catalog_types.map((type) => (
                    <SelectItem key={type} value={type} className="text-foreground">{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="catalog-subtype" className="mb-2 block text-sm font-medium text-foreground">Catalog Subtype</Label>
              <Select 
                value={tempFilters.catalog_subtype} 
                onValueChange={(value) => handleTempFilterChange("catalog_subtype", value)}
              >
                <SelectTrigger id="catalog-subtype" className="w-full bg-input border-border text-foreground">
                  <SelectValue placeholder="Select catalog subtype" />
                </SelectTrigger>
                <SelectContent className="bg-input border-border text-foreground">
                  <SelectItem value="all" className="text-foreground">All catalog subtypes</SelectItem>
                  {catalogValues.catalog_subtypes.map((subtype) => (
                    <SelectItem key={subtype} value={subtype} className="text-foreground">{subtype}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="catalog-name" className="mb-2 block text-sm font-medium text-foreground">Catalog Name</Label>
              <Select 
                value={tempFilters.catalog_name} 
                onValueChange={(value) => handleTempFilterChange("catalog_name", value)}
              >
                <SelectTrigger id="catalog-name" className="w-full bg-input border-border text-foreground">
                  <SelectValue placeholder="Select catalog name" />
                </SelectTrigger>
                <SelectContent className="bg-input border-border text-foreground">
                  <SelectItem value="all" className="text-foreground">All catalog names</SelectItem>
                  {catalogValues.catalog_names.map((name) => (
                    <SelectItem key={name} value={name} className="text-foreground">{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="mt-6 flex justify-end">
            <Button onClick={applyFilters} className="bg-primary hover:bg-primary/90 text-primary-foreground">
              Apply Filters
            </Button>
          </div>
        </CardContent>
      </Card>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">Total Cache Entries</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.total_entries || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Across all template types
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">SQL Templates</CardTitle>
            <Code className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.sql || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              SQL query templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">API Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.api || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              API call templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">URL Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.url || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              URL templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">Workflow Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.workflow || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Workflow templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">GraphQL Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.graphql || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              GraphQL query templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">Regex Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.regex || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Regular expression templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">Script Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.script || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Script templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">NoSQL Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.nosql || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              NoSQL query templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">CLI Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.cli || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Command-line interface templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">Prompt Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.prompt || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              LLM prompt templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">Reasoning Steps</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.reasoning_steps || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Reasoning process templates
            </p>
          </CardContent>
        </Card>
        
        <Card className="workflow-card bg-card border-2 border-card-border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-foreground">DSL Components</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "Loading..." : stats?.by_template_type?.dsl || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Domain Specific Language components
            </p>
          </CardContent>
        </Card>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="col-span-1 workflow-card bg-card border-2 border-card-border">
          <CardHeader>
            <CardTitle className="text-foreground">Recent Statistics</CardTitle>
            <CardDescription className="text-muted-foreground">
              Cache entry usage over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-60">
                <p className="text-foreground">Loading chart data...</p>
              </div>
            ) : stats?.recent_usage && stats.recent_usage.length > 0 ? (
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={stats.recent_usage}
                    margin={{
                      top: 10,
                      right: 10,
                      left: 0,
                      bottom: 20,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12, fill: "#94A3B8" }}
                      tickFormatter={(value) => {
                        const date = new Date(value);
                        return `${date.getMonth() + 1}/${date.getDate()}`;
                      }}
                    />
                    <YAxis tick={{ fontSize: 12, fill: "#94A3B8" }} />
                    <Tooltip
                      labelFormatter={(value) => {
                        const date = new Date(value);
                        return `Date: ${date.toLocaleDateString()}`;
                      }}
                      formatter={(value) => [`${value} uses`, 'Count']}
                      contentStyle={{ backgroundColor: '#222', borderColor: '#444' }}
                      itemStyle={{ color: '#DDD' }}
                      labelStyle={{ color: '#DDD' }}
                    />
                    <Bar dataKey="count" fill="#4f46e5" name="Usage Count" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex items-center justify-center h-60 flex-col">
                <BarChart2 className="h-40 w-40 text-muted-foreground" />
                <p className="text-muted-foreground mt-2">No usage data available yet.</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Link 
              href="/statistics" 
              className="text-sm text-blue-500 hover:text-blue-400 flex items-center"
            >
              View detailed stats
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </CardFooter>
        </Card>
        
        <Card className="col-span-1 workflow-card bg-card border-2 border-card-border">
          <CardHeader>
            <CardTitle className="text-foreground">Popular Cache Entries</CardTitle>
            <CardDescription className="text-muted-foreground">
              Most frequently used cache entries
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-60">
                <p className="text-foreground">Loading popular entries...</p>
              </div>
            ) : stats?.popular_entries && stats.popular_entries.length > 0 ? (
              <div className="space-y-4">
                {stats.popular_entries.slice(0, 5).map((entry) => (
                  <div key={entry.id} className="flex justify-between items-start mb-3">
                    <div className="max-w-[75%]">
                      <p className="text-sm font-medium break-words text-foreground">{entry.nl_query}</p>
                    </div>
                    <div className="text-sm text-muted-foreground whitespace-nowrap ml-2">
                      {entry.usage_count} uses
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-60">
                <p className="text-muted-foreground">No entries used yet</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Link 
              href="/cache-entries" 
              className="text-sm text-blue-500 hover:text-blue-400 flex items-center"
            >
              View all cache entries
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </CardFooter>
        </Card>
        
        <Card className="col-span-2 workflow-card bg-card border-2 border-card-border">
          <CardHeader>
            <CardTitle className="text-foreground">Recent Usage Logs</CardTitle>
            <CardDescription className="text-muted-foreground">
              Latest interactions with the cache
            </CardDescription>
          </CardHeader>
          <CardContent>
            {logsLoading ? (
              <div className="flex items-center justify-center h-60">
                <p className="text-foreground">Loading usage logs...</p>
              </div>
            ) : usageLogs && usageLogs.length > 0 ? (
              <div className="space-y-4 max-h-[400px] overflow-y-auto">
                {usageLogs
                  .sort((a, b) => {
                    // Sort by timestamp, most recent first
                    const dateA = new Date(a.timestamp || 0);
                    const dateB = new Date(b.timestamp || 0);
                    return dateB.getTime() - dateA.getTime();
                  })
                  .map((log, index) => {
                  // Ensure all required fields have fallback values
                  const timestamp = log.timestamp ? new Date(log.timestamp) : new Date();
                  const prompt = log.prompt || "No prompt data";
                  const success = !!log.success_status;
                  const score = log.similarity_score || 0;
                  const cacheId = log.cache_entry_id;
                  const llmUsed = !!log.llm_used;
                  
                  return (
                    <div key={log.id || index} className="flex flex-col border-b border-border pb-3 mb-2">
                      <div className="flex justify-between items-start mb-1">
                        <div className="max-w-[80%]">
                          <Link 
                            href={cacheId ? `/cache-entries/${cacheId}` : '#'} 
                            className={`text-sm font-medium break-words ${cacheId ? 'text-blue-500 hover:text-blue-400' : 'text-foreground'}`}
                          >
                            {prompt}
                          </Link>
                        </div>
                        <div className={`text-sm px-2 py-1 rounded text-white ${success ? 'bg-green-600' : 'bg-red-600'}`}>
                          {success ? 'Success' : 'Failed'}
                        </div>
                      </div>
                      <div className="flex justify-between items-center mt-1">
                        <p className="text-xs text-muted-foreground">
                          {timestamp.toLocaleString()}
                        </p>
                        <div className="flex items-center space-x-2">
                          {score > 0 && (
                            <span className="text-xs bg-input text-foreground px-2 py-1 rounded">
                              Score: {(score * 100).toFixed(1)}%
                            </span>
                          )}
                          {llmUsed && (
                            <span className="flex items-center text-xs bg-indigo-600/20 text-indigo-400 border border-indigo-600/30 px-2 py-1 rounded">
                              <Brain className="h-3 w-3 mr-1" />
                              LLM Enhanced
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-60 flex-col">
                <FileText className="h-16 w-16 text-muted-foreground mb-2" />
                <p className="text-muted-foreground">No usage logs available</p>
                <p className="text-xs text-muted-foreground mt-2">Logs appear when users interact with the cache</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Link 
              href="/usage-logs" 
              className="text-sm text-blue-500 hover:text-blue-400 flex items-center"
            >
              View all usage logs
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
} 