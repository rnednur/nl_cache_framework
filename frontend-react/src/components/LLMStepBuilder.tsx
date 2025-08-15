import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Label } from "./ui/label";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Badge } from "./ui/badge";
import { Alert } from "./ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Plus, X, TestTube, Save, Copy } from "lucide-react";
import api from "../services/api";

interface LLMStepConfig {
  prompt_template: string;
  input_parameters: string[];
  output_format: "json" | "text" | "structured";
  expected_output: Record<string, any>;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt?: string;
}

interface ValidationRules {
  required_fields: string[];
  validation_schema: Record<string, any>;
  fallback_handling: {
    on_validation_error: "retry" | "fallback" | "fail";
    max_retries: number;
    fallback_response: Record<string, any>;
  };
}

interface LLMStepBuilderProps {
  onSave?: (stepData: any) => void;
  onTest?: (stepData: any) => void;
  initialData?: any;
  readOnly?: boolean;
}

const TEMPLATE_OPTIONS = [
  {
    id: "support_ticket_classifier",
    name: "Support Ticket Classifier",
    description: "Analyze support tickets and classify their urgency level"
  },
  {
    id: "sentiment_analyzer", 
    name: "Sentiment Analyzer",
    description: "Analyze text sentiment and provide confidence scores"
  },
  {
    id: "content_summarizer",
    name: "Content Summarizer", 
    description: "Generate concise summaries of long text content"
  },
  {
    id: "entity_extractor",
    name: "Entity Extractor",
    description: "Extract named entities from text (people, places, organizations, etc.)"
  }
];

const MODEL_OPTIONS = [
  "google/gemini-pro",
  "openai/gpt-4",
  "openai/gpt-3.5-turbo",
  "anthropic/claude-3-sonnet",
  "anthropic/claude-3-haiku"
];

export function LLMStepBuilder({ onSave, onTest, initialData, readOnly = false }: LLMStepBuilderProps) {
  const [nlQuery, setNlQuery] = useState(initialData?.nl_query || "");
  const [config, setConfig] = useState<LLMStepConfig>({
    prompt_template: initialData?.prompt_template || "",
    input_parameters: initialData?.input_parameters || [],
    output_format: initialData?.output_format || "json",
    expected_output: initialData?.expected_output || {},
    model: initialData?.model || "google/gemini-pro",
    temperature: initialData?.temperature || 0.3,
    max_tokens: initialData?.max_tokens || 500,
    system_prompt: initialData?.system_prompt || ""
  });

  const [validationRules, setValidationRules] = useState<ValidationRules>({
    required_fields: [],
    validation_schema: {},
    fallback_handling: {
      on_validation_error: "fallback",
      max_retries: 2,
      fallback_response: {}
    }
  });

  const [newParameter, setNewParameter] = useState("");
  const [newOutputField, setNewOutputField] = useState({ name: "", type: "string" });
  const [testInputs, setTestInputs] = useState<Record<string, string>>({});
  const [testResult, setTestResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load template when user selects one
  const loadTemplate = async (templateId: string) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await api.get('/v1/llm-steps/templates');
      const template = response.data.templates[templateId];
      
      if (template) {
        const stepConfig = template.template.step_config;
        setConfig({
          prompt_template: stepConfig.prompt_template,
          input_parameters: stepConfig.input_parameters,
          output_format: stepConfig.output_format,
          expected_output: stepConfig.expected_output,
          model: stepConfig.model,
          temperature: stepConfig.temperature,
          max_tokens: stepConfig.max_tokens,
          system_prompt: stepConfig.system_prompt || ""
        });
        
        if (template.template.validation_rules) {
          setValidationRules(template.template.validation_rules);
        }
        
        setNlQuery(template.description);
      }
    } catch (err) {
      setError(`Error loading template: ${err}`);
    } finally {
      setIsLoading(false);
    }
  };

  const addParameter = () => {
    if (newParameter && !config.input_parameters.includes(newParameter)) {
      setConfig(prev => ({
        ...prev,
        input_parameters: [...prev.input_parameters, newParameter]
      }));
      setNewParameter("");
    }
  };

  const removeParameter = (param: string) => {
    setConfig(prev => ({
      ...prev,
      input_parameters: prev.input_parameters.filter(p => p !== param)
    }));
    
    // Remove from test inputs too
    const newTestInputs = { ...testInputs };
    delete newTestInputs[param];
    setTestInputs(newTestInputs);
  };

  const addOutputField = () => {
    if (newOutputField.name && !config.expected_output[newOutputField.name]) {
      setConfig(prev => ({
        ...prev,
        expected_output: {
          ...prev.expected_output,
          [newOutputField.name]: newOutputField.type
        }
      }));
      setNewOutputField({ name: "", type: "string" });
    }
  };

  const removeOutputField = (fieldName: string) => {
    setConfig(prev => {
      const newOutput = { ...prev.expected_output };
      delete newOutput[fieldName];
      return { ...prev, expected_output: newOutput };
    });
  };

  const testStep = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // First create a temporary LLM step
      const stepData = {
        nl_query: nlQuery,
        prompt_template: config.prompt_template,
        input_parameters: config.input_parameters,
        output_format: config.output_format,
        expected_output: config.expected_output,
        model: config.model,
        temperature: config.temperature,
        max_tokens: config.max_tokens,
        system_prompt: config.system_prompt,
        validation_rules: validationRules
      };
      
      const createResponse = await api.post('/v1/llm-steps/create', stepData);
      const stepId = createResponse.data.id;
      
      // Test the step with inputs
      const testResponse = await api.post(`/v1/llm-steps/${stepId}/test`, {
        test_inputs: testInputs
      });
      
      setTestResult(testResponse.data);
      
      if (onTest) {
        onTest({ stepId, testResult: testResponse.data });
      }
    } catch (err: any) {
      setError(`Test failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const saveStep = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const stepData = {
        nl_query: nlQuery,
        prompt_template: config.prompt_template,
        input_parameters: config.input_parameters,
        output_format: config.output_format,
        expected_output: config.expected_output,
        model: config.model,
        temperature: config.temperature,
        max_tokens: config.max_tokens,
        system_prompt: config.system_prompt,
        validation_rules: validationRules
      };
      
      const response = await api.post('/v1/llm-steps/create', stepData);
      
      if (onSave) {
        onSave(response.data);
      }
    } catch (err: any) {
      setError(`Save failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Update test inputs when parameters change
  useEffect(() => {
    const newTestInputs = { ...testInputs };
    config.input_parameters.forEach(param => {
      if (!newTestInputs[param]) {
        newTestInputs[param] = "";
      }
    });
    setTestInputs(newTestInputs);
  }, [config.input_parameters]);

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <div>{error}</div>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>LLM Step Builder</CardTitle>
          <CardDescription>
            Create custom LLM-powered steps for your recipes
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Template Selection */}
          <div className="space-y-2">
            <Label>Load Template (Optional)</Label>
            <Select onValueChange={loadTemplate} disabled={readOnly}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a template to start with" />
              </SelectTrigger>
              <SelectContent>
                {TEMPLATE_OPTIONS.map(template => (
                  <SelectItem key={template.id} value={template.id}>
                    <div>
                      <div className="font-medium">{template.name}</div>
                      <div className="text-sm text-muted-foreground">{template.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Step Description */}
          <div className="space-y-2">
            <Label htmlFor="nlQuery">Step Description *</Label>
            <Textarea
              id="nlQuery"
              placeholder="Describe what this LLM step should do (e.g., 'Analyze the issue and classify it into buckets')"
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              readOnly={readOnly}
              rows={2}
            />
          </div>

          <Tabs defaultValue="config" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="config">Configuration</TabsTrigger>
              <TabsTrigger value="prompt">Prompt</TabsTrigger>
              <TabsTrigger value="validation">Validation</TabsTrigger>
              <TabsTrigger value="test">Test</TabsTrigger>
            </TabsList>

            {/* Configuration Tab */}
            <TabsContent value="config" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="model">Model</Label>
                  <Select 
                    value={config.model} 
                    onValueChange={(value) => setConfig(prev => ({ ...prev, model: value }))}
                    disabled={readOnly}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS.map(model => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="outputFormat">Output Format</Label>
                  <Select 
                    value={config.output_format} 
                    onValueChange={(value: "json" | "text" | "structured") => 
                      setConfig(prev => ({ ...prev, output_format: value }))
                    }
                    disabled={readOnly}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="json">JSON</SelectItem>
                      <SelectItem value="text">Text</SelectItem>
                      <SelectItem value="structured">Structured</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="temperature">Temperature: {config.temperature}</Label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={config.temperature}
                    onChange={(e) => setConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                    disabled={readOnly}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxTokens">Max Tokens</Label>
                  <Input
                    id="maxTokens"
                    type="number"
                    value={config.max_tokens}
                    onChange={(e) => setConfig(prev => ({ ...prev, max_tokens: parseInt(e.target.value) }))}
                    readOnly={readOnly}
                    min={50}
                    max={4000}
                  />
                </div>
              </div>

              {/* Input Parameters */}
              <div className="space-y-3">
                <Label>Input Parameters</Label>
                <div className="flex flex-wrap gap-2">
                  {config.input_parameters.map(param => (
                    <Badge key={param} variant="secondary" className="flex items-center gap-1">
                      {param}
                      {!readOnly && (
                        <button
                          onClick={() => removeParameter(param)}
                          className="ml-1 hover:bg-red-200 rounded-full p-0.5"
                        >
                          <X size={12} />
                        </button>
                      )}
                    </Badge>
                  ))}
                </div>
                {!readOnly && (
                  <div className="flex gap-2">
                    <Input
                      placeholder="Parameter name (e.g., issue_text)"
                      value={newParameter}
                      onChange={(e) => setNewParameter(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && addParameter()}
                    />
                    <Button onClick={addParameter} size="sm" variant="outline">
                      <Plus size={16} />
                    </Button>
                  </div>
                )}
              </div>

              {/* Expected Output */}
              <div className="space-y-3">
                <Label>Expected Output Fields</Label>
                <div className="space-y-2">
                  {Object.entries(config.expected_output).map(([field, type]) => (
                    <div key={field} className="flex items-center gap-2 p-2 border rounded">
                      <span className="font-medium">{field}</span>
                      <Badge variant="outline">{String(type)}</Badge>
                      {!readOnly && (
                        <button
                          onClick={() => removeOutputField(field)}
                          className="ml-auto hover:bg-red-200 rounded-full p-1"
                        >
                          <X size={12} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                {!readOnly && (
                  <div className="flex gap-2">
                    <Input
                      placeholder="Field name"
                      value={newOutputField.name}
                      onChange={(e) => setNewOutputField(prev => ({ ...prev, name: e.target.value }))}
                    />
                    <Select
                      value={newOutputField.type}
                      onValueChange={(value) => setNewOutputField(prev => ({ ...prev, type: value }))}
                    >
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="string">string</SelectItem>
                        <SelectItem value="number">number</SelectItem>
                        <SelectItem value="boolean">boolean</SelectItem>
                        <SelectItem value="array">array</SelectItem>
                        <SelectItem value="object">object</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button onClick={addOutputField} size="sm" variant="outline">
                      <Plus size={16} />
                    </Button>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Prompt Tab */}
            <TabsContent value="prompt" className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="systemPrompt">System Prompt (Optional)</Label>
                <Textarea
                  id="systemPrompt"
                  placeholder="System-level instructions for the LLM (e.g., 'You are a customer support expert...')"
                  value={config.system_prompt}
                  onChange={(e) => setConfig(prev => ({ ...prev, system_prompt: e.target.value }))}
                  readOnly={readOnly}
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="promptTemplate">Prompt Template *</Label>
                <Textarea
                  id="promptTemplate"
                  placeholder="Enter your prompt with {parameter} placeholders (e.g., 'Analyze this text: {text} and classify it as...')"
                  value={config.prompt_template}
                  onChange={(e) => setConfig(prev => ({ ...prev, prompt_template: e.target.value }))}
                  readOnly={readOnly}
                  rows={8}
                  className="font-mono"
                />
                <div className="text-sm text-muted-foreground">
                  Use curly braces to reference input parameters: {config.input_parameters.map(p => `{${p}}`).join(', ')}
                </div>
              </div>
            </TabsContent>

            {/* Validation Tab */}
            <TabsContent value="validation" className="space-y-4">
              <div className="text-sm text-muted-foreground">
                Configure validation rules and error handling for the LLM output.
              </div>
              
              <div className="space-y-2">
                <Label>Error Handling</Label>
                <Select
                  value={validationRules.fallback_handling.on_validation_error}
                  onValueChange={(value: "retry" | "fallback" | "fail") =>
                    setValidationRules(prev => ({
                      ...prev,
                      fallback_handling: { ...prev.fallback_handling, on_validation_error: value }
                    }))
                  }
                  disabled={readOnly}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="retry">Retry on error</SelectItem>
                    <SelectItem value="fallback">Use fallback response</SelectItem>
                    <SelectItem value="fail">Fail on error</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxRetries">Max Retries</Label>
                <Input
                  id="maxRetries"
                  type="number"
                  value={validationRules.fallback_handling.max_retries}
                  onChange={(e) => setValidationRules(prev => ({
                    ...prev,
                    fallback_handling: { ...prev.fallback_handling, max_retries: parseInt(e.target.value) }
                  }))}
                  readOnly={readOnly}
                  min={0}
                  max={5}
                />
              </div>
            </TabsContent>

            {/* Test Tab */}
            <TabsContent value="test" className="space-y-4">
              <div className="text-sm text-muted-foreground">
                Test your LLM step with sample inputs to validate the configuration.
              </div>

              {/* Test Inputs */}
              <div className="space-y-3">
                <Label>Test Inputs</Label>
                {config.input_parameters.map(param => (
                  <div key={param} className="space-y-1">
                    <Label htmlFor={`test-${param}`}>{param}</Label>
                    <Input
                      id={`test-${param}`}
                      placeholder={`Enter value for ${param}`}
                      value={testInputs[param] || ""}
                      onChange={(e) => setTestInputs(prev => ({ ...prev, [param]: e.target.value }))}
                      disabled={readOnly}
                    />
                  </div>
                ))}
              </div>

              <Button
                onClick={testStep}
                disabled={isLoading || readOnly || !config.prompt_template || config.input_parameters.length === 0}
                className="w-full"
              >
                <TestTube className="mr-2" size={16} />
                {isLoading ? "Testing..." : "Test LLM Step"}
              </Button>

              {/* Test Results */}
              {testResult && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Test Results</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div>
                        <Badge variant={testResult.success ? "default" : "destructive"}>
                          {testResult.success ? "Success" : "Failed"}
                        </Badge>
                        {testResult.validation_passed !== undefined && (
                          <Badge variant={testResult.validation_passed ? "default" : "secondary"} className="ml-2">
                            Validation: {testResult.validation_passed ? "Passed" : "Failed"}
                          </Badge>
                        )}
                      </div>

                      {testResult.output && (
                        <div>
                          <Label>Output:</Label>
                          <pre className="mt-1 p-3 bg-muted rounded text-sm overflow-auto">
                            {JSON.stringify(testResult.output, null, 2)}
                          </pre>
                        </div>
                      )}

                      {testResult.raw_response && (
                        <div>
                          <Label>Raw LLM Response:</Label>
                          <pre className="mt-1 p-3 bg-muted rounded text-sm overflow-auto">
                            {testResult.raw_response}
                          </pre>
                        </div>
                      )}

                      {testResult.error_message && (
                        <div>
                          <Label>Error:</Label>
                          <div className="mt-1 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                            {testResult.error_message}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      {!readOnly && (
        <div className="flex gap-2">
          <Button
            onClick={saveStep}
            disabled={isLoading || !nlQuery || !config.prompt_template}
            className="flex items-center gap-2"
          >
            <Save size={16} />
            Save LLM Step
          </Button>
          
          <Button
            variant="outline"
            onClick={() => {
              const stepJson = JSON.stringify({
                nl_query: nlQuery,
                step_config: config,
                validation_rules: validationRules
              }, null, 2);
              navigator.clipboard.writeText(stepJson);
            }}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            <Copy size={16} />
            Copy JSON
          </Button>
        </div>
      )}
    </div>
  );
}