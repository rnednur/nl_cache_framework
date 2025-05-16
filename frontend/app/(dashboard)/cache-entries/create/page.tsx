"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "../../../components/ui/button"
import { Card, CardContent } from "../../../components/ui/card"
import api, { CacheEntryCreate } from "../../../services/api"
import { CacheEntryForm } from "../[id]/CacheEntryForm"

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
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!nlQuery.trim() || !template.trim()) {
      setError("Natural Language Query and Template are required.")
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      // Prepare the catalog fields, ensuring they're either valid strings or undefined
      const catalogTypeValue = catalogType?.trim() || undefined
      const catalogSubtypeValue = catalogSubtype?.trim() || undefined
      const catalogNameValue = catalogName?.trim() || undefined
      
      const entry: CacheEntryCreate = {
        nl_query: nlQuery,
        template,
        template_type: templateType,
        reasoning_trace: reasoningTrace || undefined,
        is_template: true,
        tags: tags.length > 0 ? tags : undefined,
        catalog_type: catalogTypeValue,
        catalog_subtype: catalogSubtypeValue,
        catalog_name: catalogNameValue,
        status: status
      }
      
      // Debug log
      console.log("Create entry:", entry)
      
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
      
      <Card className="shadow-sm">
        <form onSubmit={handleSubmit}>
          <CardContent className="p-6 space-y-8">
            {error && (
              <div className="bg-red-50 text-red-600 p-4 rounded-md border border-red-200 text-sm mb-4">
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
              <div className="flex justify-end space-x-4 border-t pt-6 mt-6">
                <Button 
                  type="button"
                  variant="outline" 
                  onClick={() => router.push("/cache-entries")}
                  className="px-6"
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={loading} className="px-6">
                  {loading ? "Creating..." : "Create Cache Entry"}
                </Button>
              </div>
            </CacheEntryForm>
          </CardContent>
        </form>
      </Card>
    </div>
  )
} 