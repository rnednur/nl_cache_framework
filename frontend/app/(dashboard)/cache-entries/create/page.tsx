"use client"

import { useState, useEffect } from "react"
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
import React from "react"

export default function CreateCacheEntry() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Form state
  const [nlQuery, setNlQuery] = useState("")
  const [template, setTemplate] = useState("")
  const [templateType, setTemplateType] = useState("sql")
  const [reasoningTrace, setReasoningTrace] = useState("")
  const [catalogType, setCatalogType] = useState<string | undefined>(undefined)
  const [catalogSubtype, setCatalogSubtype] = useState<string | undefined>(undefined)
  const [catalogName, setCatalogName] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState('active')
  
  // Tags handling
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState("")
  
  // New state for API structured form
  const [apiMethod, setApiMethod] = useState('GET')
  const [apiEndpoint, setApiEndpoint] = useState('')
  const [apiHeaders, setApiHeaders] = useState('{"Content-Type": "application/json"}')
  const [apiBody, setApiBody] = useState('{}')
  const [useRawEditor, setUseRawEditor] = useState(false)
  const [jsonError, setJsonError] = useState<string | null>(null)
  
  const addTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()])
    }
    setTagInput('')
  }
  
  const removeTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag))
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault()
      addTag()
    }
  }
  
  // Function to generate JSON from structured form
  const generateApiJson = () => {
    try {
      const headers = JSON.parse(apiHeaders || '{}')
      const body = JSON.parse(apiBody || '{}')
      const apiJson = {
        method: apiMethod,
        url: apiEndpoint,
        headers,
        body
      }
      const jsonString = JSON.stringify(apiJson, null, 2)
      setJsonError(null)
      return jsonString
    } catch (err) {
      setJsonError('Invalid JSON in headers or body fields')
      return ''
    }
  }
  
  // Update template when using structured form
  useEffect(() => {
    if (templateType === 'api' && !useRawEditor) {
      const newTemplate = generateApiJson()
      if (newTemplate) {
        setTemplate(newTemplate)
      }
    }
  }, [apiMethod, apiEndpoint, apiHeaders, apiBody, templateType, useRawEditor])
  
  // Clear API form fields when switching away from API template type
  useEffect(() => {
    if (templateType !== 'api') {
      setApiMethod('GET')
      setApiEndpoint('')
      setApiHeaders('{"Content-Type": "application/json"}')
      setApiBody('{}')
      setUseRawEditor(false)
      setJsonError(null)
      setTemplate('')
    }
  }, [templateType])
  
  // Validate raw JSON editor input
  useEffect(() => {
    if (templateType === 'api' && template.trim()) {
      try {
        JSON.parse(template)
        setJsonError(null)
      } catch (err) {
        setJsonError(err instanceof Error ? err.message : 'Invalid JSON format')
      }
    } else {
      setJsonError(null)
    }
  }, [template, templateType])
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (templateType === 'api' && jsonError) {
      setError('Please fix the JSON errors before submitting')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const entry: CacheEntryCreate = {
        nl_query: nlQuery,
        template,
        template_type: templateType,
        reasoning_trace: reasoningTrace || undefined,
        is_template: true,
        tags: tags.length > 0 ? tags : undefined,
        catalog_type: catalogType || undefined,
        catalog_subtype: catalogSubtype || undefined,
        catalog_name: catalogName || undefined,
        status: status
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
                htmlFor="nl-query"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Natural Language Query<span className="text-red-500">*</span>
              </label>
              <Textarea
                id="nl-query"
                placeholder="e.g., Show me all users who signed up last week"
                className="min-h-[100px]"
                value={nlQuery}
                onChange={(e) => setNlQuery(e.target.value)}
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
                  <SelectItem value="graphql">GraphQL</SelectItem>
                  <SelectItem value="regex">Regex</SelectItem>
                  <SelectItem value="script">Script</SelectItem>
                  <SelectItem value="nosql">NoSQL</SelectItem>
                  <SelectItem value="cli">CLI</SelectItem>
                  <SelectItem value="prompt">Prompt</SelectItem>
                  <SelectItem value="configuration">Configuration</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="template"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Template<span className="text-red-500">*</span>
              </label>
              {templateType === 'api' ? (
                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setUseRawEditor(!useRawEditor)}
                    >
                      {useRawEditor ? 'Use Structured Form' : 'Use Raw JSON Editor'}
                    </Button>
                  </div>
                  {useRawEditor ? (
                    <div className="space-y-2">
                      <Textarea
                        id="template"
                        placeholder='e.g., {\n  "method": "GET",\n  "url": "https://api.example.com/data",\n  "headers": {\n    "Content-Type": "application/json"\n  },\n  "body": {}\n}'
                        className="min-h-[200px] font-mono text-sm"
                        value={template}
                        onChange={(e) => setTemplate(e.target.value)}
                        required
                      />
                      {jsonError && <p className="text-red-500 text-xs">{jsonError}</p>}
                    </div>
                  ) : (
                    <div className="space-y-4 border p-4 rounded-md">
                      <div className="space-y-2">
                        <label htmlFor="api-method" className="text-sm">Method</label>
                        <Select value={apiMethod} onValueChange={setApiMethod}>
                          <SelectTrigger id="api-method">
                            <SelectValue placeholder="Select method" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="GET">GET</SelectItem>
                            <SelectItem value="POST">POST</SelectItem>
                            <SelectItem value="PUT">PUT</SelectItem>
                            <SelectItem value="DELETE">DELETE</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <label htmlFor="api-endpoint" className="text-sm">Endpoint URL</label>
                        <Input
                          id="api-endpoint"
                          placeholder="https://api.example.com/resource"
                          value={apiEndpoint}
                          onChange={(e) => setApiEndpoint(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <label htmlFor="api-headers" className="text-sm">Headers (JSON)</label>
                        <Textarea
                          id="api-headers"
                          placeholder='{"Content-Type": "application/json"}'
                          className="min-h-[100px] font-mono text-sm"
                          value={apiHeaders}
                          onChange={(e) => setApiHeaders(e.target.value)}
                        />
                        {jsonError && jsonError.includes('headers') && <p className="text-red-500 text-xs">Invalid JSON in headers</p>}
                      </div>
                      <div className="space-y-2">
                        <label htmlFor="api-body" className="text-sm">Body (JSON)</label>
                        <Textarea
                          id="api-body"
                          placeholder="{}"
                          className="min-h-[100px] font-mono text-sm"
                          value={apiBody}
                          onChange={(e) => setApiBody(e.target.value)}
                        />
                        {jsonError && jsonError.includes('body') && <p className="text-red-500 text-xs">Invalid JSON in body</p>}
                      </div>
                    </div>
                  )}
                </div>
              ) : templateType === 'sql' ? (
                <Textarea
                  id="template"
                  placeholder="e.g., SELECT * FROM users WHERE signup_date >= '{{start_date}}' AND signup_date <= '{{end_date}}'"
                  className="min-h-[100px] font-mono text-sm"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              ) : templateType === 'url' ? (
                <Input
                  id="template"
                  placeholder="e.g., https://example.com/data?param={{value}}"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              ) : templateType === 'workflow' ? (
                <div className="space-y-2">
                  <Textarea
                    id="template"
                    placeholder='e.g., {
  "steps": [
    {
      "type": "api",
      "url": "https://api.example.com/step1"
    },
    {
      "type": "transform",
      "operation": "filter"
    }
  ]
}'
                    className="min-h-[200px] font-mono text-sm"
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    required
                  />
                  {templateType === 'workflow' && template.trim() && (() => {
                    try {
                      JSON.parse(template);
                      return null;
                    } catch (err) {
                      return <p className="text-red-500 text-xs">Invalid JSON format</p>;
                    }
                  })()}
                </div>
              ) : templateType === 'graphql' ? (
                <Textarea
                  id="template"
                  placeholder="e.g., query { user(id: {{user_id}}) { name, email } }"
                  className="min-h-[100px] font-mono text-sm"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              ) : templateType === 'regex' ? (
                <Input
                  id="template"
                  placeholder="e.g., \d{4}-\d{2}-\d{2}"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              ) : templateType === 'script' ? (
                <div className="space-y-2">
                  <Textarea
                    id="template"
                    placeholder='e.g., {
  "language": "javascript",
  "code": "function transform(data) { return data.filter(d => d.active); }"
}'
                    className="min-h-[200px] font-mono text-sm"
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    required
                  />
                  {templateType === 'script' && template.trim() && (() => {
                    try {
                      JSON.parse(template);
                      return null;
                    } catch (err) {
                      return <p className="text-red-500 text-xs">Invalid JSON format</p>;
                    }
                  })()}
                </div>
              ) : templateType === 'nosql' ? (
                <Textarea
                  id="template"
                  placeholder='e.g., {
  "collection": "users",
  "query": { "status": "active" },
  "projection": { "name": 1, "email": 1 }
}'
                  className="min-h-[100px] font-mono text-sm"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              ) : templateType === 'cli' ? (
                <Input
                  id="template"
                  placeholder="e.g., grep '{{search_term}}' /var/log/*.log"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              ) : templateType === 'prompt' ? (
                <Textarea
                  id="template"
                  placeholder="e.g., Translate the following text to {{language}}: '{{text}}'"
                  className="min-h-[100px] font-mono text-sm"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              ) : templateType === 'configuration' ? (
                <div className="space-y-2">
                  <Textarea
                    id="template"
                    placeholder='e.g., {
  "settings": {
    "timeout": 30,
    "retries": 3
  },
  "parameters": {
    "key": "{{api_key}}"
  }
}'
                    className="min-h-[200px] font-mono text-sm"
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    required
                  />
                  {templateType === 'configuration' && template.trim() && (() => {
                    try {
                      JSON.parse(template);
                      return null;
                    } catch (err) {
                      return <p className="text-red-500 text-xs">Invalid JSON format</p>;
                    }
                  })()}
                </div>
              ) : (
                <Textarea
                  id="template"
                  placeholder="Enter template content"
                  className="min-h-[100px] font-mono text-sm"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  required
                />
              )}
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
                <Label htmlFor="catalogType">Catalog Type</Label>
                <Input
                  id="catalogType"
                  placeholder="Enter catalog type"
                  value={catalogType || ''}
                  onChange={(e) => setCatalogType(e.target.value || undefined)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="catalogSubtype">Catalog Subtype</Label>
                <Input
                  id="catalogSubtype"
                  placeholder="Enter catalog subtype"
                  value={catalogSubtype || ''}
                  onChange={(e) => setCatalogSubtype(e.target.value || undefined)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="catalogName">Catalog Name</Label>
                <Input
                  id="catalogName"
                  placeholder="Enter catalog name"
                  value={catalogName || ''}
                  onChange={(e) => setCatalogName(e.target.value || undefined)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="status"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Status
              </label>
              <Select 
                value={status}
                onValueChange={setStatus}
              >
                <SelectTrigger id="status">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
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