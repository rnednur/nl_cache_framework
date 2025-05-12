"use client"

import { useState, useEffect } from "react"
import { Sparkles, Check, Info, AlertCircle, ArrowLeft, ArrowRight } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../components/ui/card"
import { Button } from "../../components/ui/button"
import { Textarea } from "../../components/ui/textarea"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { Switch } from "../../components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs"
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
  const [resultsHistory, setResultsHistory] = useState<CompleteResponse[]>([])
  const [currentHistoryIndex, setCurrentHistoryIndex] = useState(-1)
  
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
      
      // Add to history
      setResultsHistory(prev => [...prev, response])
      setCurrentHistoryIndex(prev => prev + 1)
    } catch (err: any) {
      setError(err.message || "An error occurred while processing your request")
      setResult(null)
    } finally {
      setLoading(false)
    }
  }
  
  const goToPreviousResult = () => {
    if (currentHistoryIndex > 0) {
      setCurrentHistoryIndex(currentHistoryIndex - 1)
      setResult(resultsHistory[currentHistoryIndex - 1])
    }
  }
  
  const goToNextResult = () => {
    if (currentHistoryIndex < resultsHistory.length - 1) {
      setCurrentHistoryIndex(currentHistoryIndex + 1)
      setResult(resultsHistory[currentHistoryIndex + 1])
    }
  }
  
  return (
    <div className="container mx-auto py-4 space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-neutral-200">Complete Test</h1>
        <Button 
          variant="outline" 
          onClick={() => window.location.reload()}
          size="sm"
          className="border-neutral-700 hover:bg-neutral-800 hover:text-neutral-200 text-neutral-300"
        >
          Reset
        </Button>
      </div>
      
      <div className="flex flex-col space-y-3">
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-neutral-200">
              <Sparkles className="h-5 w-5" />
              Complete Endpoint Testing
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Test the /complete endpoint with optional LLM enhancement
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <Label htmlFor="prompt" className="text-neutral-300">Natural Language Prompt</Label>
                <Textarea 
                  id="prompt"
                  placeholder="Enter your natural language query..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="h-28 bg-neutral-800 border-neutral-700 text-neutral-200 placeholder:text-neutral-500 focus-visible:ring-[#3B4BF6]"
                />
              </div>
              
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="use-llm"
                    checked={useLlm}
                    onCheckedChange={setUseLlm}
                  />
                  <Label htmlFor="use-llm" className="cursor-pointer text-neutral-300">
                    Enable LLM Enhancement
                  </Label>
                  <span className="text-xs text-neutral-500 ml-2">
                    (Uses Gemini Flash 2.5 to analyze search results)
                  </span>
                </div>
                
                <div className="flex items-center gap-2">
                  <Label htmlFor="threshold" className="whitespace-nowrap text-neutral-300">Similarity Threshold:</Label>
                  <Input 
                    id="threshold"
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                    className="w-24 bg-neutral-800 border-neutral-700 text-neutral-200"
                  />
                  <span className="text-xs whitespace-nowrap text-neutral-500">(0.0 - 1.0)</span>
                </div>
              </div>
              
              <div className="flex flex-wrap gap-3">
                <div className="flex-1 min-w-[200px]">
                  <Label htmlFor="catalog-type" className="text-neutral-300">Catalog Type (Optional)</Label>
                  {loadingCatalogs ? (
                    <div className="p-2 border border-neutral-700 rounded-md text-neutral-500 bg-neutral-800">Loading...</div>
                  ) : (
                    <Select value={catalogType} onValueChange={setCatalogType}>
                      <SelectTrigger id="catalog-type" className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectValue placeholder="Select catalog type" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        {catalogValues.catalog_types.map((type) => (
                          <SelectItem key={type} value={type} className="text-neutral-300">{type}</SelectItem>
                        ))}
                        <SelectItem value="reasoning_steps" className="text-neutral-300">Reasoning Steps</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                </div>
                
                <div className="flex-1 min-w-[200px]">
                  <Label htmlFor="catalog-subtype" className="text-neutral-300">Catalog Subtype (Optional)</Label>
                  {loadingCatalogs ? (
                    <div className="p-2 border border-neutral-700 rounded-md text-neutral-500 bg-neutral-800">Loading...</div>
                  ) : (
                    <Select value={catalogSubtype} onValueChange={setCatalogSubtype}>
                      <SelectTrigger id="catalog-subtype" className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectValue placeholder="Select catalog subtype" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        {catalogValues.catalog_subtypes.map((subtype) => (
                          <SelectItem key={subtype} value={subtype} className="text-neutral-300">{subtype}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
                
                <div className="flex-1 min-w-[200px]">
                  <Label htmlFor="catalog-name" className="text-neutral-300">Catalog Name (Optional)</Label>
                  {loadingCatalogs ? (
                    <div className="p-2 border border-neutral-700 rounded-md text-neutral-500 bg-neutral-800">Loading...</div>
                  ) : (
                    <Select value={catalogName} onValueChange={setCatalogName}>
                      <SelectTrigger id="catalog-name" className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        <SelectValue placeholder="Select catalog name" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-800 border-neutral-700 text-neutral-300">
                        {catalogValues.catalog_names.map((name) => (
                          <SelectItem key={name} value={name} className="text-neutral-300">{name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button 
              onClick={handleSubmit} 
              disabled={loading || !prompt.trim()}
              className="w-full bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white"
            >
              {loading ? "Processing..." : "Submit"}
            </Button>
          </CardFooter>
        </Card>
        
        <Card className="bg-neutral-900 border-neutral-700 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-neutral-200">Result</CardTitle>
              <CardDescription className="text-neutral-400">
                Response from the /complete endpoint
              </CardDescription>
            </div>
            {resultsHistory.length > 1 && (
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="icon" 
                  onClick={goToPreviousResult}
                  disabled={currentHistoryIndex <= 0}
                  className="border-neutral-700 hover:bg-neutral-800 hover:text-neutral-200 text-neutral-300"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <span className="text-xs text-neutral-400">
                  {currentHistoryIndex + 1} / {resultsHistory.length}
                </span>
                <Button 
                  variant="outline" 
                  size="icon" 
                  onClick={goToNextResult}
                  disabled={currentHistoryIndex >= resultsHistory.length - 1}
                  className="border-neutral-700 hover:bg-neutral-800 hover:text-neutral-200 text-neutral-300"
                >
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <div className="p-3 border border-red-700 bg-red-900/30 rounded-md text-red-300 flex gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p>{error}</p>
              </div>
            )}
            
            {loading && (
              <div className="flex flex-col items-center justify-center h-40 text-neutral-400">
                <p>Processing your request...</p>
              </div>
            )}
            
            {!loading && result && (
              <div className="space-y-4 overflow-auto max-h-[500px]">
                <Tabs defaultValue="result" className="w-full">
                  <TabsList className="bg-neutral-800 border-neutral-700">
                    <TabsTrigger value="result" className="data-[state=active]:bg-neutral-700 data-[state=active]:text-neutral-200">Template Result</TabsTrigger>
                    <TabsTrigger value="prompt" className="data-[state=active]:bg-neutral-700 data-[state=active]:text-neutral-200">Processed Prompt</TabsTrigger>
                    <TabsTrigger value="details" className="data-[state=active]:bg-neutral-700 data-[state=active]:text-neutral-200">Response Details</TabsTrigger>
                    <TabsTrigger value="matches" className="data-[state=active]:bg-neutral-700 data-[state=active]:text-neutral-200">Score Details</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="result" className="space-y-4 pt-4">
                    <div className="space-y-1">
                      <div className="flex items-center text-sm text-neutral-200">
                        <h4 className="font-semibold mr-2">Status:</h4>
                        {result.success ? (
                          <span className="flex items-center text-green-500">
                            <Check className="h-4 w-4 mr-1" />
                            Success
                          </span>
                        ) : (
                          <span className="flex items-center text-red-500">
                            <AlertCircle className="h-4 w-4 mr-1" />
                            No Match Found
                          </span>
                        )}
                      </div>
                      
                      {result.similarity_score !== undefined && (
                        <div className="flex items-center text-sm text-neutral-200">
                          <h4 className="font-semibold mr-2">Similarity Score:</h4>
                          <span>{(result.similarity_score * 100).toFixed(2)}%</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="p-4 border border-neutral-700 rounded-md bg-neutral-800 whitespace-pre-wrap text-neutral-200 font-mono overflow-auto max-h-[300px]">
                      {result.result || "No result returned"}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="prompt" className="space-y-4 pt-4">
                    <div className="p-4 border border-neutral-700 rounded-md bg-neutral-800 whitespace-pre-wrap text-neutral-200 font-mono overflow-auto max-h-[300px]">
                      {result.processed_prompt || prompt}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="details" className="space-y-4 pt-4">
                    <div className="p-4 border border-neutral-700 rounded-md bg-neutral-800 text-neutral-200 overflow-auto max-h-[300px]">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Response Time</h4>
                          <p>{result.response_time}ms</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Template Type</h4>
                          <p className="capitalize">{result.template_type || "Not specified"}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-1">LLM Used</h4>
                          <p>{result.llm_used ? "Yes" : "No"}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Cache Hit</h4>
                          <p>{result.cache_hit ? "Yes" : "No"}</p>
                        </div>
                        {result.cache_entry_id && (
                          <div className="col-span-2">
                            <h4 className="font-semibold text-sm mb-1">Cache Entry ID</h4>
                            <p>{result.cache_entry_id}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="matches" className="space-y-4 pt-4">
                    <div className="p-4 border border-neutral-700 rounded-md bg-neutral-800 text-neutral-200 overflow-auto max-h-[300px]">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-semibold text-sm mb-1">User Query</h4>
                          <p>{result.user_query}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Use LLM</h4>
                          <p>{useLlm ? "Yes" : "No"}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Threshold</h4>
                          <p>{threshold}</p>
                        </div>
                        {catalogType && (
                          <div>
                            <h4 className="font-semibold text-sm mb-1">Catalog Type</h4>
                            <p>{catalogType}</p>
                          </div>
                        )}
                        {result.similarity_score !== undefined && (
                          <div>
                            <h4 className="font-semibold text-sm mb-1">Similarity Score</h4>
                            <p>{(result.similarity_score * 100).toFixed(2)}%</p>
                          </div>
                        )}
                        {result.template_id !== undefined && (
                          <div>
                            <h4 className="font-semibold text-sm mb-1">Template ID</h4>
                            <p>
                              <a 
                                href={`/cache-entries/${result.template_id}`} 
                                className="text-blue-500 hover:text-blue-400"
                              >
                                {result.template_id}
                              </a>
                            </p>
                          </div>
                        )}
                        {result.cached_query && (
                          <div>
                            <h4 className="font-semibold text-sm mb-1">Cached Query</h4>
                            <p>{result.cached_query}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            )}
            
            {!loading && !error && !result && (
              <div className="flex items-center justify-center h-48 text-neutral-500">
                <p>Submit a request to see results</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 