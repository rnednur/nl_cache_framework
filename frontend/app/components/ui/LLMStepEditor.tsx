'use client'

import React, { useState, useEffect } from 'react'
import { X, Save, Play, Eye, Database, Zap, Code, Settings, AlertCircle, CheckCircle } from 'lucide-react'
import { Node } from 'reactflow'

interface LLMStepEditorProps {
  isOpen: boolean
  onClose: () => void
  node: Node | null
  onSave: (updatedNode: Node) => void
  availableInputs: Array<{ stepId: string; stepName: string; outputSchema: any }>
}

interface LLMStepConfig {
  prompt_template: string
  input_parameters: string[]
  output_format: 'json' | 'text' | 'structured'
  expected_output: any
  model: string
  temperature: number
  max_tokens: number
  system_prompt: string
  input_mappings: Record<string, string> // Maps template variables to step outputs
}

const AVAILABLE_MODELS = [
  { id: 'google/gemini-pro', name: 'Google Gemini Pro', description: 'Fast and capable for most tasks' },
  { id: 'openai/gpt-4', name: 'OpenAI GPT-4', description: 'Most capable, higher cost' },
  { id: 'openai/gpt-3.5-turbo', name: 'OpenAI GPT-3.5 Turbo', description: 'Fast and cost-effective' },
  { id: 'anthropic/claude-3-sonnet', name: 'Claude 3 Sonnet', description: 'Balanced performance and safety' },
  { id: 'anthropic/claude-3-haiku', name: 'Claude 3 Haiku', description: 'Fast and efficient' }
]

const OUTPUT_FORMATS = [
  { id: 'json', name: 'JSON', description: 'Structured JSON object' },
  { id: 'text', name: 'Plain Text', description: 'Simple text response' },
  { id: 'structured', name: 'Structured', description: 'Custom structured format' }
]

export const LLMStepEditor: React.FC<LLMStepEditorProps> = ({
  isOpen,
  onClose,
  node,
  onSave,
  availableInputs
}) => {
  const [config, setConfig] = useState<LLMStepConfig>({
    prompt_template: '',
    input_parameters: [],
    output_format: 'json',
    expected_output: {},
    model: 'google/gemini-pro',
    temperature: 0.3,
    max_tokens: 1000,
    system_prompt: 'You are a helpful assistant.',
    input_mappings: {}
  })

  const [activeTab, setActiveTab] = useState<'prompt' | 'inputs' | 'model' | 'output'>('prompt')
  const [isPreviewMode, setIsPreviewMode] = useState(false)
  const [previewPrompt, setPreviewPrompt] = useState('')

  // Load existing config when node changes
  useEffect(() => {
    if (node && node.data.template) {
      try {
        const template = typeof node.data.template === 'string' 
          ? JSON.parse(node.data.template) 
          : node.data.template
        setConfig(prev => ({ ...prev, ...template }))
      } catch (error) {
        console.error('Failed to parse node template:', error)
      }
    }
  }, [node])

  // Generate preview prompt with sample data
  useEffect(() => {
    if (isPreviewMode) {
      let preview = config.prompt_template
      
      // Replace variables with sample data or mapped inputs
      Object.entries(config.input_mappings).forEach(([variable, mapping]) => {
        const inputSource = availableInputs.find(input => mapping.startsWith(input.stepId))
        const sampleValue = inputSource ? `[Data from ${inputSource.stepName}]` : `{${variable}}`
        preview = preview.replace(new RegExp(`\\{${variable}\\}`, 'g'), sampleValue)
      })
      
      setPreviewPrompt(preview)
    }
  }, [config.prompt_template, config.input_mappings, isPreviewMode, availableInputs])

  const handleSave = () => {
    if (!node) return

    const updatedNode = {
      ...node,
      data: {
        ...node.data,
        template: JSON.stringify(config)
      }
    }

    onSave(updatedNode)
    onClose()
  }

  const extractVariablesFromPrompt = (prompt: string): string[] => {
    const regex = /\{([^}]+)\}/g
    const variables = []
    let match

    while ((match = regex.exec(prompt)) !== null) {
      if (!variables.includes(match[1])) {
        variables.push(match[1])
      }
    }

    return variables
  }

  const handlePromptChange = (newPrompt: string) => {
    const variables = extractVariablesFromPrompt(newPrompt)
    setConfig(prev => ({
      ...prev,
      prompt_template: newPrompt,
      input_parameters: variables
    }))
  }

  if (!isOpen || !node) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-neutral-900 border border-neutral-700 rounded-lg w-full max-w-4xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-neutral-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Edit LLM Step</h2>
              <p className="text-sm text-neutral-400">{node.data.label}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPreviewMode(!isPreviewMode)}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                isPreviewMode 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-neutral-700 text-neutral-300 hover:bg-neutral-600'
              }`}
            >
              <Eye className="h-3 w-3 mr-1 inline" />
              Preview
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-neutral-700 rounded-md transition-colors"
            >
              <X className="h-4 w-4 text-neutral-400" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-neutral-700 px-4">
          <div className="flex space-x-1">
            {[
              { id: 'prompt', label: 'Prompt', icon: Code },
              { id: 'inputs', label: 'Inputs', icon: Database },
              { id: 'model', label: 'Model', icon: Settings },
              { id: 'output', label: 'Output', icon: CheckCircle }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-3 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
                  activeTab === tab.id
                    ? 'bg-neutral-800 text-white border-b-2 border-purple-500'
                    : 'text-neutral-400 hover:text-neutral-300 hover:bg-neutral-800/50'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'prompt' && (
            <div className="p-4 h-full flex flex-col">
              <div className="mb-4">
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  System Prompt
                </label>
                <textarea
                  value={config.system_prompt}
                  onChange={(e) => setConfig(prev => ({ ...prev, system_prompt: e.target.value }))}
                  className="w-full h-20 px-3 py-2 bg-neutral-800 border border-neutral-600 rounded-md text-white text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Define the AI's role and behavior..."
                />
              </div>
              
              <div className="flex-1 flex flex-col">
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Prompt Template
                  <span className="text-neutral-500 font-normal ml-2">
                    Use {'{variable_name}'} for dynamic content
                  </span>
                </label>
                {isPreviewMode ? (
                  <div className="flex-1 bg-neutral-800 border border-neutral-600 rounded-md p-3 overflow-auto">
                    <div className="text-xs text-neutral-400 mb-2">Preview with mapped inputs:</div>
                    <pre className="text-white text-sm whitespace-pre-wrap">{previewPrompt}</pre>
                  </div>
                ) : (
                  <textarea
                    value={config.prompt_template}
                    onChange={(e) => handlePromptChange(e.target.value)}
                    className="flex-1 px-3 py-2 bg-neutral-800 border border-neutral-600 rounded-md text-white text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Write your prompt template here...

Example:
Analyze the following data from the previous step:
{input_data}

Please provide:
1. Key insights
2. Recommendations  
3. Next steps

Format the response as JSON."
                  />
                )}
              </div>
              
              {config.input_parameters.length > 0 && (
                <div className="mt-4 p-3 bg-neutral-800/50 rounded-md">
                  <div className="text-xs text-neutral-400 mb-1">Detected variables:</div>
                  <div className="flex flex-wrap gap-2">
                    {config.input_parameters.map(param => (
                      <span 
                        key={param}
                        className="px-2 py-1 bg-purple-600/20 text-purple-300 text-xs rounded border border-purple-500/30"
                      >
                        {'{' + param + '}'}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'inputs' && (
            <div className="p-4">
              <div className="mb-4">
                <h3 className="text-sm font-medium text-neutral-300 mb-3">Map Variables to Step Outputs</h3>
                {availableInputs.length === 0 ? (
                  <div className="text-center py-8 text-neutral-500">
                    <Database className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No previous steps available</p>
                    <p className="text-xs">Add steps before this LLM step to use their outputs</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {config.input_parameters.map(param => (
                      <div key={param} className="flex items-center gap-3 p-3 bg-neutral-800 rounded-md">
                        <div className="text-sm text-neutral-300 min-w-24">
                          {'{' + param + '}'}
                        </div>
                        <div className="text-neutral-500">→</div>
                        <select
                          value={config.input_mappings[param] || ''}
                          onChange={(e) => setConfig(prev => ({
                            ...prev,
                            input_mappings: {
                              ...prev.input_mappings,
                              [param]: e.target.value
                            }
                          }))}
                          className="flex-1 px-3 py-2 bg-neutral-700 border border-neutral-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        >
                          <option value="">Select input source...</option>
                          {availableInputs.map(input => (
                            <option key={input.stepId} value={`${input.stepId}.output`}>
                              {input.stepName} → output
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'model' && (
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">Model</label>
                <select
                  value={config.model}
                  onChange={(e) => setConfig(prev => ({ ...prev, model: e.target.value }))}
                  className="w-full px-3 py-2 bg-neutral-800 border border-neutral-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {AVAILABLE_MODELS.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} - {model.description}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Temperature: {config.temperature}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={config.temperature}
                    onChange={(e) => setConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                    className="w-full accent-purple-500"
                  />
                  <div className="text-xs text-neutral-500 mt-1">Lower = more focused, Higher = more creative</div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">Max Tokens</label>
                  <input
                    type="number"
                    min="1"
                    max="4000"
                    value={config.max_tokens}
                    onChange={(e) => setConfig(prev => ({ ...prev, max_tokens: parseInt(e.target.value) || 1000 }))}
                    className="w-full px-3 py-2 bg-neutral-800 border border-neutral-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'output' && (
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">Output Format</label>
                <select
                  value={config.output_format}
                  onChange={(e) => setConfig(prev => ({ ...prev, output_format: e.target.value as any }))}
                  className="w-full px-3 py-2 bg-neutral-800 border border-neutral-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {OUTPUT_FORMATS.map(format => (
                    <option key={format.id} value={format.id}>
                      {format.name} - {format.description}
                    </option>
                  ))}
                </select>
              </div>

              {config.output_format === 'json' && (
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Expected JSON Schema
                  </label>
                  <textarea
                    value={JSON.stringify(config.expected_output, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value)
                        setConfig(prev => ({ ...prev, expected_output: parsed }))
                      } catch {
                        // Keep typing, don't update until valid JSON
                      }
                    }}
                    className="w-full h-40 px-3 py-2 bg-neutral-800 border border-neutral-600 rounded text-white text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder='{
  "insights": "string",
  "recommendations": ["string"],
  "confidence": "number"
}'
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-neutral-700 flex justify-between items-center">
          <div className="text-xs text-neutral-500">
            Configure how this LLM step processes data from previous workflow steps
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-neutral-400 hover:text-neutral-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md transition-colors flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
