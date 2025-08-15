import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Label } from "./ui/label";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Badge } from "./ui/badge";
import { Plus, X, ArrowRight } from "lucide-react";

interface Parameter {
  name: string;
  type: string;
  required?: boolean;
  description?: string;
  default_value?: any;
}

interface ParameterMapperProps {
  inputParameters: Parameter[];
  outputParameters: Parameter[];
  onInputParametersChange: (params: Parameter[]) => void;
  onOutputParametersChange: (params: Parameter[]) => void;
  readOnly?: boolean;
  showMapping?: boolean;
  parameterMapping?: Record<string, string>;
  onMappingChange?: (mapping: Record<string, string>) => void;
}

const PARAMETER_TYPES = [
  { value: "string", label: "Text (string)" },
  { value: "number", label: "Number" },
  { value: "boolean", label: "Boolean (true/false)" },
  { value: "array", label: "List (array)" },
  { value: "object", label: "Object (JSON)" },
  { value: "date", label: "Date" },
  { value: "email", label: "Email" },
  { value: "url", label: "URL" }
];

export function ParameterMapper({
  inputParameters,
  outputParameters,
  onInputParametersChange,
  onOutputParametersChange,
  readOnly = false,
  showMapping = false,
  parameterMapping = {},
  onMappingChange
}: ParameterMapperProps) {
  const [newInputParam, setNewInputParam] = useState<Partial<Parameter>>({
    name: "",
    type: "string",
    required: true,
    description: ""
  });

  const [newOutputParam, setNewOutputParam] = useState<Partial<Parameter>>({
    name: "",
    type: "string",
    description: ""
  });

  const addInputParameter = () => {
    if (newInputParam.name && !inputParameters.some(p => p.name === newInputParam.name)) {
      onInputParametersChange([
        ...inputParameters,
        {
          name: newInputParam.name,
          type: newInputParam.type || "string",
          required: newInputParam.required !== false,
          description: newInputParam.description || ""
        }
      ]);
      setNewInputParam({ name: "", type: "string", required: true, description: "" });
    }
  };

  const removeInputParameter = (name: string) => {
    onInputParametersChange(inputParameters.filter(p => p.name !== name));
  };

  const updateInputParameter = (name: string, updates: Partial<Parameter>) => {
    onInputParametersChange(
      inputParameters.map(p => p.name === name ? { ...p, ...updates } : p)
    );
  };

  const addOutputParameter = () => {
    if (newOutputParam.name && !outputParameters.some(p => p.name === newOutputParam.name)) {
      onOutputParametersChange([
        ...outputParameters,
        {
          name: newOutputParam.name,
          type: newOutputParam.type || "string",
          description: newOutputParam.description || ""
        }
      ]);
      setNewOutputParam({ name: "", type: "string", description: "" });
    }
  };

  const removeOutputParameter = (name: string) => {
    onOutputParametersChange(outputParameters.filter(p => p.name !== name));
  };

  const updateOutputParameter = (name: string, updates: Partial<Parameter>) => {
    onOutputParametersChange(
      outputParameters.map(p => p.name === name ? { ...p, ...updates } : p)
    );
  };

  const updateMapping = (outputParam: string, inputParam: string) => {
    if (onMappingChange) {
      onMappingChange({
        ...parameterMapping,
        [outputParam]: inputParam
      });
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Parameters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Input Parameters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Existing Input Parameters */}
          <div className="space-y-3">
            {inputParameters.map((param, index) => (
              <div key={param.name} className="p-3 border rounded-md space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Input
                      value={param.name}
                      onChange={(e) => updateInputParameter(param.name, { name: e.target.value })}
                      readOnly={readOnly}
                      className="font-mono text-sm w-32"
                    />
                    {param.required && (
                      <Badge variant="destructive" className="text-xs">Required</Badge>
                    )}
                  </div>
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeInputParameter(param.name)}
                    >
                      <X size={14} />
                    </Button>
                  )}
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <Select
                    value={param.type}
                    onValueChange={(value) => updateInputParameter(param.name, { type: value })}
                    disabled={readOnly}
                  >
                    <SelectTrigger className="text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PARAMETER_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  <label className="flex items-center gap-1 text-xs">
                    <input
                      type="checkbox"
                      checked={param.required}
                      onChange={(e) => updateInputParameter(param.name, { required: e.target.checked })}
                      disabled={readOnly}
                    />
                    Required
                  </label>
                </div>
                
                <Input
                  placeholder="Description (optional)"
                  value={param.description || ""}
                  onChange={(e) => updateInputParameter(param.name, { description: e.target.value })}
                  readOnly={readOnly}
                  className="text-xs"
                />
              </div>
            ))}
          </div>

          {/* Add New Input Parameter */}
          {!readOnly && (
            <Card className="border-dashed">
              <CardContent className="pt-4">
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="Parameter name"
                      value={newInputParam.name || ""}
                      onChange={(e) => setNewInputParam(prev => ({ ...prev, name: e.target.value }))}
                      className="font-mono text-sm"
                    />
                    <Select
                      value={newInputParam.type || "string"}
                      onValueChange={(value) => setNewInputParam(prev => ({ ...prev, type: value }))}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PARAMETER_TYPES.map(type => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <Input
                    placeholder="Description (optional)"
                    value={newInputParam.description || ""}
                    onChange={(e) => setNewInputParam(prev => ({ ...prev, description: e.target.value }))}
                    className="text-xs"
                  />
                  
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1 text-xs">
                      <input
                        type="checkbox"
                        checked={newInputParam.required !== false}
                        onChange={(e) => setNewInputParam(prev => ({ ...prev, required: e.target.checked }))}
                      />
                      Required
                    </label>
                    
                    <Button
                      size="sm"
                      onClick={addInputParameter}
                      disabled={!newInputParam.name}
                      className="flex items-center gap-1"
                    >
                      <Plus size={14} />
                      Add Input
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>

      {/* Output Parameters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Output Parameters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Existing Output Parameters */}
          <div className="space-y-3">
            {outputParameters.map((param, index) => (
              <div key={param.name} className="p-3 border rounded-md space-y-2">
                <div className="flex items-center justify-between">
                  <Input
                    value={param.name}
                    onChange={(e) => updateOutputParameter(param.name, { name: e.target.value })}
                    readOnly={readOnly}
                    className="font-mono text-sm flex-1 mr-2"
                  />
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeOutputParameter(param.name)}
                    >
                      <X size={14} />
                    </Button>
                  )}
                </div>
                
                <Select
                  value={param.type}
                  onValueChange={(value) => updateOutputParameter(param.name, { type: value })}
                  disabled={readOnly}
                >
                  <SelectTrigger className="text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PARAMETER_TYPES.map(type => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Input
                  placeholder="Description (optional)"
                  value={param.description || ""}
                  onChange={(e) => updateOutputParameter(param.name, { description: e.target.value })}
                  readOnly={readOnly}
                  className="text-xs"
                />

                {/* Parameter Mapping */}
                {showMapping && onMappingChange && (
                  <div className="flex items-center gap-2 pt-2 border-t">
                    <span className="text-xs text-muted-foreground">Maps to:</span>
                    <ArrowRight size={12} className="text-muted-foreground" />
                    <Select
                      value={parameterMapping[param.name] || ""}
                      onValueChange={(value) => updateMapping(param.name, value)}
                      disabled={readOnly}
                    >
                      <SelectTrigger className="text-xs flex-1">
                        <SelectValue placeholder="Select input" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">None</SelectItem>
                        {inputParameters.map(input => (
                          <SelectItem key={input.name} value={input.name}>
                            {input.name} ({input.type})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Add New Output Parameter */}
          {!readOnly && (
            <Card className="border-dashed">
              <CardContent className="pt-4">
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="Parameter name"
                      value={newOutputParam.name || ""}
                      onChange={(e) => setNewOutputParam(prev => ({ ...prev, name: e.target.value }))}
                      className="font-mono text-sm"
                    />
                    <Select
                      value={newOutputParam.type || "string"}
                      onValueChange={(value) => setNewOutputParam(prev => ({ ...prev, type: value }))}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PARAMETER_TYPES.map(type => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <Input
                    placeholder="Description (optional)"
                    value={newOutputParam.description || ""}
                    onChange={(e) => setNewOutputParam(prev => ({ ...prev, description: e.target.value }))}
                    className="text-xs"
                  />
                  
                  <div className="flex justify-end">
                    <Button
                      size="sm"
                      onClick={addOutputParameter}
                      disabled={!newOutputParam.name}
                      className="flex items-center gap-1"
                    >
                      <Plus size={14} />
                      Add Output
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </div>
  );
}