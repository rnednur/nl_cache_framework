"use client"

import { useState, useEffect } from "react"
import { Sparkles, Check, Info, AlertCircle, ArrowLeft, ArrowRight, ExternalLink } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/app/components/ui/card"
import { Button } from "@/app/components/ui/button"
import { Textarea } from "@/app/components/ui/textarea"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { Switch } from "@/app/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/app/components/ui/tabs"
import api, { CompleteRequest, CompleteResponse as ApiCompleteResponse, CatalogValues } from "../../services/api"
import Link from "next/link"
import { CacheEntryModal } from "@/components/ui/CacheEntryModal"
import { CacheBreadcrumbs } from "@/components/ui/CacheBreadcrumbs"
import { CacheEntryTooltip } from "@/components/ui/CacheEntryTooltip"
import { SimpleCacheTooltip } from "@/components/ui/SimpleCacheTooltip"
import { CacheEntryList } from "@/components/ui/CacheEntryList"
import { toast } from "react-hot-toast"

// Extended response interface to include UI-specific fields
interface ExtendedCompleteResponse extends ApiCompleteResponse {
  success?: boolean;
  result?: string;
  processed_prompt?: string;
  response_time?: number;
  template_type?: string;
  llm_used?: boolean;
  cache_entry_id?: number;
  is_confident?: boolean;
}

// Define the state interface for persistence
interface CompleteTestState {
  prompt: string;
  threshold: number;
  limit: number;
  catalogType: string;
  catalogSubtype: string;
  catalogName: string;
  useLlm: boolean;
  resultsHistory: ExtendedCompleteResponse[];
  currentHistoryIndex: number;
}

export default function CompleteTestPage() {
  const [prompt, setPrompt] = useState("")
  const [threshold, setThreshold] = useState(0.85)
  const [limit, setLimit] = useState(5)
  const [catalogType, setCatalogType] = useState("")
  const [catalogSubtype, setCatalogSubtype] = useState("")
  const [catalogName, setCatalogName] = useState("")
  const [useLlm, setUseLlm] = useState(false)
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({ catalog_types: [], catalog_subtypes: [], catalog_names: [] })
  const [loadingCatalogs, setLoadingCatalogs] = useState(false)
  
  const [result, setResult] = useState<ExtendedCompleteResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resultsHistory, setResultsHistory] = useState<ExtendedCompleteResponse[]>([])
  const [currentHistoryIndex, setCurrentHistoryIndex] = useState(-1)
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedCacheEntryId, setSelectedCacheEntryId] = useState<number | null>(null)
  
  // Load state from localStorage on component mount
  useEffect(() => {
    const savedState = localStorage.getItem('completeTestState');
    if (savedState) {
      try {
        const parsedState = JSON.parse(savedState) as CompleteTestState;
        
        // Only restore results if there's a prompt - this ensures synchronization
        if (parsedState.prompt && parsedState.prompt.trim() !== "") {
          setPrompt(parsedState.prompt);
          setThreshold(parsedState.threshold);
          setLimit(parsedState.limit);
          setCatalogType(parsedState.catalogType);
          setCatalogSubtype(parsedState.catalogSubtype);
          setCatalogName(parsedState.catalogName);
          setUseLlm(parsedState.useLlm);
          setResultsHistory(parsedState.resultsHistory);
          setCurrentHistoryIndex(parsedState.currentHistoryIndex);
          
          if (parsedState.resultsHistory.length > 0 && parsedState.currentHistoryIndex >= 0) {
            setResult(parsedState.resultsHistory[parsedState.currentHistoryIndex]);
          }
        } else {
          // If there's no prompt, don't restore results - this prevents orphaned results
          console.log("No prompt found in saved state, clearing results");
          localStorage.removeItem('completeTestState');
        }
      } catch (e) {
        console.error("Failed to parse saved state", e);
        // Clear invalid state
        localStorage.removeItem('completeTestState');
      }
    }
  }, []);
  
  // Save state to localStorage whenever key values change
  useEffect(() => {
    // Only save state if both prompt and results exist
    if (prompt && prompt.trim() !== "") {
      const stateToSave: CompleteTestState = {
        prompt,
        threshold,
        limit,
        catalogType,
        catalogSubtype,
        catalogName,
        useLlm,
        resultsHistory,
        currentHistoryIndex
      };
      localStorage.setItem('completeTestState', JSON.stringify(stateToSave));
    } else if (localStorage.getItem('completeTestState')) {
      // If prompt is empty but we have saved state, remove it
      localStorage.removeItem('completeTestState');
    }
  }, [prompt, threshold, limit, catalogType, catalogSubtype, catalogName, useLlm, resultsHistory, currentHistoryIndex]);

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
        similarity_threshold: threshold,
        limit: limit
      }
      
      if (catalogType) request.catalog_type = catalogType
      if (catalogSubtype) request.catalog_subtype = catalogSubtype
      if (catalogName) request.catalog_name = catalogName
      
      // Add timeout handling
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
      
      try {
        const response = await api.complete(request);
        clearTimeout(timeoutId);
        
        // Adapt response to UI expectations
        const extendedResponse: ExtendedCompleteResponse = {
          ...response,
          success: response.cache_hit,
          result: response.updated_template || response.cache_template,
          processed_prompt: response.user_query,
          llm_used: useLlm,
          cache_entry_id: response.cache_entry_id,
          is_confident: response.is_confident
        }
        
        setResult(extendedResponse)
        
        // Add to history
        setResultsHistory(prev => [...prev, extendedResponse])
        setCurrentHistoryIndex(prev => prev + 1)
      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        
        if (fetchError.name === 'AbortError') {
          setError("Request timed out. The server took too long to respond.");
        } else {
          throw fetchError; // Let the outer catch handle other types of errors
        }
      }
    } catch (err: any) {
      console.error("API request failed:", err);
      if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
        setError("Cannot connect to the backend server. Please check if the server is running.");
      } else {
        setError(err.message || "An error occurred while processing your request");
      }
      setResult(null)
    } finally {
      setLoading(false)
    }
  }
  
  const goToPreviousResult = () => {
    if (currentHistoryIndex > 0) {
      const previousIndex = currentHistoryIndex - 1;
      setCurrentHistoryIndex(previousIndex);
      setResult(resultsHistory[previousIndex]);
    }
  }
  
  const goToNextResult = () => {
    if (currentHistoryIndex < resultsHistory.length - 1) {
      const nextIndex = currentHistoryIndex + 1;
      setCurrentHistoryIndex(nextIndex);
      setResult(resultsHistory[nextIndex]);
    }
  }

  const openCacheEntryModal = (id: number) => {
    setSelectedCacheEntryId(id);
    setModalOpen(true);
  }
  
  // Add event listener for page refresh/unload to ensure state consistency
  useEffect(() => {
    // Check if prompt and results are in sync on page visibility change
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // When tab becomes visible again, validate state consistency
        if (result && (!prompt || prompt.trim() === "")) {
          console.log("Detected mismatch: results present but prompt empty, clearing results");
          setResult(null);
          setResultsHistory([]);
          setCurrentHistoryIndex(-1);
          localStorage.removeItem('completeTestState');
        }
      }
    };

    // Also handle before unload to ensure we save clean state
    const handleBeforeUnload = () => {
      // Save current state before page refresh/unload
      if (prompt && prompt.trim() !== "") {
        const stateToSave: CompleteTestState = {
          prompt,
          threshold,
          limit,
          catalogType,
          catalogSubtype,
          catalogName,
          useLlm,
          resultsHistory,
          currentHistoryIndex
        };
        localStorage.setItem('completeTestState', JSON.stringify(stateToSave));
      } else {
        // If no prompt, don't save any state
        localStorage.removeItem('completeTestState');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [prompt, result, resultsHistory, currentHistoryIndex]);

  return (
    <div className="container mx-auto py-4 space-y-3">
      <CacheBreadcrumbs 
        items={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Complete Test" }
        ]}
        className="mb-2"
      />
      
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-neutral-200">Complete Test</h1>
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            onClick={() => {
              // Clear localStorage to remove saved state
              localStorage.removeItem('completeTestState');
              
              // Reset all state variables
              setPrompt("");
              setThreshold(0.85);
              setLimit(5);
              setCatalogType("");
              setCatalogSubtype("");
              setCatalogName("");
              setUseLlm(false);
              setResult(null);
              setError(null);
              setResultsHistory([]);
              setCurrentHistoryIndex(-1);
              
              // Show success message
              toast.success("Form has been reset");
            }}
            size="sm"
            className="border-neutral-700 hover:bg-neutral-800 hover:text-neutral-200 text-neutral-300"
          >
            Reset
          </Button>
          {(resultsHistory.length > 0 || result) && (
            <Button 
              variant="destructive" 
              onClick={() => {
                // Only clear results, not inputs
                setResult(null);
                setError(null);
                setResultsHistory([]);
                setCurrentHistoryIndex(-1);
                
                // Show success message
                toast.success("Results cleared");
              }}
              size="sm"
              className="bg-red-900 hover:bg-red-800 text-white"
            >
              Clear Results
            </Button>
          )}
        </div>
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
                <div className="flex items-center space-x-2 py-2">
                  <Switch
                    id="use-llm"
                    checked={useLlm}
                    onCheckedChange={setUseLlm}
                    className="data-[state=checked]:bg-blue-600"
                  />
                  <Label htmlFor="use-llm" className="cursor-pointer text-neutral-200">
                    Enable LLM Enhancement
                  </Label>
                  <span className="text-xs text-neutral-400 ml-2">
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
                
                <div className="flex items-center gap-2">
                  <Label htmlFor="limit" className="whitespace-nowrap text-neutral-300">Result Limit:</Label>
                  <Input 
                    id="limit"
                    type="number"
                    min={1}
                    max={20}
                    step={1}
                    value={limit}
                    onChange={(e) => setLimit(parseInt(e.target.value))}
                    className="w-24 bg-neutral-800 border-neutral-700 text-neutral-200"
                  />
                  <span className="text-xs whitespace-nowrap text-neutral-500">(max results)</span>
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
                        <SelectItem value="dsl" className="text-neutral-300">DSL Components</SelectItem>
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
                {result.llm_used && result.is_confident === false && (
                  <div className="p-3 border border-yellow-700 bg-yellow-900/30 rounded-md text-yellow-300 flex gap-2">
                    <AlertCircle className="h-5 w-5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold">Low Confidence Warning</p>
                      <p className="text-sm">The LLM has determined that this answer may not be accurate or complete. Review the explanation for details.</p>
                    </div>
                  </div>
                )}
                
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
                        {result.cache_hit ? (
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
                      {result.updated_template || result.cache_template || "No result returned"}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="prompt" className="space-y-4 pt-4">
                    <div className="p-4 border border-neutral-700 rounded-md bg-neutral-800 whitespace-pre-wrap text-neutral-200 font-mono overflow-auto max-h-[300px]">
                      {result.user_query || prompt}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="details" className="space-y-4 pt-4">
                    <div className="p-4 border border-neutral-700 rounded-md bg-neutral-800 text-neutral-200 overflow-auto max-h-[300px]">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Response Time</h4>
                          <p>{result.response_time || "N/A"}ms</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Template Type</h4>
                          <p className="capitalize">{result.template_type || "Not specified"}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm mb-1">LLM Used</h4>
                          <p>{result.llm_used ? "Yes" : "No"}</p>
                        </div>
                        {result.cache_entry_id && (
                          <div>
                            <h4 className="font-semibold text-sm mb-1">Cache Entry</h4>
                            <div className="flex items-center gap-2">
                              <Button 
                                variant="link" 
                                className="h-auto p-0 text-blue-500 hover:text-blue-400"
                                onClick={() => openCacheEntryModal(result.cache_entry_id!)}
                              >
                                View Entry
                              </Button>
                              <span className="text-xs text-neutral-500">
                                ID: <SimpleCacheTooltip 
                                  content={
                                    <div className="text-sm">
                                      <p className="text-neutral-300 mb-1">Cache Entry ID: {result.cache_entry_id}</p>
                                      <p className="text-neutral-400 text-xs">Click "View Entry" to see details</p>
                                    </div>
                                  }
                                >
                                  {result.cache_entry_id}
                                </SimpleCacheTooltip>
                              </span>
                            </div>
                          </div>
                        )}
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Cache Hit</h4>
                          <p>{result.cache_hit ? "Yes" : "No"}</p>
                        </div>
                        {result.template_id && (
                          <div className="col-span-2">
                            <h4 className="font-semibold text-sm mb-1">Template ID</h4>
                            <p>
                              <SimpleCacheTooltip
                                content={
                                  <div className="text-sm p-2">
                                    <div className="mb-2">
                                      <p className="text-neutral-300">Cache Entry ID: {result.template_id}</p>
                                      <p className="text-neutral-400 text-xs mt-1">
                                        This is the template that was matched and used for the response
                                      </p>
                                    </div>
                                    <div className="mt-2 text-xs">
                                      <a 
                                        href={`/cache-entries/${result.template_id}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-400 hover:underline"
                                      >
                                        Click to open entry in new tab
                                      </a>
                                    </div>
                                  </div>
                                }
                              >
                                <a 
                                  href={`/cache-entries/${result.template_id}`} 
                                  className="text-blue-500 hover:text-blue-400"
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  {result.template_id}
                                </a>
                              </SimpleCacheTooltip>
                            </p>
                          </div>
                        )}
                        {result.llm_explanation && (
                          <div className="col-span-2">
                            <h4 className="font-semibold text-sm mb-1">LLM Explanation</h4>
                            <p>{result.llm_explanation}</p>
                          </div>
                        )}
                        {result.llm_used && (
                          <div className="col-span-2">
                            <h4 className="font-semibold text-sm mb-1">LLM Confidence</h4>
                            <p className={`flex items-center ${result.is_confident ? 'text-green-500' : 'text-yellow-500'}`}>
                              {result.is_confident ? (
                                <>
                                  <Check className="h-4 w-4 mr-1" />
                                  Confident
                                </>
                              ) : (
                                <>
                                  <AlertCircle className="h-4 w-4 mr-1" />
                                  Low Confidence
                                </>
                              )}
                            </p>
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
                          <p>{result.llm_used ? "Yes" : "No"}</p>
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
                        {result.cached_query && (
                          <div>
                            <h4 className="font-semibold text-sm mb-1">Cached Query</h4>
                            <p>{result.cached_query}</p>
                          </div>
                        )}
                        {result.considered_entries && result.considered_entries.length > 0 && (
                          <div className="col-span-2">
                            <h4 className="font-semibold text-sm mb-1">All Considered Cache Entries</h4>
                            <CacheEntryList entryIds={result.considered_entries} />
                          </div>
                        )}
                        {result.updated_template && (
                          <div className="col-span-2">
                            <h4 className="font-semibold text-sm mb-1">Updated Template</h4>
                            <p className="font-mono text-xs">{result.updated_template}</p>
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

      {/* Cache Entry Modal */}
      <CacheEntryModal 
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        cacheEntryId={selectedCacheEntryId}
        source={{
          type: "complete-test",
          label: "Complete Test",
          href: "/complete-test"
        }}
      />
    </div>
  )
} 