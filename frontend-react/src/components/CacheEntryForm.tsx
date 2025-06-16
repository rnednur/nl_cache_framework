import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./ui/card";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import React from "react";
// import WorkflowBuilder if/when available

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
  tags: string[] | null;
  addTag?: (tag: string) => void;
  removeTag?: (tag: string) => void;
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
                <SelectItem value="dsl">DSL Components</SelectItem>
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
          <Textarea
            id="template"
            placeholder="Enter template content"
            className="min-h-[100px]"
            value={template}
            onChange={setTemplate ? (e) => setTemplate(e.target.value) : undefined}
            disabled={readOnly}
          />
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
            {tags && Array.isArray(tags) && tags.map((tag, index) => (
              <div key={`tag-${index}-${tag}`} className="flex items-center gap-1 bg-secondary text-secondary-foreground px-3 py-1 rounded-full text-sm">
                {tag}
                {!readOnly && removeTag && (
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    className="text-secondary-foreground/70 hover:text-secondary-foreground"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {!readOnly && (
              <div className="flex items-center">
                <Input
                  id="tag-input"
                  placeholder="Add tag..."
                  value={tagNameInput || ""}
                  onChange={setTagNameInput ? (e) => setTagNameInput(e.target.value) : undefined}
                  onKeyDown={handleKeyDown}
                  className="w-40 h-8 px-2 py-1"
                  disabled={readOnly}
                />
                {addTag && (
                  <button
                    type="button"
                    onClick={() => addTag(tagNameInput || "")}
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