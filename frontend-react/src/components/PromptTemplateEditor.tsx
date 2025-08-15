import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Eye, EyeOff, Lightbulb } from "lucide-react";

interface PromptTemplateEditorProps {
  value: string;
  onChange: (value: string) => void;
  parameters: string[];
  placeholder?: string;
  readOnly?: boolean;
  showPreview?: boolean;
  sampleValues?: Record<string, string>;
  suggestions?: string[];
}

const PROMPT_SUGGESTIONS = [
  "Analyze the following {content} and provide a summary",
  "Classify this {text} into one of these categories: {categories}",
  "Extract the key information from {input} and format as JSON",
  "Based on {context}, generate a response to {question}",
  "Review {data} and identify any issues or concerns",
  "Compare {item_a} and {item_b} and explain the differences"
];

export function PromptTemplateEditor({
  value,
  onChange,
  parameters,
  placeholder = "Enter your prompt template with {parameter} placeholders...",
  readOnly = false,
  showPreview = true,
  sampleValues = {},
  suggestions = PROMPT_SUGGESTIONS
}: PromptTemplateEditorProps) {
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [previewText, setPreviewText] = useState("");

  // Generate preview text by replacing parameters with sample values
  useEffect(() => {
    let preview = value;
    parameters.forEach(param => {
      const sampleValue = sampleValues[param] || `[${param}]`;
      const regex = new RegExp(`\\{${param}\\}`, 'g');
      preview = preview.replace(regex, sampleValue);
    });
    setPreviewText(preview);
  }, [value, parameters, sampleValues]);

  const insertSuggestion = (suggestion: string) => {
    if (readOnly) return;
    
    const textarea = document.getElementById("prompt-template") as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = value.substring(0, start) + suggestion + value.substring(end);
      onChange(newValue);
      
      // Set cursor position after inserted text
      setTimeout(() => {
        textarea.setSelectionRange(start + suggestion.length, start + suggestion.length);
        textarea.focus();
      }, 0);
    }
  };

  const insertParameter = (param: string) => {
    if (readOnly) return;
    
    const paramPlaceholder = `{${param}}`;
    const textarea = document.getElementById("prompt-template") as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = value.substring(0, start) + paramPlaceholder + value.substring(end);
      onChange(newValue);
      
      // Set cursor position after inserted parameter
      setTimeout(() => {
        textarea.setSelectionRange(start + paramPlaceholder.length, start + paramPlaceholder.length);
        textarea.focus();
      }, 0);
    }
  };

  const getParameterUsage = () => {
    const usedParams = new Set<string>();
    const unusedParams = new Set(parameters);
    
    parameters.forEach(param => {
      const regex = new RegExp(`\\{${param}\\}`, 'g');
      if (regex.test(value)) {
        usedParams.add(param);
        unusedParams.delete(param);
      }
    });
    
    return { used: Array.from(usedParams), unused: Array.from(unusedParams) };
  };

  const { used: usedParams, unused: unusedParams } = getParameterUsage();

  return (
    <div className="space-y-4">
      {/* Parameter Helper */}
      {parameters.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Available Parameters</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-3">
              <div className="flex flex-wrap gap-1">
                {usedParams.map(param => (
                  <Badge
                    key={param}
                    variant="default"
                    className="cursor-pointer hover:bg-primary/80"
                    onClick={() => !readOnly && insertParameter(param)}
                  >
                    {param} ✓
                  </Badge>
                ))}
                {unusedParams.map(param => (
                  <Badge
                    key={param}
                    variant="outline"
                    className={`${!readOnly ? 'cursor-pointer hover:bg-muted' : ''}`}
                    onClick={() => !readOnly && insertParameter(param)}
                  >
                    {param}
                  </Badge>
                ))}
              </div>
              {unusedParams.length > 0 && (
                <div className="text-xs text-muted-foreground">
                  Click unused parameters to insert them into your prompt
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Editor */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Prompt Template</CardTitle>
            {showPreview && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsPreviewMode(!isPreviewMode)}
                className="flex items-center gap-1"
              >
                {isPreviewMode ? <EyeOff size={14} /> : <Eye size={14} />}
                {isPreviewMode ? "Edit" : "Preview"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {isPreviewMode ? (
            <div className="space-y-2">
              <Label>Preview (with sample values)</Label>
              <div className="p-3 bg-muted rounded-md whitespace-pre-wrap font-mono text-sm min-h-[120px]">
                {previewText || "Enter a prompt template to see preview..."}
              </div>
              <div className="text-xs text-muted-foreground">
                Parameters are replaced with sample values or placeholders
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Textarea
                id="prompt-template"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                readOnly={readOnly}
                rows={6}
                className="font-mono"
              />
              <div className="text-xs text-muted-foreground">
                Use {parameters.length > 0 ? `{${parameters.join('}, {')}` : '{parameter_name}'} syntax for dynamic values
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Suggestions */}
      {!readOnly && suggestions.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-1">
              <Lightbulb size={14} />
              Prompt Suggestions
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2">
              {suggestions.slice(0, 4).map((suggestion, index) => (
                <div key={index} className="group">
                  <Button
                    variant="ghost"
                    className="w-full text-left justify-start h-auto p-2 text-xs hover:bg-muted"
                    onClick={() => insertSuggestion(suggestion)}
                  >
                    <div className="truncate group-hover:whitespace-normal group-hover:overflow-visible">
                      {suggestion}
                    </div>
                  </Button>
                </div>
              ))}
              <div className="text-xs text-muted-foreground">
                Click to insert suggestion at cursor position
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Validation Messages */}
      {value && (
        <div className="space-y-1">
          {unusedParams.length > 0 && (
            <div className="text-xs text-amber-600">
              ⚠️ Unused parameters: {unusedParams.join(', ')}
            </div>
          )}
          {!value.includes('{') && parameters.length > 0 && (
            <div className="text-xs text-amber-600">
              ⚠️ No parameter placeholders found in prompt
            </div>
          )}
          {value.length > 2000 && (
            <div className="text-xs text-amber-600">
              ⚠️ Prompt is quite long ({value.length} chars) - consider simplifying
            </div>
          )}
        </div>
      )}
    </div>
  );
}