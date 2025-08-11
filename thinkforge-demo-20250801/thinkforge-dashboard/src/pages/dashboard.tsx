import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BarChart } from "../components/bar-chart"
import { PopularEntries } from "../components/popular-entries"
import { StatCard } from "../components/stats-card"
import {
  Database,
  Code2,
  FileText,
  Globe,
  GitBranch,
  Terminal,
  Regex,
  FileCode2,
  Server,
  CommandIcon as CommandLine,
  MessageSquare,
  BrainCircuit,
} from "lucide-react"

export function Dashboard() {
  return (
    <>
      <div className="flex flex-col md:flex-row gap-4 md:items-center md:justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white">Welcome back</h2>
          <p className="text-slate-400">Here's an overview of your cache system</p>
        </div>
        <Tabs defaultValue="day" className="w-full md:w-auto">
          <TabsList className="bg-[#2a2a4a]">
            <TabsTrigger value="day" className="data-[state=active]:bg-blue-600 text-white">
              Day
            </TabsTrigger>
            <TabsTrigger value="week" className="data-[state=active]:bg-blue-600 text-white">
              Week
            </TabsTrigger>
            <TabsTrigger value="month" className="data-[state=active]:bg-blue-600 text-white">
              Month
            </TabsTrigger>
            <TabsTrigger value="year" className="data-[state=active]:bg-blue-600 text-white">
              Year
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <Card className="bg-[#1e1e38] border-[#2a2a4a] text-white">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Catalog Filters</CardTitle>
          <p className="text-sm text-slate-400">Filter dashboard statistics by catalog</p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Catalog Type</label>
              <Select>
                <SelectTrigger className="bg-[#2a2a4a] border-[#3a3a5e] text-white">
                  <SelectValue placeholder="Select catalog type" />
                </SelectTrigger>
                <SelectContent className="bg-[#2a2a4a] border-[#3a3a5e] text-white">
                  <SelectItem value="sql">SQL</SelectItem>
                  <SelectItem value="api">API</SelectItem>
                  <SelectItem value="url">URL</SelectItem>
                  <SelectItem value="workflow">Workflow</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Catalog Subtype</label>
              <Select>
                <SelectTrigger className="bg-[#2a2a4a] border-[#3a3a5e] text-white">
                  <SelectValue placeholder="Select catalog subtype" />
                </SelectTrigger>
                <SelectContent className="bg-[#2a2a4a] border-[#3a3a5e] text-white">
                  <SelectItem value="query">Query</SelectItem>
                  <SelectItem value="call">Call</SelectItem>
                  <SelectItem value="template">Template</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Catalog Name</label>
              <Select>
                <SelectTrigger className="bg-[#2a2a4a] border-[#3a3a5e] text-white">
                  <SelectValue placeholder="Select catalog name" />
                </SelectTrigger>
                <SelectContent className="bg-[#2a2a4a] border-[#3a3a5e] text-white">
                  <SelectItem value="main">Main</SelectItem>
                  <SelectItem value="secondary">Secondary</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button variant="default" size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
              Apply Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Cache Entries"
          value="8,031"
          description="Across all template types"
          icon={<Database className="h-4 w-4 text-blue-500" />}
          trend={{ value: 12, label: "from last month", positive: true }}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="SQL Templates"
          value="8,031"
          description="SQL query templates"
          icon={<Code2 className="h-4 w-4 text-blue-500" />}
          trend={{ value: 12, label: "from last month", positive: true }}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="API Templates"
          value="0"
          description="API call templates"
          icon={<FileText className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="URL Templates"
          value="0"
          description="URL templates"
          icon={<Globe className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Workflow Templates"
          value="0"
          description="Workflow templates"
          icon={<GitBranch className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="GraphQL Templates"
          value="0"
          description="GraphQL query templates"
          icon={<Terminal className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="Regex Templates"
          value="0"
          description="Regular expression templates"
          icon={<Regex className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="Script Templates"
          value="0"
          description="Script templates"
          icon={<FileCode2 className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="NoSQL Templates"
          value="0"
          description="NoSQL query templates"
          icon={<Server className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="CLI Templates"
          value="0"
          description="Command-line interface templates"
          icon={<CommandLine className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="Prompt Templates"
          value="0"
          description="LLM prompt templates"
          icon={<MessageSquare className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
        <StatCard
          title="Reasoning Steps"
          value="0"
          description="Reasoning process templates"
          icon={<BrainCircuit className="h-4 w-4 text-blue-500" />}
          className="bg-[#1e1e38] border-[#2a2a4a] text-white"
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="bg-[#1e1e38] border-[#2a2a4a] text-white">
          <CardHeader>
            <CardTitle className="text-base">Recent Statistics</CardTitle>
            <p className="text-sm text-slate-400">Cache entry usage over time</p>
          </CardHeader>
          <CardContent>
            <BarChart darkMode={true} />
          </CardContent>
          <div className="px-6 pb-4">
            <Button variant="link" size="sm" className="h-auto p-0 text-sm text-blue-500 hover:text-blue-400">
              View detailed stats →
            </Button>
          </div>
        </Card>
        <Card className="bg-[#1e1e38] border-[#2a2a4a] text-white">
          <CardHeader>
            <CardTitle className="text-base">Popular Cache Entries</CardTitle>
            <p className="text-sm text-slate-400">Most frequently used cache entries</p>
          </CardHeader>
          <CardContent>
            <PopularEntries darkMode={true} />
          </CardContent>
          <div className="px-6 pb-4">
            <Button variant="link" size="sm" className="h-auto p-0 text-sm text-blue-500 hover:text-blue-400">
              View all cache entries →
            </Button>
          </div>
        </Card>
      </div>
    </>
  )
}
