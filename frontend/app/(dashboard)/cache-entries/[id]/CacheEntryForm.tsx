import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../../components/ui/card";
import { Label } from "../../../components/ui/label";
import { Button } from "../../../components/ui/button";
import React from "react";
import WorkflowBuilder from "../../../../components/ui/WorkflowBuilder";

interface CacheEntryFormProps {
  nlQuery: string;
  setNlQuery?: (v: string) => void;
  template: string;
  setTemplate?: (v: string) => void;
  templateType: string;
  setTemplateType?: (v: string) => void;
  reasoningTrace: string;
  setReasoningTrace?: (v: string) => void;
  catalogType?: string;
  setCatalogType?: (v: string | undefined) => void;
  catalogSubtype?: string;
  setCatalogSubtype?: (v: string | undefined) => void;
  catalogName?: string;
  setCatalogName?: (v: string | undefined) => void;
  status: string;
  setStatus?: (v: string) => void;
  tags: Record<string, string[]>;
  addTag?: (name: string, value: string) => void;
  removeTag?: (name: string, value: string) => void;
  tagNameInput?: string;
  setTagNameInput?: (v: string) => void;
  tagValueInput?: string;
  setTagValueInput?: (v: string) => void;
  handleKeyDown?: (e: React.KeyboardEvent) => void;
  error?: string | null;
  readOnly?: boolean;
  children?: React.ReactNode;
  onGenerateReasoning?: () => void;
  isGeneratingReasoning?: boolean;
}

export function CacheEntryForm({
  nlQuery,
  setNlQuery,
  template,
  setTemplate,
  templateType,
  setTemplateType,
  reasoningTrace,
  setReasoningTrace,
  catalogType,
  setCatalogType,
  catalogSubtype,
  setCatalogSubtype,
  catalogName,
  setCatalogName,
  status,
  setStatus,
  tags,
  addTag,
  removeTag,
  tagNameInput,
  setTagNameInput,
  tagValueInput,
  setTagValueInput,
  handleKeyDown,
  error,
  readOnly,
  children,
  onGenerateReasoning,
  isGeneratingReasoning,
}: CacheEntryFormProps) {
  return (
    <Card className="w-full border-0 shadow-none">
      <CardContent className="p-4 space-y-8">
        <div className="grid gap-6 md:grid-cols-3">
          <div className="grid gap-2">
            <Label htmlFor="catalogType">Catalog Type</Label>
            <Input
              id="catalogType"
              placeholder="Enter catalog type"
              value={catalogType || ""}
              onChange={setCatalogType ? (e) => setCatalogType(e.target.value ? e.target.value : undefined) : undefined}
              disabled={readOnly}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="catalogSubtype">Catalog Subtype</Label>
            <Input
              id="catalogSubtype"
              placeholder="Enter catalog subtype"
              value={catalogSubtype || ""}
              onChange={setCatalogSubtype ? (e) => setCatalogSubtype(e.target.value ? e.target.value : undefined) : undefined}
              disabled={readOnly}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="catalogName">Catalog Name</Label>
            <Input
              id="catalogName"
              placeholder="Enter catalog name"
              value={catalogName || ""}
              onChange={setCatalogName ? (e) => setCatalogName(e.target.value ? e.target.value : undefined) : undefined}
              disabled={readOnly}
            />
          </div>
        </div>
        
        <div className="grid gap-2">
          <Label htmlFor="nl-query">Natural Language Query</Label>
          <Input
            id="nl-query"
            placeholder="Enter natural language query"
            value={nlQuery}
            onChange={setNlQuery ? (e) => setNlQuery(e.target.value) : undefined}
            disabled={readOnly}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="template-type">Template Type</Label>
            <Select
              value={templateType}
              onValueChange={setTemplateType}
              disabled={readOnly}
            >
              <SelectTrigger id="template-type">
                <SelectValue placeholder="Select template type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sql">SQL</SelectItem>
                <SelectItem value="url">URL</SelectItem>
                <SelectItem value="api">API</SelectItem>
                <SelectItem value="workflow">Workflow</SelectItem>
                <SelectItem value="graphql">GraphQL</SelectItem>
                <SelectItem value="regex">Regex</SelectItem>
                <SelectItem value="script">Script</SelectItem>
                <SelectItem value="nosql">NoSQL</SelectItem>
                <SelectItem value="cli">CLI</SelectItem>
                <SelectItem value="prompt">Prompt</SelectItem>
                <SelectItem value="configuration">Configuration</SelectItem>
                <SelectItem value="reasoning_steps">Reasoning Steps</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="status">Status</Label>
            <Select
              value={status}
              onValueChange={setStatus}
              disabled={readOnly}
            >
              <SelectTrigger id="status">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="archive">Archive</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="template">Template</Label>
          {templateType === 'api' ? (
            <Textarea
              id="template"
              placeholder="Enter API template content in JSON format"
              className="min-h-[100px] font-mono text-sm"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'sql' ? (
            <Textarea
              id="template"
              placeholder="e.g., SELECT * FROM users WHERE signup_date >= '{{start_date}}' AND signup_date <= '{{end_date}}'"
              className="min-h-[100px] font-mono text-sm"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'url' ? (
            <Input
              id="template"
              placeholder="e.g., https://example.com/data?param={{value}}"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'workflow' ? (
            <div className="space-y-2">
              <Textarea
                id="template"
                placeholder='e.g., {\n  "steps": [\n    {\n      "type": "api",\n      "url": "https://api.example.com/step1"\n    },\n    {\n      "type": "transform",\n      "operation": "filter"\n    }\n  ]\n}'
                className="min-h-[100px] font-mono text-sm"
                value={template}
                onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
                disabled={readOnly}
              />
              {templateType === 'workflow' && !readOnly && (
                <p className="text-sm text-muted-foreground mt-1">
                  Define the workflow visually using the builder below. The JSON template will be updated.
                </p>
              )}
              {templateType === 'workflow' && !readOnly && (
                <div className="mt-4">
                  <WorkflowBuilder
                    catalogType={catalogType || undefined}
                    catalogSubType={catalogSubtype || undefined}
                    catalogName={catalogName || undefined}
                    initialNodes={(() => {
                      try {
                        if (!template) return undefined;
                        const parsed = JSON.parse(template);
                        return Array.isArray(parsed.nodes) ? parsed.nodes : undefined;
                      } catch (e) {
                        return undefined; // Or provide default nodes
                      }
                    })()}
                    initialEdges={(() => {
                      try {
                        if (!template) return undefined;
                        const parsed = JSON.parse(template);
                        return Array.isArray(parsed.edges) ? parsed.edges : undefined;
                      } catch (e) {
                        return undefined; // Or provide default edges
                      }
                    })()}
                    onWorkflowChange={(nodes, edges) => {
                      if (setTemplate) {
                        // Update the main template state with the workflow structure
                        setTemplate(JSON.stringify({ nodes, edges }, null, 2));
                      }
                    }}
                  />
                </div>
              )}
              {templateType === 'workflow' && template.trim() && !readOnly && (() => {
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
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'regex' ? (
            <Input
              id="template"
              placeholder="e.g., \d{4}-\d{2}-\d{2}"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'script' ? (
            <div className="space-y-2">
              <Textarea
                id="template"
                placeholder='e.g., {\n  "language": "javascript",\n  "code": "function transform(data) { return data.filter(d => d.active); }"\n}'
                className="min-h-[200px] font-mono text-sm"
                value={template}
                onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
                disabled={readOnly}
              />
              {templateType === 'script' && !readOnly && (
                <p className="text-sm text-muted-foreground mt-1">
                  For script templates, include visualization details in JSON format (e.g., visualization_type, script).
                </p>
              )}
              {templateType === 'script' && template.trim() && !readOnly && (() => {
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
              placeholder='e.g., {\n  "collection": "users",\n  "query": { "status": "active" },\n  "projection": { "name": 1, "email": 1 }\n}'
              className="min-h-[100px] font-mono text-sm"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'cli' ? (
            <Input
              id="template"
              placeholder="e.g., grep '{{search_term}}' /var/log/*.log"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'prompt' ? (
            <Textarea
              id="template"
              placeholder="e.g., Translate the following text to {{language}}: '{{text}}'"
              className="min-h-[100px] font-mono text-sm"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          ) : templateType === 'configuration' ? (
            <div className="space-y-2">
              <Textarea
                id="template"
                placeholder='e.g., {\n  "settings": {\n    "timeout": 30,\n    "retries": 3\n  },\n  "parameters": {\n    "key": "{{api_key}}"\n  }\n}'
                className="min-h-[200px] font-mono text-sm"
                value={template}
                onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
                disabled={readOnly}
              />
              {templateType === 'configuration' && template.trim() && !readOnly && (() => {
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
              className="min-h-[100px]"
              value={template}
              onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
              disabled={readOnly}
            />
          )}
        </div>

        <div className="grid gap-2">
          <Label htmlFor="reasoning">Reasoning Trace</Label>
          <div className="flex gap-2">
            <Textarea
              id="reasoning"
              placeholder="Explain how this template relates to the query..."
              className="min-h-[100px] flex-1"
              value={reasoningTrace}
              onChange={setReasoningTrace ? (e) => setReasoningTrace(e.target.value) : undefined}
              disabled={readOnly}
            />
            {!readOnly && setReasoningTrace && (
              <Button 
                type="button" 
                className="h-10 whitespace-nowrap" 
                variant="outline"
                onClick={onGenerateReasoning}
                disabled={!nlQuery.trim() || !template.trim() || isGeneratingReasoning}
              >
                {isGeneratingReasoning ? (
                  <>
                    <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"></span>
                    Generating...
                  </>
                ) : (
                  "Generate with AI"
                )}
              </Button>
            )}
          </div>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="entity-substitution">Entity Substitution</Label>
          <Textarea
            id="entity-substitution"
            placeholder={!readOnly ? 'e.g., { "city": "New York", "start_date": "2023-01-01" }' : ''}
            className="min-h-[100px] font-mono text-sm"
            disabled={readOnly}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="tags">Tags</Label>
          <div className="flex flex-wrap gap-2">
            {Object.entries(tags || {}).map(([name, values]) => (
              <div key={name} className="flex items-center gap-1 bg-secondary text-secondary-foreground px-3 py-1 rounded-full text-sm">
                {name}
                {Array.isArray(values) ? values.map((value) => (
                  <div key={`${name}-${value}`} className="flex items-center gap-1 bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full text-sm">
                    {value}
                    {!readOnly && removeTag && (
                      <button
                        type="button"
                        onClick={() => removeTag(name, value)}
                        className="text-secondary-foreground/70 hover:text-secondary-foreground"
                      >
                        ×
                      </button>
                    )}
                  </div>
                )) : null}
              </div>
            ))}
            {!readOnly && (
              <div className="flex items-center">
                <Input
                  id="tag-name-input"
                  placeholder="Add tag name..."
                  value={tagNameInput || ""}
                  onChange={setTagNameInput ? (e) => setTagNameInput(e.target.value) : undefined}
                  onKeyDown={handleKeyDown}
                  className="w-28 h-8 px-2 py-1"
                  disabled={readOnly}
                />
                <Input
                  id="tag-value-input"
                  placeholder="Add tag value..."
                  value={tagValueInput || ""}
                  onChange={setTagValueInput ? (e) => setTagValueInput(e.target.value) : undefined}
                  onKeyDown={handleKeyDown}
                  className="w-28 h-8 px-2 py-1"
                  disabled={readOnly}
                />
                {addTag && (
                  <button
                    type="button"
                    onClick={() => addTag(tagNameInput || "", tagValueInput || "")}
                    className="ml-2 text-sm text-primary hover:text-primary/80"
                  >
                    Add
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
      {children}
    </Card>
  );
} 