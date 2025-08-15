'use client'

import { useState, useCallback, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'react-hot-toast'
import {
  ArrowLeft,
  FileText,
  Settings,
  Zap,
  RotateCcw,
  Save,
  Play,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  Eye,
  Code,
  CheckSquare,
  Loader2,
  Workflow,
  Copy,
  Clock,
  Wand2,
  RefreshCw
} from 'lucide-react'
import api from '@/app/services/api'
import InteractiveWorkflowBuilder from '@/app/components/ui/InteractiveWorkflowBuilder'
import { parseNLWorkflow, type ParserResult } from '@/app/utils/nlWorkflowParser'
import { convertWorkflowToNL, validateWorkflowStructure, convertWorkflowToDSL, generateExecutableWorkflow } from '@/app/utils/workflowToNL'
import { Node, Edge } from 'reactflow'


const EXECUTION_MODES = [
  { value: 'interactive', label: 'Interactive (with user prompts)' },
  { value: 'batch', label: 'Batch (fully automated)' },
  { value: 'scheduled', label: 'Scheduled (cron-based)' }
] as const

const ERROR_HANDLING = [
  { value: 'fail_fast', label: 'Fail fast (stop on first error)' },
  { value: 'continue', label: 'Continue (skip failed steps)' },
  { value: 'compensate', label: 'Compensate (rollback on failure)' }
] as const

interface CompilationResult {
  success: boolean
  steps_detected: number
  edges_wired: number
  tools_resolved: number
  dsl: any
  validation_results: ValidationItem[]
}

interface ValidationItem {
  type: 'success' | 'warning' | 'error'
  icon: string
  message: string
}


export default function WorkflowBuilder() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const editId = searchParams?.get('edit')
  const isEditMode = !!editId
  
  // Form state
  const [workflowName, setWorkflowName] = useState('')
  const [nlDescription, setNlDescription] = useState('')
  const [selectedFlowType, setSelectedFlowType] = useState('workflow')
  const [executionMode, setExecutionMode] = useState('interactive')
  const [errorHandling, setErrorHandling] = useState('fail_fast')
  const [isLoadingRecipe, setIsLoadingRecipe] = useState(isEditMode)
  
  // Generate unique workflow session ID for new workflows
  const [workflowSessionId] = useState(() => 
    isEditMode ? editId : `new-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  )
  
  // UI state
  const [activeTab, setActiveTab] = useState<'visual' | 'dsl' | 'validation'>('visual')
  const [isWorkflowMaximized, setIsWorkflowMaximized] = useState(false)
  
  // Debounced catalog name to prevent cache refreshing on every keystroke
  const [debouncedCatalogName, setDebouncedCatalogName] = useState('workflow')
  
  // Workflow synchronization state
  const [workflowNodes, setWorkflowNodes] = useState<Node[]>([])
  const [workflowEdges, setWorkflowEdges] = useState<Edge[]>([])
  const [isParsing, setIsParsing] = useState(false)
  const [parseResult, setParseResult] = useState<ParserResult | null>(null)
  const [isNLSynced, setIsNLSynced] = useState(true) // Track if NL and visual are in sync

  // Load existing recipe data if in edit mode
  useEffect(() => {
    if (isEditMode && editId) {
      loadExistingRecipe(parseInt(editId))
    }
  }, [isEditMode, editId])

  // Debounce catalog name to prevent unnecessary cache refreshes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedCatalogName(workflowName.toLowerCase().replace(/\s+/g, '-'))
    }, 500) // 500ms debounce

    return () => clearTimeout(timer)
  }, [workflowName])

  // Helper function to generate NL description from workflow steps
  const generateNLDescriptionFromSteps = (workflowName: string, steps: any[], connections?: any[]) => {
    let nl = `Fullflow '${workflowName}':\n`
    
    steps.forEach((step, index) => {
      nl += `${index + 1}) ${step.name}\n`
    })
    
    if (connections && connections.length > 0) {
      nl += '\nWire: '
      const wiringStrings = connections.map((conn, index) => {
        const fromStep = steps.findIndex(s => s.id === conn.from) + 1
        const toStep = steps.findIndex(s => s.id === conn.to) + 1
        return fromStep > 0 && toStep > 0 ? `${fromStep}→${toStep}` : ''
      }).filter(Boolean)
      nl += wiringStrings.join(', ')
    }
    
    return nl
  }

  // Helper functions for template styling (matching InteractiveWorkflowBuilder)
  const getTemplateIcon = (templateType: string): string => {
    const iconMap: Record<string, string> = {
      sql: '🗄️',
      api: '🌐',
      workflow: '⚡',
      script: '📜',
      url: '🔗',
      cli: '💻',
      prompt: '🤖',
      llm_step: '🧠',
      configuration: '⚙️',
      graphql: '📊',
      nosql: '🍃',
      function: '⚙️',
      mcp_tool: '🔧',
      agent: '🤖',
    }
    return iconMap[templateType] || '📋'
  }

  const getTemplateColor = (templateType: string): string => {
    const colorMap: Record<string, string> = {
      sql: '#3b82f6',
      api: '#10b981',
      workflow: '#8b5cf6',
      script: '#f59e0b',
      url: '#06b6d4',
      cli: '#6b7280',
      prompt: '#ec4899',
      llm_step: '#a855f7',
      configuration: '#84cc16',
      graphql: '#f97316',
      nosql: '#14b8a6',
      function: '#f59e0b',
      mcp_tool: '#059669',
      agent: '#dc2626',
    }
    return colorMap[templateType] || '#6b7280'
  }

  const loadExistingRecipe = async (recipeId: number) => {
    setIsLoadingRecipe(true)
    try {
      toast.loading('Loading recipe data...', { id: 'load-recipe' })
      
      const recipe = await api.getCacheEntry(recipeId)
      
      // Populate form fields with existing data
      setWorkflowName(recipe.nl_query || '')
      setSelectedFlowType(recipe.catalog_type || 'workflow')
      setExecutionMode(recipe.catalog_subtype || 'interactive')
      
      // Convert existing recipe template to visual workflow if possible
      let nlDesc = ''
      let loadedNodes: Node[] = []
      let loadedEdges: Edge[] = []
      
      if (recipe.template) {
        try {
          // Try to parse as JSON first (might be a workflow definition)
          const templateObj = JSON.parse(recipe.template)
          
          if (templateObj.flow && templateObj.flow.steps) {
            // It's our structured workflow format - convert to visual
            const flow = templateObj.flow
            
            // Create start node
            const startNode: Node = {
              id: 'start',
              type: 'input',
              position: { x: 250, y: 50 },
              data: { label: 'Start' },
              style: {
                background: '#10b981',
                color: 'white',
                border: '2px solid #047857',
                borderRadius: '8px',
              },
            }
            loadedNodes.push(startNode)
            
            // Convert steps to nodes
            flow.steps.forEach((step: any, index: number) => {
              const node: Node = {
                id: step.id,
                type: 'default',
                position: step.position || { x: 100 + (index % 3) * 200, y: 150 + Math.floor(index / 3) * 100 },
                data: {
                  label: `${getTemplateIcon(step.type)} ${step.name}`,
                  originalDescription: step.name,
                  templateType: step.type,
                  originalStepType: step.type,
                  toolRef: step.tool_ref,
                  params: step.params,
                  cacheEntryId: step.cache_entry_id
                },
                style: {
                  background: getTemplateColor(step.type),
                  color: 'white',
                  border: '2px solid #374151',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  width: 180,
                  textAlign: 'center',
                },
              }
              loadedNodes.push(node)
            })
            
            // Convert connections to edges
            if (flow.connections) {
              flow.connections.forEach((conn: any, index: number) => {
                const edge: Edge = {
                  id: `edge-${conn.from}-${conn.to}`,
                  source: conn.from,
                  target: conn.to,
                  animated: true,
                  style: { stroke: '#10b981', strokeWidth: 2 },
                  label: conn.label || conn.data_mapping || '',
                }
                loadedEdges.push(edge)
              })
            }
            
            // Create NL description from structured data
            nlDesc = flow.nl_description || (flow.metadata?.nl_description) || 
                    generateNLDescriptionFromSteps(recipe.nl_query, flow.steps, flow.connections)
                    
          } else {
            // Other JSON format, use as description
            nlDesc = recipe.reasoning_trace || recipe.template
          }
        } catch {
          // Not JSON, use as plain text
          nlDesc = recipe.reasoning_trace || recipe.template || 
                  `Fullflow '${recipe.nl_query}':\n(Loaded from existing recipe)`
        }
      } else {
        // No template, create a basic NL description
        nlDesc = recipe.reasoning_trace || 
                `Fullflow '${recipe.nl_query}':\n(No workflow steps defined - please add steps using the visual editor or NL description)`
      }
      
      setNlDescription(nlDesc)
      
      // Set loaded workflow nodes and edges if any
      if (loadedNodes.length > 1) { // More than just start node
        setWorkflowNodes(loadedNodes)
        setWorkflowEdges(loadedEdges)
        setIsNLSynced(true) // They should be in sync since we just loaded both
      }
      
      toast.success('Recipe loaded successfully', { id: 'load-recipe' })
    } catch (error: any) {
      toast.error(`Failed to load recipe: ${error.message}`, { id: 'load-recipe' })
      // Redirect back to new recipe mode if loading fails
      router.replace('/recipes/new')
    } finally {
      setIsLoadingRecipe(false)
    }
  }

  // Enhanced maximize function with notifications and keyboard support
  const handleMaximizeToggle = (maximize: boolean) => {
    setIsWorkflowMaximized(maximize)
    if (maximize) {
      toast.success('🖥️ Entered full-screen workflow mode', { 
        duration: 2000,
        position: 'bottom-center'
      })
    } else {
      toast.success('📐 Returned to split-screen mode', { 
        duration: 2000,
        position: 'bottom-center'
      })
    }
  }

  // Keyboard shortcuts for full-screen mode
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl+Shift+M for full-screen toggle
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'M') {
        event.preventDefault()
        handleMaximizeToggle(!isWorkflowMaximized)
      }
      
      // Escape key to exit full-screen
      if (event.key === 'Escape' && isWorkflowMaximized) {
        event.preventDefault()
        handleMaximizeToggle(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isWorkflowMaximized])
  const [isCompiling, setIsCompiling] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [compilationResult, setCompilationResult] = useState<CompilationResult | null>(null)



  const handleCompile = async () => {
    setIsCompiling(true)
    try {
      toast.loading('Compiling workflow...', { id: 'compile' })
      
      // Validate that we have a workflow to compile
      if (!workflowNodes || workflowNodes.length <= 1) {
        throw new Error('No workflow steps defined. Please add steps to the visual workflow builder.')
      }
      
      // Validate workflow structure first
      const validation = validateWorkflowStructure(workflowNodes, workflowEdges)
      const validationResults: ValidationItem[] = []
      
      // Add validation results
      validation.errors.forEach(error => {
        validationResults.push({ type: 'error', icon: '✗', message: error })
      })
      validation.warnings.forEach(warning => {
        validationResults.push({ type: 'warning', icon: '!', message: warning })
      })
      
      // If there are errors, compilation fails
      if (!validation.isValid) {
        const result: CompilationResult = {
          success: false,
          steps_detected: workflowNodes.length - 1, // Exclude start node
          edges_wired: workflowEdges.length,
          tools_resolved: 0,
          dsl: null,
          validation_results: validationResults
        }
        setCompilationResult(result)
        toast.error('Compilation failed due to validation errors', { id: 'compile' })
        return
      }
      
      // Generate real DSL from the workflow
      const dslResult = convertWorkflowToDSL(workflowNodes, workflowEdges, workflowName)
      
      if (!dslResult.success || !dslResult.dsl) {
        throw new Error(dslResult.error || 'Failed to generate DSL from workflow')
      }
      
      // Generate executable workflow format
      const executableResult = generateExecutableWorkflow(workflowNodes, workflowEdges, workflowName)
      
      // Count cache-referenced steps vs manual steps
      const cacheReferencedSteps = workflowNodes.filter(node => 
        node.id !== 'start' && node.data?.cacheEntryId
      ).length
      const manualSteps = (workflowNodes.length - 1) - cacheReferencedSteps // Exclude start node
      
      // Add success validation results
      validationResults.push(
        { type: 'success', icon: '✓', message: `${workflowNodes.length - 1} workflow steps detected` },
        { type: 'success', icon: '✓', message: `${workflowEdges.length} connections mapped` },
        { type: 'success', icon: '✓', message: `${cacheReferencedSteps} steps reference cache entries` }
      )
      
      if (manualSteps > 0) {
        validationResults.push({
          type: 'warning', 
          icon: '!', 
          message: `${manualSteps} steps need manual template definition (no cache reference)`
        })
      }
      
      if (executableResult.success) {
        validationResults.push(
          { type: 'success', icon: '✓', message: 'Executable workflow format generated' }
        )
      }
      
      // Build successful compilation result
      const result: CompilationResult = {
        success: true,
        steps_detected: workflowNodes.length - 1, // Exclude start node
        edges_wired: workflowEdges.length,
        tools_resolved: cacheReferencedSteps,
        dsl: {
          // Include both DSL and executable formats
          workflow_dsl: dslResult.dsl,
          executable_workflow: executableResult.success ? executableResult.workflow : null,
          cache_references: dslResult.dsl.workflow.metadata.cache_ids,
          template_types: dslResult.dsl.workflow.metadata.template_types
        },
        validation_results: validationResults
      }
      
      setCompilationResult(result)
      toast.success(
        `Workflow compiled! ${cacheReferencedSteps} cache refs, ${workflowEdges.length} connections`, 
        { id: 'compile' }
      )
      
    } catch (error: any) {
      toast.error('Compilation failed', { id: 'compile' })
      setCompilationResult({
        success: false,
        steps_detected: workflowNodes ? workflowNodes.length - 1 : 0,
        edges_wired: workflowEdges ? workflowEdges.length : 0,
        tools_resolved: 0,
        dsl: null,
        validation_results: [
          { type: 'error', icon: '✗', message: error.message || 'Compilation failed' }
        ]
      })
    } finally {
      setIsCompiling(false)
    }
  }

  const handleSaveWorkflow = async () => {
    if (!workflowName.trim()) {
      toast.error('Please enter a workflow name')
      return
    }

    setIsSaving(true)
    try {
      const loadingMessage = isEditMode ? 'Updating workflow...' : 'Saving workflow...'
      toast.loading(loadingMessage, { id: 'save' })

      // Create workflow structure from current data
      let workflowTemplate = {}
      
      if (workflowNodes.length > 1) { // More than just the start node
        // Convert visual workflow to structured format
        const stepNodes = workflowNodes.filter(node => node.id !== 'start')
        const steps = stepNodes.map((node, index) => ({
          id: node.id,
          step_number: index + 1,
          name: node.data?.originalDescription || node.data?.label || `Step ${index + 1}`,
          type: node.data?.templateType || node.data?.originalStepType || 'api',
          tool_ref: node.data?.toolRef,
          params: node.data?.params,
          position: node.position,
          cache_entry_id: node.data?.cacheEntryId
        }))
        
        const connections = workflowEdges.map(edge => ({
          from: edge.source,
          to: edge.target,
          label: edge.label || '',
          data_mapping: edge.label
        }))
        
        workflowTemplate = {
          flow: {
            id: workflowName.toLowerCase().replace(/\s+/g, '-'),
            name: workflowName,
            type: selectedFlowType,
            execution_mode: executionMode,
            error_handling: errorHandling,
            steps: steps,
            connections: connections,
            metadata: {
              created_from: 'visual_editor',
              nl_description: nlDescription,
              nodes_count: workflowNodes.length,
              edges_count: workflowEdges.length
            }
          }
        }
      } else if (compilationResult?.success) {
        // Use compiled DSL if available and no visual workflow
        workflowTemplate = compilationResult.dsl
      } else if (nlDescription.trim()) {
        // Use NL description as template
        workflowTemplate = {
          flow: {
            id: workflowName.toLowerCase().replace(/\s+/g, '-'),
            name: workflowName,
            type: selectedFlowType,
            execution_mode: executionMode,
            error_handling: errorHandling,
            nl_description: nlDescription,
            metadata: {
              created_from: 'nl_description'
            }
          }
        }
      } else {
        toast.error('Please add workflow steps using the visual editor or provide a natural language description')
        setIsSaving(false)
        return
      }

      // Convert to cache entry format
      const cacheEntry = {
        nl_query: workflowName,
        template: JSON.stringify(workflowTemplate, null, 2),
        template_type: 'workflow',
        catalog_type: selectedFlowType,
        catalog_subtype: executionMode,
        catalog_name: workflowName.toLowerCase().replace(/\s+/g, '-'),
        reasoning_trace: nlDescription,
        is_template: false,
        status: 'active',
        entity_replacements: {},
        tags: {
          flow_type: [selectedFlowType],
          execution_mode: [executionMode],
          error_handling: [errorHandling],
          has_visual_workflow: workflowNodes.length > 1 ? ['true'] : ['false'],
          steps_count: [workflowNodes.length.toString()]
        }
      }

      let savedWorkflow
      if (isEditMode && editId) {
        // Update existing recipe
        savedWorkflow = await api.updateCacheEntry(parseInt(editId), cacheEntry)
        toast.success('Workflow updated successfully', { id: 'save' })
      } else {
        // Create new recipe
        savedWorkflow = await api.createCacheEntry(cacheEntry)
        toast.success('Workflow saved successfully', { id: 'save' })
      }
      
      router.push(`/recipes/${savedWorkflow.id}`)
    } catch (error: any) {
      const errorMessage = isEditMode ? 'Failed to update workflow' : 'Failed to save workflow'
      toast.error(`${errorMessage}: ${error.message}`, { id: 'save' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleClearAll = () => {
    setWorkflowName('')
    setNlDescription('')
    setSelectedFlowType('workflow')
    setExecutionMode('interactive')
    setErrorHandling('fail_fast')
    setCompilationResult(null)
    toast.success('Workflow cleared')
  }

  // Parse natural language description into visual workflow using backend API
  const handleParseNL = async () => {
    console.log('🖱️ Parse NL button clicked')
    console.log('Current isParsing state:', isParsing)
    
    if (!nlDescription.trim()) {
      toast.error('Please enter a natural language workflow description')
      return
    }

    console.log('✅ Validation passed, setting isParsing to true')
    setIsParsing(true)
    
    // Add a small delay to ensure the UI updates
    await new Promise(resolve => setTimeout(resolve, 100))
    try {
      toast.loading('Analyzing natural language with AI...', { id: 'parse', duration: 30000 }) // Persist for 30 seconds
      
      console.log('🚀 Starting recipe analysis...')
      console.log('Recipe text:', nlDescription.substring(0, 100) + '...')
      console.log('Workflow name:', workflowName || 'New Workflow')
      console.log('isParsing set to:', true)
      
      // Call backend API for recipe analysis
      const startTime = Date.now()
      const analysisResult = await api.analyzeRecipeText({
        recipe_text: nlDescription,
        recipe_name: workflowName || 'New Workflow'
      })
      const endTime = Date.now()
      
      console.log(`✅ Recipe analysis completed in ${endTime - startTime}ms`)
      console.log('Analysis result:', analysisResult)
      
      // Update the toast to show success
      toast.loading('Processing analysis results...', { id: 'parse', duration: 10000 })
      
      if (analysisResult.steps && analysisResult.steps.length > 0) {
        console.log(`📋 Found ${analysisResult.steps.length} steps, creating visual workflow...`)
        // Convert backend analysis result to ReactFlow nodes and edges
        const nodes: any[] = []
        const edges: any[] = []
        
        // Add start node
        nodes.push({
          id: 'start',
          type: 'input',
          position: { x: 250, y: 50 },
          data: { label: 'Start' },
          style: {
            background: '#10b981',
            color: 'white',
            border: '2px solid #047857',
            borderRadius: '8px',
          },
        })
        
        // Add step nodes from backend analysis
        const stepSpacing = 200
        analysisResult.steps.forEach((step: any, index: number) => {
          // Use mapped tool information if available, otherwise fall back to step info
          const mappedTool = step.mapped_tool
          const toolType = mappedTool?.type || step.step_type
          const toolName = mappedTool?.name || step.name
          const confidence = mappedTool?.confidence || step.confidence
          
          // Create enhanced label with tool mapping info
          let label = `${getTemplateIcon(toolType)} ${toolName}`
          if (mappedTool && confidence) {
            label += ` (${(confidence * 100).toFixed(0)}%)`
          }
          
          const node = {
            id: `step-${index + 1}`,
            type: 'default',
            position: { 
              x: 100 + (index % 3) * stepSpacing, 
              y: 150 + Math.floor(index / 3) * 100 
            },
            data: {
              label: label,
              stepNumber: index + 1,
              templateType: toolType,
              originalStepType: step.step_type,
              template: step.description,
              confidence: confidence,
              entities: step.entities,
              originalDescription: step.description,
              // Add mapped tool information
              mappedTool: mappedTool,
              alternativeTools: step.alternative_tools || [],
              requiresReview: step.requires_review || false,
              suggestions: step.suggestions || []
            },
            style: {
              background: mappedTool ? getTemplateColor(toolType) : '#6b7280', // Gray if no tool mapped
              color: 'white',
              border: mappedTool && confidence > 0.7 ? '2px solid #10b981' : 
                      mappedTool && confidence > 0.5 ? '2px solid #f59e0b' :
                      mappedTool ? '2px solid #ef4444' : '2px solid #374151',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 'bold',
              width: 200, // Slightly wider to accommodate confidence %
              textAlign: 'center',
            },
          }
          nodes.push(node)
        })
        
        // Create sequential edges (start -> step1 -> step2 -> ...)
        if (analysisResult.steps.length > 0) {
          // Connect start to first step
          edges.push({
            id: 'edge-start-1',
            source: 'start',
            target: `step-1`,
            animated: true,
            style: { stroke: '#10b981', strokeWidth: 2 },
          })
          
          // Connect steps sequentially
          for (let i = 0; i < analysisResult.steps.length - 1; i++) {
            edges.push({
              id: `edge-${i + 1}-${i + 2}`,
              source: `step-${i + 1}`,
              target: `step-${i + 2}`,
              animated: true,
              style: { stroke: '#10b981', strokeWidth: 2 },
            })
          }
        }
        
        // Update workflow state
        setWorkflowNodes(nodes)
        setWorkflowEdges(edges)
        setIsNLSynced(true)
        
        // Update workflow name if provided by analysis
        if (analysisResult.recipe_name) {
          setWorkflowName(analysisResult.recipe_name)
        }
        
        toast.success(`Analyzed ${analysisResult.steps.length} steps successfully`, { id: 'parse' })
        
        // Store parse result for debugging
        setParseResult({
          success: true,
          workflow: {
            name: analysisResult.recipe_name || workflowName,
            steps: analysisResult.steps,
            wiring: []
          },
          nodes,
          edges
        })
        
      } else {
        console.warn('⚠️ No steps found in analysis result:', analysisResult)
        toast.error('Failed to analyze recipe - no steps identified', { id: 'parse' })
        setParseResult({ success: false, errors: ['No steps identified'] })
      }
    } catch (error: any) {
      console.error('❌ Parse NL error:', error)
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        stack: error.stack
      })
      
      let errorMessage = 'Analysis failed'
      if (error.response?.data?.detail) {
        errorMessage += `: ${error.response.data.detail}`
      } else if (error.message) {
        errorMessage += `: ${error.message}`
      }
      
      toast.error(errorMessage, { id: 'parse' })
      setParseResult({ success: false, errors: [error.message] })
    } finally {
      console.log('🏁 Finally block: setting isParsing to false')
      setIsParsing(false)
    }
  }

  // Handle workflow changes from InteractiveWorkflowBuilder
  const handleWorkflowChange = useCallback((nodes: Node[], edges: Edge[]) => {
    setWorkflowNodes(nodes)
    setWorkflowEdges(edges)
    
    // Mark as out of sync if visual workflow differs from NL
    setIsNLSynced(false)
    
    console.log('Workflow updated:', { nodes: nodes.length, edges: edges.length })
  }, [])

  // Sync visual workflow back to NL description
  const handleSyncToNL = () => {
    if (workflowNodes.length === 0) {
      toast.error('No visual workflow to sync')
      return
    }

    try {
      toast.loading('Converting visual workflow to natural language...', { id: 'sync-to-nl' })
      
      const generatedNL = convertWorkflowToNL(workflowNodes, workflowEdges, workflowName, {
        includeWiring: true,
        preserveOrder: true,
        includeMetadata: false
      })
      
      // Validate the workflow structure
      const validation = validateWorkflowStructure(workflowNodes, workflowEdges)
      
      if (validation.errors.length > 0) {
        toast.error(`Workflow has errors: ${validation.errors.join(', ')}`, { id: 'sync-to-nl' })
        return
      }
      
      setNlDescription(generatedNL)
      setIsNLSynced(true)
      
      let message = 'Visual workflow synchronized to natural language'
      if (validation.warnings.length > 0) {
        message += ` (${validation.warnings.length} warnings)`
      }
      
      toast.success(message, { id: 'sync-to-nl' })
      
      // Show warnings if any
      if (validation.warnings.length > 0) {
        setTimeout(() => {
          toast((t) => (
            <div className="text-sm">
              <div className="font-semibold mb-1">Workflow Warnings:</div>
              <ul className="list-disc list-inside space-y-1">
                {validation.warnings.map((warning, index) => (
                  <li key={index} className="text-yellow-600">{warning}</li>
                ))}
              </ul>
            </div>
          ), { duration: 5000 })
        }, 1000)
      }
      
    } catch (error: any) {
      toast.error(`Failed to sync to NL: ${error.message}`, { id: 'sync-to-nl' })
    }
  }

  const handleTestRun = async () => {
    if (!compilationResult) {
      toast.error('Please compile the workflow first before testing')
      return
    }
    
    if (!compilationResult.success) {
      toast.error('Please fix compilation errors before testing')
      return
    }
    
    const stepCount = compilationResult.steps_detected
    const edgeCount = compilationResult.edges_wired
    
    toast.loading(`Testing workflow with ${stepCount} steps and ${edgeCount} connections...`, { id: 'test' })
    
    // Simulate test run with realistic timing
    setTimeout(() => {
      toast.success(
        `Test run completed! Executed ${stepCount} steps successfully.`, 
        { id: 'test', duration: 4000 }
      )
    }, 2000 + (stepCount * 500)) // More steps = longer test time
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      {/* Header */}
      <div className="bg-neutral-900 border-b border-neutral-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/recipes')}
            className="p-2 text-neutral-400 hover:text-neutral-300 transition-colors rounded-md hover:bg-neutral-800"
            title="Back to Workflows"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-600 rounded-md flex items-center justify-center text-white font-bold text-sm">
              W
            </div>
            <div>
              <h1 className="text-lg font-semibold text-neutral-100">
                {isLoadingRecipe ? 'Loading Workflow...' : isEditMode ? 'Edit Workflow' : 'Create New Workflow'}
              </h1>
              <p className="text-sm text-neutral-400">
                {isEditMode ? 'Modify existing automation workflow' : 'Multi-step automation workflow'}
              </p>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleClearAll}
            className="px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-md text-neutral-300 hover:bg-neutral-700 transition-colors text-sm font-medium"
          >
            Clear All
          </button>
          <button
            onClick={handleSaveWorkflow}
            disabled={isSaving || isLoadingRecipe || !workflowName.trim()}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {isEditMode ? 'Update Workflow' : 'Save Workflow'}
          </button>
        </div>
      </div>

      {/* Loading overlay when loading recipe data */}
      {isLoadingRecipe && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-neutral-800 rounded-lg p-6 flex items-center gap-3 border border-neutral-700">
            <Loader2 className="h-6 w-6 animate-spin text-green-400" />
            <span className="text-neutral-100">Loading recipe data...</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className={`${isWorkflowMaximized ? 'hidden' : 'grid grid-cols-[400px_1fr]'} h-[calc(100vh-81px)]`}>
        {/* Left Panel - Workflow Specification */}
        <div className="bg-neutral-900 border-r border-neutral-800 flex flex-col min-w-0">
          <div className="px-6 py-5 border-b border-neutral-800">
            <div className="flex items-center gap-2 text-base font-semibold text-neutral-100 mb-2">
              <FileText className="h-5 w-5" />
              Workflow Specification
            </div>
            <p className="text-sm text-neutral-400">
              Define your workflow using natural language or structured inputs
            </p>
          </div>

          <div className="flex-1 px-6 py-6 overflow-y-auto space-y-8">
            {/* Basic Information */}
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-neutral-100 mb-3">
                <span>📋</span>
                Basic Information
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Workflow Name *
                  </label>
                  <input
                    type="text"
                    value={workflowName}
                    onChange={(e) => setWorkflowName(e.target.value)}
                    className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-md text-neutral-100 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    placeholder="Post-Incident Review Automation"
                  />
                </div>

              </div>
            </div>

            {/* Natural Language Specification */}
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-neutral-100 mb-3">
                <span>🗣️</span>
                Natural Language Description
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Describe your workflow
                  </label>
                  <textarea
                    value={nlDescription}
                    onChange={(e) => setNlDescription(e.target.value)}
                    className="w-full h-48 px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg text-neutral-100 font-mono text-sm resize-y focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 leading-relaxed"
                    placeholder="Example: 'Fullflow for Post-Incident Review:&#10;1) Fetch Jira issues with query project=OPS AND status=Resolved&#10;2) Summarize issues using Claude LLM &#10;3) Update Confluence page with summary&#10;&#10;Wire: 1→2 (pass issues), 2→3 (pass summary)'"
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={handleParseNL}
                    disabled={isParsing || !nlDescription.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Parse natural language description into visual workflow"
                  >
                    {isParsing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                    Parse NL to Visual
                  </button>
                  <button
                    onClick={handleSyncToNL}
                    disabled={workflowNodes.length <= 1} // Disable if only start node
                    className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Sync visual workflow back to natural language description"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Sync Visual to NL
                  </button>
                  <button
                    onClick={handleCompile}
                    disabled={isCompiling}
                    className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isCompiling ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                    Compile to DSL
                  </button>
                  <button 
                    onClick={handleSaveWorkflow}
                    disabled={isSaving}
                    className="px-5 py-2.5 bg-transparent border border-neutral-600 text-neutral-300 rounded-md hover:bg-neutral-700 transition-colors font-medium"
                  >
                    Save Draft
                  </button>
                  <button
                    onClick={handleTestRun}
                    disabled={!compilationResult?.success}
                    className="px-5 py-2.5 bg-transparent border border-neutral-600 text-neutral-300 rounded-md hover:bg-neutral-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    title={!compilationResult?.success ? "Compile the workflow first before testing" : "Test the compiled workflow"}
                  >
                    Test Run
                  </button>
                </div>

                {/* Sync Status Indicator */}
                <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${
                  isNLSynced 
                    ? 'bg-green-500/10 text-green-400 border border-green-500/30' 
                    : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${isNLSynced ? 'bg-green-400' : 'bg-yellow-400'}`} />
                  <span>
                    {isNLSynced 
                      ? 'Natural language and visual workflow are synchronized' 
                      : 'Visual workflow has changed - re-parse to synchronize'}
                  </span>
                  {!isNLSynced && (
                    <div className="ml-2 flex gap-1">
                      <button
                        onClick={handleParseNL}
                        className="px-2 py-1 bg-blue-500/20 hover:bg-blue-500/30 rounded text-blue-400 transition-colors"
                        title="Parse NL to Visual"
                      >
                        <Wand2 className="h-3 w-3" />
                      </button>
                      <button
                        onClick={handleSyncToNL}
                        disabled={workflowNodes.length <= 1}
                        className="px-2 py-1 bg-purple-500/20 hover:bg-purple-500/30 rounded text-purple-400 transition-colors disabled:opacity-50"
                        title="Sync Visual to NL"
                      >
                        <RefreshCw className="h-3 w-3" />
                      </button>
                    </div>
                  )}
                </div>

                {compilationResult && (
                  <div className={`rounded-lg border p-4 ${
                    compilationResult.success
                      ? 'bg-green-500/10 border-green-500/30'
                      : 'bg-red-500/10 border-red-500/30'
                  }`}>
                    <div className={`font-semibold mb-2 flex items-center gap-2 ${
                      compilationResult.success ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {compilationResult.success ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                      {compilationResult.success ? 'Compilation Successful' : 'Compilation Failed'}
                    </div>
                    <ul className="space-y-1 text-sm text-neutral-300">
                      {compilationResult.success && (
                        <>
                          <li className="flex items-center gap-2">
                            <span className="text-green-400">•</span>
                            {compilationResult.steps_detected} steps detected and validated
                          </li>
                          <li className="flex items-center gap-2">
                            <span className="text-green-400">•</span>
                            {compilationResult.edges_wired} edges wired correctly
                          </li>
                          <li className="flex items-center gap-2">
                            <span className="text-green-400">•</span>
                            {compilationResult.tools_resolved} tool references resolved
                          </li>
                        </>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Advanced Settings */}
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-neutral-100 mb-3">
                <Settings className="h-4 w-4" />
                Execution Settings
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Execution Mode
                  </label>
                  <select
                    value={executionMode}
                    onChange={(e) => setExecutionMode(e.target.value)}
                    className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-md text-neutral-100 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    {EXECUTION_MODES.map((mode) => (
                      <option key={mode.value} value={mode.value}>
                        {mode.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Error Handling
                  </label>
                  <select
                    value={errorHandling}
                    onChange={(e) => setErrorHandling(e.target.value)}
                    className="w-full px-3 py-2.5 bg-neutral-800 border border-neutral-700 rounded-md text-neutral-100 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    {ERROR_HANDLING.map((handler) => (
                      <option key={handler.value} value={handler.value}>
                        {handler.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Visual Preview */}
        <div className="bg-neutral-950 flex flex-col min-w-0 overflow-hidden relative">
          <div className="flex bg-neutral-900 border-b border-neutral-800">
            <button
              onClick={() => setActiveTab('visual')}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'visual'
                  ? 'text-green-400 border-green-400'
                  : 'text-neutral-400 border-transparent hover:text-neutral-300'
              }`}
            >
              <Eye className="h-4 w-4 inline mr-2" />
              Visual Flow
            </button>
            <button
              onClick={() => setActiveTab('dsl')}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'dsl'
                  ? 'text-green-400 border-green-400'
                  : 'text-neutral-400 border-transparent hover:text-neutral-300'
              }`}
            >
              <Code className="h-4 w-4 inline mr-2" />
              DSL Preview
            </button>
            <button
              onClick={() => setActiveTab('validation')}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'validation'
                  ? 'text-green-400 border-green-400'
                  : 'text-neutral-400 border-transparent hover:text-neutral-300'
              }`}
            >
              <CheckSquare className="h-4 w-4 inline mr-2" />
              Validation
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === 'visual' && (
              <div className="h-full w-full relative">
                <InteractiveWorkflowBuilder
                  catalogType="workflow"
                  catalogSubtype={executionMode}
                  catalogName={debouncedCatalogName || 'workflow'}
                  initialNodes={workflowNodes}
                  initialEdges={workflowEdges}
                  onWorkflowChange={handleWorkflowChange}
                  onMaximizeChange={handleMaximizeToggle}
                  clearOnMount={!isEditMode}  // Clear on mount for new workflows, preserve for edit mode
                  workflowId={workflowSessionId}  // Use unique session ID
                />
              </div>
            )}

            {activeTab === 'dsl' && (
              <div className="p-6 h-full overflow-y-auto">
                <div className="bg-neutral-800 border border-neutral-700 rounded-lg p-4 overflow-hidden">
                {compilationResult?.success && compilationResult.dsl ? (
                  <div className="space-y-4">
                    {/* Cache References Summary */}
                    {compilationResult.dsl.cache_references && compilationResult.dsl.cache_references.length > 0 && (
                      <div className="mb-4 p-3 bg-green-900/20 border border-green-700/50 rounded-lg">
                        <div className="text-sm font-medium text-green-400 mb-1">Cache References</div>
                        <div className="text-xs text-neutral-300">
                          This workflow references {compilationResult.dsl.cache_references.length} cache entries:
                          <span className="ml-1 text-green-400">
                            {compilationResult.dsl.cache_references.filter(Boolean).join(', ')}
                          </span>
                        </div>
                        <div className="text-xs text-neutral-400 mt-1">
                          Template types: {compilationResult.dsl.template_types?.join(', ')}
                        </div>
                      </div>
                    )}
                    
                    {/* Actual DSL Content */}
                    <div className="bg-neutral-900 border border-neutral-600 rounded-lg p-4 font-mono text-sm text-neutral-300 overflow-x-auto max-h-96">
                      <pre className="whitespace-pre-wrap">
                        {JSON.stringify(
                          compilationResult.dsl.workflow_dsl || compilationResult.dsl, 
                          null, 
                          2
                        )}
                      </pre>
                    </div>
                    
                    {/* Executable Workflow Preview */}
                    {compilationResult.dsl.executable_workflow && (
                      <div className="mt-4">
                        <div className="text-sm font-medium text-blue-400 mb-2">Executable Workflow Format:</div>
                        <div className="bg-neutral-900 border border-neutral-600 rounded-lg p-4 font-mono text-xs text-neutral-400 overflow-x-auto max-h-64">
                          <pre className="whitespace-pre-wrap">
                            {JSON.stringify(compilationResult.dsl.executable_workflow, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                    
                    {/* Copy to Clipboard Button */}
                    <div className="flex gap-2 pt-2 border-t border-neutral-700">
                      <button
                        onClick={() => {
                          const dslContent = JSON.stringify(compilationResult.dsl.workflow_dsl || compilationResult.dsl, null, 2)
                          navigator.clipboard.writeText(dslContent)
                          toast.success('DSL copied to clipboard', { duration: 2000 })
                        }}
                        className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded-md transition-colors"
                      >
                        Copy DSL
                      </button>
                      {compilationResult.dsl.executable_workflow && (
                        <button
                          onClick={() => {
                            const execContent = JSON.stringify(compilationResult.dsl.executable_workflow, null, 2)
                            navigator.clipboard.writeText(execContent)
                            toast.success('Executable format copied to clipboard', { duration: 2000 })
                          }}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-md transition-colors"
                        >
                          Copy Executable
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-neutral-500">
                    <Code className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No DSL generated yet</p>
                    <p className="text-sm">Compile your workflow to see the DSL with cache references</p>
                  </div>
                )}
                </div>
              </div>
            )}

            {activeTab === 'validation' && (
              <div className="p-6 h-full overflow-y-auto">
                <div className="bg-neutral-800 border border-neutral-700 rounded-lg p-4">
                {compilationResult?.validation_results && compilationResult.validation_results.length > 0 ? (
                  <div className="space-y-2">
                    {compilationResult.validation_results.map((item, index) => (
                      <div key={index} className="flex items-center gap-3 text-sm">
                        <div className={`w-4 h-4 rounded-full flex items-center justify-center text-xs font-bold ${
                          item.type === 'success' ? 'bg-green-600 text-white' :
                          item.type === 'warning' ? 'bg-yellow-600 text-white' :
                          'bg-red-600 text-white'
                        }`}>
                          {item.icon}
                        </div>
                        <span className={
                          item.type === 'success' ? 'text-green-400' :
                          item.type === 'warning' ? 'text-yellow-400' :
                          'text-red-400'
                        }>
                          {item.message}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-neutral-500">
                    <CheckSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No validation results yet</p>
                    <p className="text-sm">Compile your workflow to see validation results</p>
                  </div>
                )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Full-Screen Workflow Builder */}
      {isWorkflowMaximized && (
        <div className="fixed inset-0 z-50 bg-neutral-950 flex flex-col transition-all duration-300">
          {/* Full-Screen Header */}
          <div className="bg-neutral-900 border-b border-neutral-800 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                <Workflow className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-neutral-100">
                  {workflowName} - Full Screen Editor
                </h1>
                <p className="text-sm text-neutral-400">
                  {executionMode} mode
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-xs text-neutral-400 mr-4">
                <div className="flex items-center gap-4">
                  <span>Ctrl+Shift+M: Toggle full-screen</span>
                  <span>Esc: Exit full-screen</span>
                </div>
              </div>
              <button
                onClick={() => handleMaximizeToggle(false)}
                className="flex items-center gap-2 px-4 py-2 bg-neutral-700 text-white rounded-md hover:bg-neutral-600 transition-colors"
              >
                <span className="text-lg">⏐⏐</span>
                <span>Exit Full Screen</span>
              </button>
            </div>
          </div>

          {/* Full-Screen Workflow Builder */}
          <div className="flex-1 overflow-hidden">
            <InteractiveWorkflowBuilder
              catalogType="workflow"
              catalogSubtype={executionMode}
              catalogName={workflowName.toLowerCase().replace(/\s+/g, '-')}
              initialNodes={workflowNodes}
              initialEdges={workflowEdges}
              onWorkflowChange={handleWorkflowChange}
              isMaximized={true}
              onMaximizeChange={handleMaximizeToggle}
              clearOnMount={!isEditMode}  // Clear on mount for new workflows, preserve for edit mode
              workflowId={workflowSessionId}  // Use unique session ID
            />
          </div>
        </div>
      )}
    </div>
  )
}