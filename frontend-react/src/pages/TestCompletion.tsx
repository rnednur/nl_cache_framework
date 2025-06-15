import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import api, { type CatalogValues } from "@/services/api";
import { Check, AlertCircle } from "lucide-react";
import { SimpleCacheTooltip } from "@/components/ui/simple-cache-tooltip";
import { Link } from "react-router-dom";

interface ExtendedCompleteResponse {
  cache_hit?: boolean;
  similarity_score?: number;
  cache_template?: string;
  updated_template?: string;
  user_query?: string;
  llm_explanation?: string;
  cache_entry_id?: number;
  is_confident?: boolean;
  [key: string]: any;
}

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

export default function TestCompletion() {
  const [prompt, setPrompt] = useState("");
  const [threshold, setThreshold] = useState(0.85);
  const [limit, setLimit] = useState(5);
  const [catalogType, setCatalogType] = useState("");
  const [catalogSubtype, setCatalogSubtype] = useState("");
  const [catalogName, setCatalogName] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const [catalogValues, setCatalogValues] = useState<CatalogValues>({ catalog_types: [], catalog_subtypes: [], catalog_names: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultsHistory, setResultsHistory] = useState<ExtendedCompleteResponse[]>([]);
  const [currentHistoryIndex, setCurrentHistoryIndex] = useState(-1);
  const [activeTab, setActiveTab] = useState("template");

  // State persistence
  useEffect(() => {
    const savedState = localStorage.getItem('completeTestState');
    if (savedState) {
      try {
        const parsedState = JSON.parse(savedState) as CompleteTestState;
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
        } else {
          localStorage.removeItem('completeTestState');
        }
      } catch (e) {
        localStorage.removeItem('completeTestState');
      }
    }
  }, []);

  useEffect(() => {
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
      localStorage.removeItem('completeTestState');
    }
  }, [prompt, threshold, limit, catalogType, catalogSubtype, catalogName, useLlm, resultsHistory, currentHistoryIndex]);

  useEffect(() => {
    api.getCatalogValues().then(setCatalogValues).catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await api.complete({
        prompt,
        use_llm: useLlm,
        similarity_threshold: threshold,
        limit,
        catalog_type: catalogType || undefined,
        catalog_subtype: catalogSubtype || undefined,
        catalog_name: catalogName || undefined,
      });
      const extendedResponse: ExtendedCompleteResponse = {
        ...response,
        result: response.updated_template || response.cache_template,
        processed_prompt: response.user_query,
        cache_entry_id: response.cache_entry_id,
        is_confident: response.is_confident
      };
      setResultsHistory(prev => [...prev, extendedResponse]);
      setCurrentHistoryIndex(prev => prev + 1);
      setActiveTab("template");
    } catch (err: any) {
      setError(err.message || "Failed to complete test");
    } finally {
      setLoading(false);
    }
  };

  

  const handleReset = () => {
    setPrompt("");
    setThreshold(0.85);
    setLimit(5);
    setCatalogType("");
    setCatalogSubtype("");
    setCatalogName("");
    setUseLlm(false);
    setError(null);
  };

  const handleClearResults = () => {
    setResultsHistory([]);
    setCurrentHistoryIndex(-1);
    setActiveTab("template");
  };

  const currentResult = currentHistoryIndex >= 0 ? resultsHistory[currentHistoryIndex] : null;

  return (
    <div className="min-h-screen bg-[#18192a] py-10 px-2">
      <div className="max-w-9xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm text-neutral-400 flex items-center gap-2">
            <span className="text-neutral-400">&#8962;</span>
            <span className="mx-1">/</span>
            <span className="text-neutral-400">Dashboard</span>
            <span className="mx-1">/</span>
            <span className="text-white font-semibold">Complete Test</span>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleReset} className="text-white border-neutral-700 bg-[#23243a] hover:bg-[#23243a]/80">Reset</Button>
            <Button variant="destructive" onClick={handleClearResults}>Clear Results</Button>
          </div>
        </div>
        <Card className="bg-[#23243a] border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="text-white">Complete Test</CardTitle>
            <CardDescription className="text-neutral-400">Test the /complete endpoint with optional LLM enhancement</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <Label htmlFor="prompt" className="text-neutral-200">Natural Language Prompt</Label>
                <Textarea id="prompt" value={prompt} onChange={e => setPrompt(e.target.value)} required className="bg-[#18192a] text-white border-neutral-700" />
              </div>
              <div className="flex flex-col md:flex-row md:items-center gap-4">
                <div className="flex items-center gap-2 flex-1">
                  <Switch id="use-llm" checked={useLlm} onCheckedChange={setUseLlm} />
                  <Label htmlFor="use-llm" className="text-neutral-200">Enable LLM Enhancement</Label>
                  <span className="text-xs text-neutral-400">(Uses Gemini Flash 2.5 to analyze search results)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="threshold" className="text-neutral-200">Similarity Threshold:</Label>
                  <Input id="threshold" type="number" min={0} max={1} step={0.01} value={threshold} onChange={e => setThreshold(Number(e.target.value))} className="w-20 bg-[#18192a] text-white border-neutral-700" />
                  <span className="text-xs text-neutral-400">(0.0 - 1.0)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="limit" className="text-neutral-200">Result Limit:</Label>
                  <Input id="limit" type="number" min={1} max={20} value={limit} onChange={e => setLimit(Number(e.target.value))} className="w-20 bg-[#18192a] text-white border-neutral-700" />
                  <span className="text-xs text-neutral-400">(max results)</span>
                </div>
              </div>
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <Label className="text-neutral-200">Catalog Type (Optional)</Label>
                  <Select value={catalogType} onValueChange={setCatalogType}>
                    <SelectTrigger className="bg-[#18192a] text-white border-neutral-700"><SelectValue placeholder="Select catalog type" /></SelectTrigger>
                    <SelectContent className="bg-[#23243a] text-white border-neutral-700">
                      {catalogValues.catalog_types.map(type => <SelectItem key={type} value={type}>{type}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1">
                  <Label className="text-neutral-200">Catalog Subtype (Optional)</Label>
                  <Select value={catalogSubtype} onValueChange={setCatalogSubtype}>
                    <SelectTrigger className="bg-[#18192a] text-white border-neutral-700"><SelectValue placeholder="Select catalog subtype" /></SelectTrigger>
                    <SelectContent className="bg-[#23243a] text-white border-neutral-700">
                      {catalogValues.catalog_subtypes.map(subtype => <SelectItem key={subtype} value={subtype}>{subtype}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1">
                  <Label className="text-neutral-200">Catalog Name (Optional)</Label>
                  <Select value={catalogName} onValueChange={setCatalogName}>
                    <SelectTrigger className="bg-[#18192a] text-white border-neutral-700"><SelectValue placeholder="Select catalog name" /></SelectTrigger>
                    <SelectContent className="bg-[#23243a] text-white border-neutral-700">
                      {catalogValues.catalog_names.map(name => <SelectItem key={name} value={name}>{name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button type="submit" className="w-full bg-[#3B4BF6] hover:bg-[#2b3bdc] text-white text-lg font-semibold py-2" disabled={loading}>{loading ? "Submitting..." : "Submit"}</Button>
            </form>
            {error && <div className="mt-4 text-red-500">{error}</div>}
          </CardContent>
        </Card>
        {currentResult && (
          <Card className="bg-[#23243a] border-0 shadow-lg mt-8">
            <CardHeader>
              <CardTitle className="text-white text-lg">Result</CardTitle>
              <CardDescription className="text-neutral-400">Response from the /complete endpoint</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="mb-4 bg-[#18192a]">
                  <TabsTrigger value="template">Template Result</TabsTrigger>
                  <TabsTrigger value="prompt">Processed Prompt</TabsTrigger>
                  <TabsTrigger value="details">Response Details</TabsTrigger>
                  <TabsTrigger value="score">Score Details</TabsTrigger>
                </TabsList>
                <TabsContent value="template" className="space-y-4 pt-2">
                  <div className="space-y-1">
                    <div className="flex items-center text-sm text-neutral-200">
                      <h4 className="font-semibold mr-2">Status:</h4>
                      {currentResult.cache_hit ? (
                        <span className="flex items-center text-green-500">
                          <Check className="h-4 w-4 mr-1" />
                          Success
                        </span>
                      ) : (
                        <span className="flex items-center text-red-500">
                          <AlertCircle className="h-4 w-4 mr-1" />
                          No Match
                        </span>
                      )}
                    </div>
                    {currentResult.similarity_score !== undefined && (
                      <div className="flex items-center text-sm text-neutral-200">
                        <h4 className="font-semibold mr-2">Similarity Score:</h4>
                        <span>{(currentResult.similarity_score * 100).toFixed(2)}%</span>
                      </div>
                    )}
                  </div>
                  <div className="p-4 border border-neutral-700 rounded-md bg-[#18192a] whitespace-pre-wrap text-neutral-200 font-mono overflow-auto">
                    {currentResult.updated_template || currentResult.cache_template || "No result returned"}
                  </div>
                </TabsContent>

                <TabsContent value="prompt" className="space-y-4 pt-2">
                  <div className="p-4 border border-neutral-700 rounded-md bg-[#18192a] whitespace-pre-wrap text-neutral-200 font-mono overflow-auto">
                    {currentResult.user_query || prompt}
                  </div>
                </TabsContent>

                <TabsContent value="details" className="space-y-4 pt-2">
                  <div className="p-4 border border-neutral-700 rounded-md bg-[#18192a] text-neutral-200 overflow-auto max-h-[300px] space-y-4">
                    {/* First row values in 2-column grid */}
                    <div className="grid grid-cols-2 gap-4">
                      {/* Response Time */}
                      <div>
                        <h4 className="font-semibold text-sm mb-1">Response Time</h4>
                        <p>{currentResult.response_time ? `${currentResult.response_time}ms` : "N/A"}</p>
                      </div>

                      {/* Template Type */}
                      <div>
                        <h4 className="font-semibold text-sm mb-1">Template Type</h4>
                        <p className="capitalize">{currentResult.template_type || "Not Specified"}</p>
                      </div>

                      {/* LLM Used */}
                      <div>
                        <h4 className="font-semibold text-sm mb-1">LLM Used</h4>
                        <p>{currentResult.llm_used ? "Yes" : "No"}</p>
                      </div>

                      {/* Cache Hit */}
                      <div>
                        <h4 className="font-semibold text-sm mb-1">Cache Hit</h4>
                        <p>{currentResult.cache_hit ? "Yes" : "No"}</p>
                      </div>
                      {/* LLM Explanation */}
                    {currentResult.llm_explanation && (
                      <div>
                        <h4 className="font-semibold text-sm mb-1">LLM Explanation</h4>
                        <p>{currentResult.llm_explanation}</p>
                      </div>
                    )}

                    {/* LLM Confidence */}
                    {currentResult.is_confident !== undefined && (
                      <div>
                        <h4 className="font-semibold text-sm mb-1">LLM Confidence</h4>
                        <p className={currentResult.is_confident ? "text-green-500" : "text-yellow-500"}>{currentResult.is_confident ? "Confident" : "Low Confidence"}</p>
                      </div>
                    )}
                    </div>

                    {/* Template ID */}
                    {(currentResult.template_id || currentResult.cache_entry_id) && (
                      <div>
                        <h4 className="font-semibold text-sm mb-1">Template ID</h4>
                        <SimpleCacheTooltip
                          content={
                            <div>
                              {currentResult.user_query && (
                                <>
                                  <p className="text-xs text-neutral-400 mb-1">Query:</p>
                                  <p className="mb-2 text-neutral-200 whitespace-pre-wrap">{currentResult.user_query}</p>
                                </>
                              )}
                              <p className="text-xs text-neutral-400 mb-1">Template:</p>
                              <pre className="bg-neutral-800 p-2 rounded text-neutral-300 whitespace-pre-wrap overflow-auto max-h-[150px]">
                                {currentResult.updated_template || currentResult.cache_template}
                              </pre>
                              <p className="text-center text-blue-400 mt-2 text-xs">Click to view full details</p>
                            </div>
                          }
                        >
                          <Link
                            to={`/cache-entries/${currentResult.template_id ?? currentResult.cache_entry_id}`}
                            target="_blank"
                            className="text-blue-400 hover:underline"
                          >
                            {currentResult.template_id ?? currentResult.cache_entry_id}
                          </Link>
                        </SimpleCacheTooltip>
                      </div>
                    )}

                    
                  </div>
                </TabsContent>

                <TabsContent value="score" className="space-y-4 pt-2">
                  <div className="p-4 border border-neutral-700 rounded-md bg-[#18192a] text-neutral-200 overflow-auto max-h-[300px]">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h4 className="font-semibold text-sm mb-1">User Query</h4>
                        <p>{currentResult.user_query}</p>
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
                      {currentResult.similarity_score !== undefined && (
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Similarity Score</h4>
                          <p>{(currentResult.similarity_score * 100).toFixed(2)}%</p>
                        </div>
                      )}
                      {currentResult.is_confident !== undefined && (
                        <div>
                          <h4 className="font-semibold text-sm mb-1">Is Confident</h4>
                          <p>{currentResult.is_confident ? "Yes" : "No"}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
} 