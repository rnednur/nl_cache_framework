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
import { toast } from "react-hot-toast"

export default function EditCacheEntry({ params }: { params: { id: string } }) {
  const router = useRouter()
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
  const [status, setStatus] = useState('active')
  
  // Tags handling
  const [tags, setTags] = useState<Record<string, string[]>>({})
  const [tagNameInput, setTagNameInput] = useState("")
  const [tagValueInput, setTagValueInput] = useState("")
  
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
        
        // Handle tags - convert from old format if necessary
        if (entry.tags) {
          if (Array.isArray(entry.tags)) {
            // Convert old string[] format to Record<string, string[]>
            const convertedTags: Record<string, string[]> = {};
            entry.tags.forEach(tag => {
              convertedTags[tag] = ['default'];
            });
            setTags(convertedTags);
          } else {
            // Already in the new format
            setTags(entry.tags);
          }
        } else {
          setTags({});
        }
      } catch (err) {
        console.error("Failed to fetch cache entry:", err)
        setError(err instanceof Error ? err.message : "Failed to fetch cache entry")
      } finally {
        setLoading(false)
      }
    }
    
    fetchEntry()
  }, [params.id])
  
  const handleGenerateReasoning = async () => {
    if (!nlQuery.trim() || !template.trim()) {
      toast.error("Both Natural Language Query and Template are required to generate reasoning.");
      return;
    }
    
    setIsGeneratingReasoning(true);
    try {
      const generatedReasoning = await api.generateReasoningTrace(
        nlQuery, 
        template,
        templateType
      );
      setReasoningTrace(generatedReasoning);
      toast.success("AI has generated a reasoning trace for your query and template.");
    } catch (err) {
      console.error("Failed to generate reasoning:", err);
      toast.error(err instanceof Error ? err.message : "An error occurred while generating reasoning.");
    } finally {
      setIsGeneratingReasoning(false);
    }
  };
  
  const addTag = (name: string, value: string) => {
    if (name.trim() === "") return;
    
    const newTags = { ...tags };
    
    // If the tag name doesn't exist yet, create a new array
    if (!newTags[name]) {
      newTags[name] = [];
    }
    
    // Only add the value if it's not empty and not already in the array
    if (value.trim() !== "" && !newTags[name].includes(value)) {
      newTags[name] = [...newTags[name], value];
    }
    
    setTags(newTags);
    setTagNameInput("");
    setTagValueInput("");
  }
  
  const removeTag = (name: string, value: string) => {
    const newTags = { ...tags };
    
    if (newTags[name]) {
      // Filter out the value from the array
      newTags[name] = newTags[name].filter(v => v !== value);
      
      // If the array is now empty, remove the tag entirely
      if (newTags[name].length === 0) {
        delete newTags[name];
      }
      
      setTags(newTags);
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      addTag(tagNameInput, tagValueInput)
    }
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Debug log
    console.log("Submitting with nlQuery:", nlQuery)
    console.log("Catalog values:", { 
      catalogType, 
      catalogSubtype, 
      catalogName, 
      type: typeof catalogType, 
      isUndefined: catalogType === undefined 
    })

    if (!nlQuery.trim() || !template.trim()) {
      setError("Natural Language Query and Template are required.")
      return
    }
    
    setSaving(true)
    setError(null)
    
    try {
      // Prepare the catalog fields, ensuring they're either valid strings or undefined
      const catalogTypeValue = catalogType?.trim() || undefined
      const catalogSubtypeValue = catalogSubtype?.trim() || undefined
      const catalogNameValue = catalogName?.trim() || undefined
      
      const entry: Partial<CacheEntryCreate> = {
        nl_query: nlQuery,
        template: template,
        template_type: templateType,
        is_template: true,
        tags: Object.keys(tags).length > 0 ? tags : undefined,
        reasoning_trace: reasoningTrace || undefined,
        catalog_type: catalogTypeValue,
        catalog_subtype: catalogSubtypeValue,
        catalog_name: catalogNameValue,
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
              tagNameInput={tagNameInput}
              setTagNameInput={setTagNameInput}
              tagValueInput={tagValueInput}
              setTagValueInput={setTagValueInput}
              handleKeyDown={handleKeyDown}
              error={null}
              onGenerateReasoning={handleGenerateReasoning}
              isGeneratingReasoning={isGeneratingReasoning}
            >
              <CardFooter className="flex justify-end space-x-4 border-t pt-6 mt-6">
                <Button 
                  type="button"
                  variant="outline" 
                  onClick={() => router.push("/cache-entries")}
                  className="px-6"
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={saving} className="px-6">
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