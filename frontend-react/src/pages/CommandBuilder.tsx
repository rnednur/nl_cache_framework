import { useState } from "react"
import { Save, Play, Code, Wand2, Settings } from "lucide-react"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Textarea } from "../components/ui/textarea"
import { Card } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import { Switch } from "../components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs"

export default function CommandBuilder() {
  const [commandName, setCommandName] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [description, setDescription] = useState("")
  const [queryText, setQueryText] = useState("")
  const [queryType, setQueryType] = useState("nl2sql")
  const [domain, setDomain] = useState("")
  const [category, setCategory] = useState("")
  const [tags, setTags] = useState<string[]>([])
  const [isPublic, setIsPublic] = useState(false)
  const [activeTab, setActiveTab] = useState("basic")

  const handleSave = () => {
    // Implementation would save the command
    console.log("Saving command:", {
      commandName,
      displayName,
      description,
      queryText,
      queryType,
      domain,
      category,
      tags,
      isPublic
    })
  }

  const handleTest = () => {
    // Implementation would test the command
    console.log("Testing command:", queryText)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Command Builder</h1>
          <p className="text-slate-400 mt-1">Create and customize your hot commands</p>
        </div>
        <div className="flex space-x-3">
          <Button 
            variant="outline" 
            onClick={handleTest}
            className="border-[#3a3a5e] text-slate-400 hover:text-white hover:bg-[#3a3a5e]"
          >
            <Play className="h-4 w-4 mr-2" />
            Test
          </Button>
          <Button onClick={handleSave} className="bg-blue-600 hover:bg-blue-700">
            <Save className="h-4 w-4 mr-2" />
            Save Command
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2">
          <Card className="bg-[#252547] border-[#3a3a5e] p-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3 bg-[#1e1e38] border border-[#3a3a5e]">
                <TabsTrigger 
                  value="basic"
                  className="data-[state=active]:bg-[#3a3a5e] data-[state=active]:text-white"
                >
                  Basic Info
                </TabsTrigger>
                <TabsTrigger 
                  value="query"
                  className="data-[state=active]:bg-[#3a3a5e] data-[state=active]:text-white"
                >
                  Query
                </TabsTrigger>
                <TabsTrigger 
                  value="advanced"
                  className="data-[state=active]:bg-[#3a3a5e] data-[state=active]:text-white"
                >
                  Advanced
                </TabsTrigger>
              </TabsList>

              <TabsContent value="basic" className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Command Name *
                  </label>
                  <Input
                    placeholder="e.g., sales_summary"
                    value={commandName}
                    onChange={(e) => setCommandName(e.target.value)}
                    className="bg-[#1e1e38] border-[#3a3a5e] text-white placeholder-slate-400"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Used as /{commandName}. Only letters, numbers, and underscores.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Display Name
                  </label>
                  <Input
                    placeholder="e.g., Sales Summary Report"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="bg-[#1e1e38] border-[#3a3a5e] text-white placeholder-slate-400"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Description
                  </label>
                  <Textarea
                    placeholder="Describe what this command does..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="bg-[#1e1e38] border-[#3a3a5e] text-white placeholder-slate-400 min-h-[100px]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Domain
                    </label>
                    <Select value={domain} onValueChange={setDomain}>
                      <SelectTrigger className="bg-[#1e1e38] border-[#3a3a5e] text-white">
                        <SelectValue placeholder="Select domain" />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                        <SelectItem value="RAN">RAN</SelectItem>
                        <SelectItem value="CustomerExperience">Customer Experience</SelectItem>
                        <SelectItem value="Finance">Finance</SelectItem>
                        <SelectItem value="Operations">Operations</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Category
                    </label>
                    <Select value={category} onValueChange={setCategory}>
                      <SelectTrigger className="bg-[#1e1e38] border-[#3a3a5e] text-white">
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                        <SelectItem value="Capacity">Capacity</SelectItem>
                        <SelectItem value="RF">RF</SelectItem>
                        <SelectItem value="Analytics">Analytics</SelectItem>
                        <SelectItem value="Reports">Reports</SelectItem>
                        <SelectItem value="Monitoring">Monitoring</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="query" className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Query Type
                  </label>
                  <Select value={queryType} onValueChange={setQueryType}>
                    <SelectTrigger className="bg-[#1e1e38] border-[#3a3a5e] text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1e1e38] border-[#3a3a5e]">
                      <SelectItem value="nl2sql">Natural Language to SQL</SelectItem>
                      <SelectItem value="direct_sql">Direct SQL Query</SelectItem>
                      <SelectItem value="tool_call">Tool/API Call</SelectItem>
                      <SelectItem value="workflow">Workflow</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Query Text *
                  </label>
                  <Textarea
                    placeholder={
                      queryType === "nl2sql" 
                        ? "e.g., Show me the top 10 products by sales this month"
                        : queryType === "direct_sql"
                        ? "e.g., SELECT * FROM products ORDER BY sales DESC LIMIT 10"
                        : "Enter your query or workflow definition..."
                    }
                    value={queryText}
                    onChange={(e) => setQueryText(e.target.value)}
                    className="bg-[#1e1e38] border-[#3a3a5e] text-white placeholder-slate-400 min-h-[150px] font-mono text-sm"
                  />
                </div>

                {queryType === "nl2sql" && (
                  <div className="bg-blue-600/10 border border-blue-600/20 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <Wand2 className="h-4 w-4 text-blue-400" />
                      <span className="text-sm font-medium text-blue-400">AI Assistant</span>
                    </div>
                    <p className="text-sm text-slate-300">
                      Your natural language query will be processed by ThinkForge's semantic engine 
                      and automatically converted to optimized SQL.
                    </p>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="advanced" className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Tags
                  </label>
                  <Input
                    placeholder="sales, monthly, report (comma separated)"
                    value={tags.join(", ")}
                    onChange={(e) => setTags(e.target.value.split(",").map(t => t.trim()).filter(Boolean))}
                    className="bg-[#1e1e38] border-[#3a3a5e] text-white placeholder-slate-400"
                  />
                  {tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {tags.map((tag, index) => (
                        <Badge key={index} className="bg-slate-700/50 text-slate-300 text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-slate-300">Make Public</label>
                    <p className="text-xs text-slate-400">Allow other users to discover and use this command</p>
                  </div>
                  <Switch checked={isPublic} onCheckedChange={setIsPublic} />
                </div>

                <div className="bg-yellow-600/10 border border-yellow-600/20 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <Settings className="h-4 w-4 text-yellow-400" />
                    <span className="text-sm font-medium text-yellow-400">Parameters & Templates</span>
                  </div>
                  <p className="text-sm text-slate-300 mb-2">
                    Parameter support is coming soon. You'll be able to define dynamic parameters 
                    like [date], [limit], [user_id] that users can customize when running commands.
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        {/* Preview */}
        <div>
          <Card className="bg-[#252547] border-[#3a3a5e] p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Preview</h3>
            
            {commandName && (
              <div className="space-y-4">
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <Code className="h-4 w-4 text-blue-400" />
                    <span className="text-sm font-medium text-slate-300">Command</span>
                  </div>
                  <div className="bg-[#1e1e38] border border-[#3a3a5e] rounded p-3">
                    <code className="text-blue-400 font-mono">/{commandName}</code>
                  </div>
                </div>

                <div>
                  <span className="text-sm font-medium text-slate-300">Display Name</span>
                  <p className="text-white mt-1">{displayName || commandName.replace('_', ' ')}</p>
                </div>

                {description && (
                  <div>
                    <span className="text-sm font-medium text-slate-300">Description</span>
                    <p className="text-slate-300 text-sm mt-1">{description}</p>
                  </div>
                )}

                {(domain || category) && (
                  <div>
                    <span className="text-sm font-medium text-slate-300">Category</span>
                    <div className="mt-1">
                      <Badge variant="outline" className="text-xs text-slate-300 border-slate-600">
                        {domain}{category && `/${category}`}
                      </Badge>
                    </div>
                  </div>
                )}

                {tags.length > 0 && (
                  <div>
                    <span className="text-sm font-medium text-slate-300">Tags</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {tags.map((tag, index) => (
                        <Badge key={index} className="bg-slate-700/50 text-slate-300 text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center space-x-4 text-xs text-slate-400">
                  <span>0 uses</span>
                  {isPublic && <Badge className="bg-green-600/20 text-green-400 text-xs">Public</Badge>}
                </div>
              </div>
            )}

            {!commandName && (
              <p className="text-slate-400 text-sm">
                Enter a command name to see the preview
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}