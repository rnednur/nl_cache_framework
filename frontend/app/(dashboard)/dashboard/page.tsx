"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { 
  BarChart2, 
  Database, 
  FileText, 
  Code, 
  PlusCircle,
  ArrowRight
} from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import api, { CacheStats } from "../../services/api"

export default function Dashboard() {
  const [stats, setStats] = useState<CacheStats | null>(null)
  const [usageLogs, setUsageLogs] = useState<any[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [logsLoading, setLogsLoading] = useState(true)
  
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getCacheStats()
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
        setUsageLogs(data.items)
      } catch (error) {
        console.error("Failed to fetch usage logs:", error)
      } finally {
        setLogsLoading(false)
      }
    }
    
    fetchStats()
    fetchLogs()
  }, [])
  
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <Button asChild>
          <Link href="/cache-entries/create">
            <PlusCircle className="mr-2 h-4 w-4" />
            Create Cache Entry
          </Link>
        </Button>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cache Entries</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.total_entries || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Across all template types
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SQL Templates</CardTitle>
            <Code className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.sql || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              SQL query templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.api || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              API call templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">URL Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.url || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              URL templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Workflow Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.workflow || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Workflow templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">GraphQL Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.graphql || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              GraphQL query templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Regex Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.regex || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Regular expression templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Script Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.script || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Script templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">NoSQL Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.nosql || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              NoSQL query templates
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CLI Templates</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "Loading..." : stats?.by_template_type?.cli || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Command-line interface templates
            </p>
          </CardContent>
        </Card>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Recent Statistics</CardTitle>
            <CardDescription>
              Cache entry usage over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-60">
                <p>Loading chart data...</p>
              </div>
            ) : (
              <div className="flex items-center justify-center h-60 flex-col">
                <BarChart2 className="h-40 w-40 text-muted-foreground" />
                <p className="text-muted-foreground mt-2">Usage chart visualization is under development. Check back soon!</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Link 
              href="/statistics" 
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
            >
              View detailed stats
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </CardFooter>
        </Card>
        
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Popular Cache Entries</CardTitle>
            <CardDescription>
              Most frequently used cache entries
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-60">
                <p>Loading popular entries...</p>
              </div>
            ) : stats?.popular_entries && stats.popular_entries.length > 0 ? (
              <div className="space-y-4">
                {stats.popular_entries.slice(0, 5).map((entry) => (
                  <div key={entry.id} className="flex justify-between items-center">
                    <div className="truncate max-w-[300px]">
                      <p className="text-sm font-medium">{entry.nl_query}</p>
                    </div>
                    <div className="text-sm text-muted-foreground">
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
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
            >
              View all cache entries
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </CardFooter>
        </Card>
        
        <Card className="col-span-2">
          <CardHeader>
            <CardTitle>Recent Usage Logs</CardTitle>
            <CardDescription>
              Latest interactions with the cache
            </CardDescription>
          </CardHeader>
          <CardContent>
            {logsLoading ? (
              <div className="flex items-center justify-center h-60">
                <p>Loading usage logs...</p>
              </div>
            ) : usageLogs && usageLogs.length > 0 ? (
              <div className="space-y-4">
                {usageLogs.slice(0, 5).map((log, index) => (
                  <div key={index} className="flex justify-between items-center border-b pb-2">
                    <div className="truncate max-w-[400px]">
                      <p className="text-sm font-medium">{log.prompt}</p>
                      <p className="text-xs text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</p>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Status: {log.success_status ? 'Success' : 'Failed'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-60">
                <p className="text-muted-foreground">No usage logs available</p>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Link 
              href="/usage-logs" 
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
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