"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Tag as TagIcon } from "lucide-react"
import { Button } from "../../../components/ui/button"
import { Input } from "../../../components/ui/input"
import { Textarea } from "../../../components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../../components/ui/card"
import api, { CacheEntryCreate } from "../../../services/api"
import { Label } from "../../../components/ui/label"

export default function CreateCacheEntry() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Form state
  const [nlQuery, setNlQuery] = useState("")
  const [template, setTemplate] = useState("")
  const [templateType, setTemplateType] = useState("sql")
  const [visualization, setVisualization] = useState("")
  const [reasoningTrace, setReasoningTrace] = useState("")
  const [databaseName, setDatabaseName] = useState("")
  const [schemaName, setSchemaName] = useState("")
  const [catalogId, setCatalogId] = useState<number | undefined>()
  
  // Tags handling
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState("")
  
  const addTag = () => {
    if (tagInput.trim() !== "" && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()])
      setTagInput("")
    }
  }
  
  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter((tag) => tag !== tagToRemove))
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      addTag()
    }
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!nlQuery.trim() || !template.trim()) {
      setError("Natural Language Query and Template are required.")
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const entry: CacheEntryCreate = {
        nl_query: nlQuery,
        template: template,
        template_type: templateType,
        is_template: true,
        tags: tags.length > 0 ? tags : undefined,
        suggested_visualization: visualization || undefined,
        reasoning_trace: reasoningTrace || undefined,
        database_name: databaseName || undefined,
        schema_name: schemaName || undefined,
        catalog_id: catalogId
      }
      
      await api.createCacheEntry(entry)
      router.push("/cache-entries")
    } catch (err) {
      console.error("Failed to create cache entry:", err)
      setError(err instanceof Error ? err.message : "Failed to create cache entry")
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Create Cache Entry</h1>
      </div>
      
      <Card>
        <form onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle>Create New Cache Entry</CardTitle>
            <CardDescription>Define a new cache entry with natural language query and template.</CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-md border border-red-200 text-sm">
                {error}
              </div>
            )}
            
            <div className="space-y-2">
              <label
                htmlFor="query"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Natural Language Query<span className="text-red-500">*</span>
              </label>
              <Textarea
                id="query"
                placeholder="e.g., Get all users who signed up last month"
                className="min-h-[100px]"
                value={nlQuery}
                onChange={(e) => setNlQuery(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="template"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Template<span className="text-red-500">*</span>
              </label>
              <Textarea
                id="template"
                placeholder="e.g., SELECT * FROM users WHERE signup_date >= '{{start_date}}' AND signup_date <= '{{end_date}}'"
                className="min-h-[100px] font-mono text-sm"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="template-type"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Template Type
              </label>
              <Select 
                value={templateType}
                onValueChange={setTemplateType}
              >
                <SelectTrigger id="template-type">
                  <SelectValue placeholder="Select template type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sql">SQL</SelectItem>
                  <SelectItem value="api">API</SelectItem>
                  <SelectItem value="url">URL</SelectItem>
                  <SelectItem value="workflow">Workflow</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="visualization"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Suggested Visualization
              </label>
              <Select 
                value={visualization}
                onValueChange={setVisualization}
              >
                <SelectTrigger id="visualization">
                  <SelectValue placeholder="Select visualization type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="table">Table</SelectItem>
                  <SelectItem value="bar">Bar Chart</SelectItem>
                  <SelectItem value="line">Line Chart</SelectItem>
                  <SelectItem value="pie">Pie Chart</SelectItem>
                  <SelectItem value="scatter">Scatter Plot</SelectItem>
                  <SelectItem value="map">Map</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                Tags
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {tags.map((tag) => (
                  <div
                    key={tag}
                    className="flex items-center bg-slate-100 text-slate-800 px-3 py-1 rounded-full text-sm"
                  >
                    <span>{tag}</span>
                    <button 
                      type="button"
                      onClick={() => removeTag(tag)} 
                      className="ml-2 text-slate-500 hover:text-slate-700"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex">
                <Input
                  placeholder="Add tag..."
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="rounded-r-none"
                />
                <Button 
                  type="button"
                  onClick={addTag} 
                  variant="secondary" 
                  className="rounded-l-none"
                >
                  <TagIcon className="h-4 w-4 mr-1" />
                  Add
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="reasoning"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Reasoning Trace
              </label>
              <Textarea
                id="reasoning"
                placeholder="Explain how this template relates to the query..."
                className="min-h-[100px]"
                value={reasoningTrace}
                onChange={(e) => setReasoningTrace(e.target.value)}
              />
            </div>

            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="database">Database Name</Label>
                <Input
                  id="database"
                  placeholder="Enter database name"
                  value={databaseName}
                  onChange={(e) => setDatabaseName(e.target.value)}
                />
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="schema">Schema Name</Label>
                <Input
                  id="schema"
                  placeholder="Enter schema name"
                  value={schemaName}
                  onChange={(e) => setSchemaName(e.target.value)}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="catalog">Catalog ID</Label>
                <Input
                  id="catalog"
                  type="number"
                  placeholder="Enter catalog ID"
                  value={catalogId || ""}
                  onChange={(e) => setCatalogId(e.target.value ? parseInt(e.target.value) : undefined)}
                />
              </div>
            </div>
          </CardContent>
          
          <CardFooter className="flex justify-end space-x-2 border-t pt-6">
            <Button 
              type="button"
              variant="outline" 
              onClick={() => router.push("/cache-entries")}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create Entry"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
} 