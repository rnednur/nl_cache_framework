import { Node, Edge } from 'reactflow'
import { generateNLFromWorkflow, type ParsedWorkflow, type ParsedWorkflowStep, type ParsedWiring } from './nlWorkflowParser'

export interface WorkflowToNLOptions {
  includeWiring?: boolean
  preserveOrder?: boolean
  includeMetadata?: boolean
}

// Convert ReactFlow nodes and edges back to natural language description
export const convertWorkflowToNL = (
  nodes: Node[], 
  edges: Edge[], 
  workflowName?: string,
  options: WorkflowToNLOptions = {}
): string => {
  const {
    includeWiring = true,
    preserveOrder = true,
    includeMetadata = false
  } = options

  try {
    // Filter out the start node and extract step nodes
    const stepNodes = nodes.filter(node => 
      node.id !== 'start' && 
      node.data && 
      (node.data.stepNumber || node.data.originalDescription || node.data.label)
    )

    if (stepNodes.length === 0) {
      return workflowName ? `Fullflow '${workflowName}': (No steps defined)` : 'Empty workflow'
    }

    // Sort nodes by step number if available, otherwise by position or creation order
    const sortedNodes = preserveOrder ? 
      stepNodes.sort((a, b) => {
        // First try to sort by step number
        if (a.data?.stepNumber && b.data?.stepNumber) {
          return a.data.stepNumber - b.data.stepNumber
        }
        
        // Then by Y position (top to bottom)
        if (a.position?.y && b.position?.y) {
          return a.position.y - b.position.y
        }
        
        // Finally by X position (left to right)  
        if (a.position?.x && b.position?.x) {
          return a.position.x - b.position.x
        }
        
        return 0
      }) : stepNodes

    // Convert nodes to parsed workflow steps
    const steps: ParsedWorkflowStep[] = sortedNodes.map((node, index) => {
      const stepNumber = node.data?.stepNumber || (index + 1)
      const description = node.data?.originalDescription || 
                         node.data?.label?.replace(/^[^\s]+ /, '') || // Remove icon prefix
                         `Step ${stepNumber}`
      
      const type = node.data?.templateType || 
                   node.data?.originalStepType ||
                   detectTypeFromLabel(node.data?.label || '') ||
                   'api'

      return {
        stepNumber,
        description: cleanDescription(description),
        type,
        toolRef: node.data?.toolRef,
        params: node.data?.params,
        cacheId: node.data?.cacheEntryId,
        nodeId: node.id,
        template: node.data?.template
      }
    })

    // Convert edges to wiring relationships if requested
    const wiring: ParsedWiring[] = []
    if (includeWiring && edges.length > 0) {
      edges.forEach(edge => {
        // Find source and target step numbers
        const sourceNode = sortedNodes.find(node => node.id === edge.source)
        const targetNode = sortedNodes.find(node => node.id === edge.target)
        
        if (sourceNode && targetNode) {
          const fromStep = sourceNode.data?.stepNumber || 
                          sortedNodes.indexOf(sourceNode) + 1
          const toStep = targetNode.data?.stepNumber || 
                        sortedNodes.indexOf(targetNode) + 1
          
          wiring.push({
            from: fromStep,
            to: toStep,
            description: edge.label || `${fromStep}→${toStep}`,
            dataMapping: edge.label || undefined
          })
        }
      })
    }

    // Create parsed workflow object
    const workflow: ParsedWorkflow = {
      name: workflowName || 'Generated Workflow',
      steps,
      wiring: includeWiring ? wiring : []
    }

    // Generate natural language description
    let nlDescription = generateNLFromWorkflow(workflow)

    // Add metadata if requested
    if (includeMetadata) {
      nlDescription += `\n\n// Generated from visual workflow with ${nodes.length} nodes and ${edges.length} connections`
    }

    return nlDescription

  } catch (error) {
    console.error('Failed to convert workflow to NL:', error)
    return `Error: Failed to convert workflow to natural language - ${error instanceof Error ? error.message : 'Unknown error'}`
  }
}

// Helper function to detect template type from node label
const detectTypeFromLabel = (label: string): string => {
  const labelLower = label.toLowerCase()
  
  if (labelLower.includes('🗄️') || labelLower.includes('sql') || labelLower.includes('database')) {
    return 'sql'
  }
  if (labelLower.includes('🌐') || labelLower.includes('api') || labelLower.includes('http')) {
    return 'api'
  }
  if (labelLower.includes('🤖') || labelLower.includes('llm') || labelLower.includes('ai')) {
    return 'prompt'
  }
  if (labelLower.includes('📜') || labelLower.includes('script') || labelLower.includes('code')) {
    return 'script'
  }
  if (labelLower.includes('⚡') || labelLower.includes('workflow')) {
    return 'workflow'
  }
  if (labelLower.includes('🔗') || labelLower.includes('url') || labelLower.includes('link')) {
    return 'url'
  }
  if (labelLower.includes('⚙️') || labelLower.includes('config')) {
    return 'configuration'
  }
  
  return 'api' // Default fallback
}

// Clean up description text (remove icons, formatting, etc.)
const cleanDescription = (description: string): string => {
  return description
    .replace(/^[^\w\s]+\s*/, '') // Remove leading icons/symbols
    .replace(/\([^)]*\)$/g, '') // Remove trailing parentheses
    .trim()
}

// Generate executable workflow format with cache ID references
export const generateExecutableWorkflow = (nodes: Node[], edges: Edge[], workflowName?: string) => {
  const dslResult = convertWorkflowToDSL(nodes, edges, workflowName)
  
  if (!dslResult.success || !dslResult.dsl) {
    return {
      success: false,
      error: dslResult.error || 'Failed to generate DSL',
      workflow: null
    }
  }

  const { workflow } = dslResult.dsl
  
  // Create an executable format that emphasizes cache ID usage
  const executableSteps = workflow.steps.map(step => ({
    id: step.id,
    name: step.name,
    action: {
      type: 'cache_template_execution',
      cache_id: step.cache_id,
      template_type: step.type,
      fallback_template: step.template,
      parameters: step.parameters
    },
    position: step.position,
    metadata: {
      original_node_id: step.node_id,
      description: step.description
    }
  }))

  const executableWorkflow = {
    id: workflow.id,
    name: workflow.name,
    version: workflow.version,
    execution_mode: 'sequential',
    steps: executableSteps,
    flow_control: workflow.edges.map(edge => ({
      from: edge.from,
      to: edge.to,
      condition: edge.label || 'always',
      data_mapping: 'auto'
    })),
    cache_dependencies: workflow.metadata.cache_ids.filter(Boolean),
    runtime_info: {
      total_steps: executableSteps.length,
      cache_referenced_steps: executableSteps.filter(s => s.action.cache_id).length,
      template_types: workflow.metadata.template_types
    }
  }

  return {
    success: true,
    workflow: executableWorkflow,
    validation_notes: [
      `${executableWorkflow.runtime_info.cache_referenced_steps} steps reference cache entries`,
      `${executableWorkflow.runtime_info.total_steps - executableWorkflow.runtime_info.cache_referenced_steps} steps need manual template definition`
    ]
  }
}

// Generate a summary of the workflow structure
export const generateWorkflowSummary = (nodes: Node[], edges: Edge[]): string => {
  const stepNodes = nodes.filter(node => node.id !== 'start')
  const totalSteps = stepNodes.length
  const totalConnections = edges.length
  
  const stepTypes = stepNodes.reduce((acc, node) => {
    const type = node.data?.templateType || node.data?.originalStepType || 'unknown'
    acc[type] = (acc[type] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  let summary = `Workflow contains ${totalSteps} steps with ${totalConnections} connections.\n`
  
  if (Object.keys(stepTypes).length > 0) {
    summary += 'Step types: ' + Object.entries(stepTypes)
      .map(([type, count]) => `${count} ${type}`)
      .join(', ')
  }
  
  return summary
}

// Validate workflow structure
export const validateWorkflowStructure = (nodes: Node[], edges: Edge[]): {
  isValid: boolean
  warnings: string[]
  errors: string[]
} => {
  const warnings: string[] = []
  const errors: string[] = []
  
  const stepNodes = nodes.filter(node => node.id !== 'start')
  
  // Check for empty workflow
  if (stepNodes.length === 0) {
    errors.push('Workflow has no steps defined')
  }
  
  // Check for disconnected nodes
  const connectedNodeIds = new Set([
    ...edges.map(edge => edge.source),
    ...edges.map(edge => edge.target)
  ])
  
  const disconnectedNodes = stepNodes.filter(node => 
    !connectedNodeIds.has(node.id)
  )
  
  if (disconnectedNodes.length > 0) {
    warnings.push(`${disconnectedNodes.length} nodes are not connected to the workflow`)
  }
  
  // Check for nodes with missing data
  const nodesWithMissingData = stepNodes.filter(node => 
    !node.data || (!node.data.label && !node.data.originalDescription)
  )
  
  if (nodesWithMissingData.length > 0) {
    warnings.push(`${nodesWithMissingData.length} nodes have incomplete data`)
  }
  
  // Check for circular dependencies (basic check)
  const hasCircularDep = checkCircularDependencies(nodes, edges)
  if (hasCircularDep) {
    warnings.push('Potential circular dependencies detected in workflow')
  }
  
  return {
    isValid: errors.length === 0,
    warnings,
    errors
  }
}

// Simple circular dependency check
const checkCircularDependencies = (nodes: Node[], edges: Edge[]): boolean => {
  const graph = new Map<string, string[]>()
  
  // Build adjacency list
  edges.forEach(edge => {
    if (!graph.has(edge.source)) {
      graph.set(edge.source, [])
    }
    graph.get(edge.source)!.push(edge.target)
  })
  
  // DFS to detect cycles
  const visited = new Set<string>()
  const recursionStack = new Set<string>()
  
  const hasCycle = (node: string): boolean => {
    if (recursionStack.has(node)) return true
    if (visited.has(node)) return false
    
    visited.add(node)
    recursionStack.add(node)
    
    const neighbors = graph.get(node) || []
    for (const neighbor of neighbors) {
      if (hasCycle(neighbor)) return true
    }
    
    recursionStack.delete(node)
    return false
  }
  
  for (const node of nodes) {
    if (!visited.has(node.id) && hasCycle(node.id)) {
      return true
    }
  }
  
  return false
}

// Convert workflow to DSL format with cache IDs
export const convertWorkflowToDSL = (nodes: Node[], edges: Edge[], workflowName?: string) => {
  try {
    // Filter out the start node
    const stepNodes = nodes.filter(node => node.id !== 'start')
    
    if (stepNodes.length === 0) {
      return {
        success: false,
        error: 'No workflow steps defined',
        dsl: null
      }
    }

    // Sort nodes by position (top to bottom, left to right)
    const sortedNodes = stepNodes.sort((a, b) => {
      if (a.position?.y && b.position?.y) {
        const yDiff = a.position.y - b.position.y
        if (Math.abs(yDiff) > 50) return yDiff // Different rows
        return (a.position.x || 0) - (b.position.x || 0) // Same row, sort by x
      }
      return 0
    })

    // Create DSL steps with cache IDs
    const dslSteps = sortedNodes.map((node, index) => ({
      id: `step_${index + 1}`,
      name: node.data?.label?.replace(/^[^\s]+ /, '') || `Step ${index + 1}`,
      type: node.data?.templateType || 'api',
      cache_id: node.data?.cacheEntryId || null,
      node_id: node.id,
      template: node.data?.template || null,
      position: node.position,
      description: node.data?.label || `Step ${index + 1}`,
      parameters: node.data?.params || {}
    }))

    // Create DSL edges
    const dslEdges = edges.map(edge => {
      const sourceNode = sortedNodes.find(n => n.id === edge.source)
      const targetNode = sortedNodes.find(n => n.id === edge.target)
      const sourceIndex = sourceNode ? sortedNodes.indexOf(sourceNode) : -1
      const targetIndex = targetNode ? sortedNodes.indexOf(targetNode) : -1
      
      return {
        from: sourceIndex >= 0 ? `step_${sourceIndex + 1}` : edge.source,
        to: targetIndex >= 0 ? `step_${targetIndex + 1}` : edge.target,
        source_node_id: edge.source,
        target_node_id: edge.target,
        label: edge.label || null
      }
    })

    // Build the complete DSL
    const dsl = {
      workflow: {
        id: workflowName?.toLowerCase().replace(/[^a-z0-9]/g, '_') || 'generated_workflow',
        name: workflowName || 'Generated Workflow',
        type: 'fullflow',
        version: '1.0',
        created_at: new Date().toISOString(),
        steps: dslSteps,
        edges: dslEdges,
        metadata: {
          node_count: stepNodes.length,
          edge_count: edges.length,
          has_cache_references: dslSteps.some(step => step.cache_id),
          cache_ids: dslSteps.filter(step => step.cache_id).map(step => step.cache_id),
          template_types: [...new Set(dslSteps.map(step => step.type))]
        }
      }
    }

    return {
      success: true,
      dsl,
      stats: {
        steps_count: dslSteps.length,
        edges_count: dslEdges.length,
        cache_references: dslSteps.filter(step => step.cache_id).length,
        template_types: dsl.workflow.metadata.template_types
      }
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      dsl: null
    }
  }
}