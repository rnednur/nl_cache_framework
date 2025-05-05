"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Tag as TagIcon } from "lucide-react"
import { Button } from "../../../../components/ui/button"
import { Input } from "../../../../components/ui/input"
import { Textarea } from "../../../../components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../../components/ui/select"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../../../components/ui/card"
import api, { CacheEntryCreate, CacheItem } from "../../../../services/api"
import { Label } from "../../../../components/ui/label"
import { CacheEntryForm } from "../CacheEntryForm"

export default function EditCacheEntry({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
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
  
  useEffect(() => {
    const fetchEntry = async () => {
      try {
        const entry = await api.getCacheEntry(parseInt(params.id))
        setNlQuery(entry.nl_query)
        setTemplate(entry.template)
        setTemplateType(entry.template_type)
        setReasoningTrace(entry.reasoning_trace || "")
        setCatalogType(entry.catalog_type || undefined)
        setCatalogSubtype(entry.catalog_subtype || undefined)
        setCatalogName(entry.catalog_name || undefined)
        setStatus(entry.status || 'active')
        setTags(entry.tags || [])
      } catch (err) {
        console.error("Failed to fetch cache entry:", err)
        setError(err instanceof Error ? err.message : "Failed to fetch cache entry")
      } finally {
        setLoading(false)
      }
    }
    
    fetchEntry()
  }, [params.id])
  
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
    
    // Debug log
    console.log("Submitting with nlQuery:", nlQuery)

    if (!nlQuery.trim() || !template.trim()) {
      setError("Natural Language Query and Template are required.")
      return
    }
    
    setSaving(true)
    setError(null)
    
    try {
      const entry: Partial<CacheEntryCreate> = {
        nl_query: nlQuery,
        template: template,
        template_type: templateType,
        is_template: true,
        tags: tags.length > 0 ? tags : undefined,
        reasoning_trace: reasoningTrace || undefined,
        catalog_type: catalogType || undefined,
        catalog_subtype: catalogSubtype || undefined,
        catalog_name: catalogName || undefined,
        status: status
      }
      
      // Debug log
      console.log("PUT body:", entry)

      await api.updateCacheEntry(parseInt(params.id), entry)
      // Force a hard refresh of the cache entries list
      router.refresh()
      router.push("/cache-entries")
    } catch (err) {
      console.error("Failed to update cache entry:", err)
      setError(err instanceof Error ? err.message : "Failed to update cache entry")
    } finally {
      setSaving(false)
    }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading cache entry...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Edit Cache Entry</h1>
      </div>
      
      <Card>
        <form onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle>Edit Cache Entry</CardTitle>
            <CardDescription>Modify the cache entry details below.</CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-md border border-red-200 text-sm">
                {error}
              </div>
            )}
            
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
              tagInput={tagInput}
              setTagInput={setTagInput}
              handleKeyDown={handleKeyDown}
              error={error}
              readOnly={false}
            >
              <CardFooter className="flex justify-end space-x-2 border-t pt-6">
                <Button 
                  type="button"
                  variant="outline" 
                  onClick={() => router.push("/cache-entries")}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
              </CardFooter>
            </CacheEntryForm>
          </CardContent>
        </form>
      </Card>
    </div>
  )
} 