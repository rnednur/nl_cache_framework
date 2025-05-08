"use client"

import { useState, useEffect } from "react"
import { Sparkles, Check, Info, AlertCircle } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Textarea } from "../../components/ui/textarea"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { Switch } from "../../components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select"
import api, { CompleteRequest, CompleteResponse, CatalogValues } from "../../services/api"

export default function CompleteTestPage() {
  const [prompt, setPrompt] = useState("")
  const [threshold, setThreshold] = useState(0.85)
  const [catalogType, setCatalogType] = useState("")
  const [catalogSubtype, setCatalogSubtype] = useState("")
  const [catalogName, setCatalogName] = useState("")
  const [useLlm, setUseLlm] = useState(false)
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({ catalog_types: [], catalog_subtypes: [], catalog_names: [] })
  const [loadingCatalogs, setLoadingCatalogs] = useState(false)
  
  const [result, setResult] = useState<CompleteResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    const fetchCatalogValues = async () => {
      setLoadingCatalogs(true)
      try {
        const values = await api.getCatalogValues()
        setCatalogValues(values)
      } catch (err) {
        console.error("Failed to fetch catalog values", err)
      } finally {
        setLoadingCatalogs(false)
      }
    }
    fetchCatalogValues()
  }, [])
  
  const handleSubmit = async () => {
    if (!prompt.trim()) {
      setError("Please enter a prompt.")
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const request: CompleteRequest = {
        prompt,
        use_llm: useLlm,
        similarity_threshold: threshold
      }
      
      if (catalogType) request.catalog_type = catalogType
      if (catalogSubtype) request.catalog_subtype = catalogSubtype
      if (catalogName) request.catalog_name = catalogName
      
      const response = await api.complete(request)
      setResult(response)
    } catch (err: any) {
      setError(err.message || "An error occurred while processing your request")
      setResult(null)
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="container mx-auto py-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Complete Test</h1>
        <Button 
          variant="outline" 
          onClick={() => window.location.reload()}
        >
          Reset
        </Button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              Complete Endpoint Testing
            </CardTitle>
            <CardDescription>
              Test the /complete endpoint with optional LLM enhancement
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="prompt">Natural Language Prompt</Label>
              <Textarea 
                id="prompt"
                placeholder="Enter your natural language query..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="h-32"
              />
            </div>
            
            <div className="flex items-center space-x-2 mt-4">
              <Switch
                id="use-llm"
                checked={useLlm}
                onCheckedChange={setUseLlm}
              />
              <Label htmlFor="use-llm" className="cursor-pointer">
                Enable LLM Enhancement
              </Label>
              <span className="text-xs text-slate-500 ml-2">
                (Uses Gemini Flash 2.5 to analyze search results)
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <Label htmlFor="threshold">Similarity Threshold</Label>
                <div className="flex items-center gap-2">
                  <Input 
                    id="threshold"
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  />
                  <span className="text-xs whitespace-nowrap">(0.0 - 1.0)</span>
                </div>
              </div>
              
              <div>
                <Label htmlFor="catalog-type">Catalog Type (Optional)</Label>
                {loadingCatalogs ? (
                  <div className="p-2 border border-slate-200 rounded-md text-slate-500">Loading...</div>
                ) : (
                  <Select value={catalogType} onValueChange={setCatalogType}>
                    <SelectTrigger id="catalog-type">
                      <SelectValue placeholder="Select catalog type" />
                    </SelectTrigger>
                    <SelectContent>
                      {catalogValues.catalog_types.map((type) => (
                        <SelectItem key={type} value={type}>{type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
              
              <div>
                <Label htmlFor="catalog-subtype">Catalog Subtype (Optional)</Label>
                {loadingCatalogs ? (
                  <div className="p-2 border border-slate-200 rounded-md text-slate-500">Loading...</div>
                ) : (
                  <Select value={catalogSubtype} onValueChange={setCatalogSubtype}>
                    <SelectTrigger id="catalog-subtype">
                      <SelectValue placeholder="Select catalog subtype" />
                    </SelectTrigger>
                    <SelectContent>
                      {catalogValues.catalog_subtypes.map((subtype) => (
                        <SelectItem key={subtype} value={subtype}>{subtype}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
              
              <div>
                <Label htmlFor="catalog-name">Catalog Name (Optional)</Label>
                {loadingCatalogs ? (
                  <div className="p-2 border border-slate-200 rounded-md text-slate-500">Loading...</div>
                ) : (
                  <Select value={catalogName} onValueChange={setCatalogName}>
                    <SelectTrigger id="catalog-name">
                      <SelectValue placeholder="Select catalog name" />
                    </SelectTrigger>
                    <SelectContent>
                      {catalogValues.catalog_names.map((name) => (
                        <SelectItem key={name} value={name}>{name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button 
              onClick={handleSubmit} 
              disabled={loading || !prompt.trim()}
              className="w-full"
            >
              {loading ? "Processing..." : "Submit"}
            </Button>
          </CardFooter>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
            <CardDescription>
              Response from the /complete endpoint
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="flex flex-col items-center justify-center h-60 text-slate-500">
                <Sparkles className="h-8 w-8 animate-pulse mb-2" />
                <p>Processing your request...</p>
              </div>
            )}
            
            {!loading && error && (
              <div className="p-4 border border-red-200 bg-red-50 rounded-md text-red-700 flex gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Error</p>
                  <p className="text-sm">{error}</p>
                </div>
              </div>
            )}
            
            {!loading && !error && result && (
              <div className="space-y-4">
                {result.warning && (
                  <div className="p-3 border border-yellow-200 bg-yellow-50 rounded-md text-yellow-700 text-sm flex gap-2">
                    <Info className="h-5 w-5 flex-shrink-0" />
                    <p>{result.warning}</p>
                  </div>
                )}
                
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-500">Cache Hit:</p>
                    <span className={`flex items-center ${result.cache_hit ? 'text-green-600' : 'text-slate-500'}`}>
                      {result.cache_hit ? (
                        <>
                          <Check className="h-4 w-4 mr-1" />
                          Yes
                        </>
                      ) : 'No'}
                    </span>
                  </div>
                  
                  {result.similarity_score !== undefined && (
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-500">Similarity:</p>
                      <span>{(result.similarity_score * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  
                  {result.template_id !== undefined && (
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-500">Template ID:</p>
                      <span>
                        <a 
                          href={`/cache-entries/${result.template_id}`} 
                          className="text-blue-600 hover:underline flex items-center"
                        >
                          {result.template_id}
                        </a>
                      </span>
                    </div>
                  )}
                </div>
                
                <div className="space-y-2 mt-4">
                  <Label>Final Result:</Label>
                  {result.cache_hit || result.updated_template ? (
                    <div className="p-3 border border-slate-200 bg-slate-50 rounded-md whitespace-pre-wrap text-sm max-h-40 overflow-y-auto">
                      {result.updated_template
                        ? result.updated_template // LLM improved or adapted result
                        : result.cache_template // cached template
                      }
                    </div>
                  ) : (
                    <div className="p-3 border border-red-100 bg-red-50 rounded-md text-red-700 flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 flex-shrink-0" />
                      <p>No matching template found in cache.</p>
                    </div>
                  )}
                  {result.cache_hit && result.updated_template && (
                    <div className="text-xs text-slate-500 mt-1">
                      (adapted from cache)
                    </div>
                  )}
                  {result.cache_hit && !result.updated_template && (
                    <div className="text-xs text-slate-500 mt-1">
                      (from cache)
                    </div>
                  )}
                </div>
                
                {result.cache_hit && result.updated_template && result.cache_template !== result.updated_template && (
                  <div className="space-y-2 mt-4">
                    <Label>Original Cached Template:</Label>
                    <div className="p-3 border border-slate-200 bg-slate-50 rounded-md whitespace-pre-wrap text-sm max-h-40 overflow-y-auto text-slate-600">
                      {result.cache_template}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      (original template from cache ID: {result.template_id})
                    </div>
                  </div>
                )}
                
                {result.llm_explanation && (
                  <div className="mt-4 text-xs text-slate-500 italic">
                    {result.llm_explanation}
                  </div>
                )}
              </div>
            )}
            
            {!loading && !error && !result && (
              <div className="flex items-center justify-center h-60 text-slate-500">
                <p>Submit a request to see results</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 