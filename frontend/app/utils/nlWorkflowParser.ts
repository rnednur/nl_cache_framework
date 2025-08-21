import { Node, Edge } from 'reactflow'

export interface ParsedWorkflowStep {
  stepNumber: number
  description: string
  type: string
  toolRef?: string
  params?: any
}

export interface ParsedWiring {
  from: number
  to: number
  description: string
  dataMapping?: string
}

export interface ParsedWorkflow {
  name: string
  steps: ParsedWorkflowStep[]
  wiring: ParsedWiring[]
}

export interface ParserResult {
  success: boolean
  workflow?: ParsedWorkflow
  nodes?: Node[]
  edges?: Edge[]
  errors?: string[]
}

// Template type mapping based on common keywords
const detectTemplateType = (description: string): string => {
  const desc = description.toLowerCase()
  
  // DuckDB SQL patterns (check first for exact toolbox match, then other patterns)
  if (desc.includes('duckdb sql')) {
    return 'duckdb_sql'
  }
  if (desc.includes('duckdb') || desc.includes('duck db')) {
    return 'duckdb_sql'
  }
  
  // LLM Step patterns (check first for exact toolbox match, then other patterns)
  if (desc.includes('llm step')) {
    return 'llm_step'
  }
  if (desc.includes('llmstep') || desc.includes('ai step') || desc.includes('aistep') ||
      desc.includes('claude') || desc.includes('gpt') ||
      desc.includes('summarize') || desc.includes('analyze') || desc.includes('generate') ||
      desc.includes('ai') || desc.includes('openai')) {
    return 'llm_step'
  }
  
  // SQL patterns (generic database operations)
  if (desc.includes('sql') || desc.includes('select') || desc.includes('query') || 
      desc.includes('database') || desc.includes('table')) {
    return 'sql'
  }
  
  // API patterns  
  if (desc.includes('api') || desc.includes('rest') || desc.includes('endpoint') ||
      desc.includes('fetch') || desc.includes('http') || desc.includes('get') ||
      desc.includes('post') || desc.includes('request')) {
    return 'api'
  }
  
  // Script patterns
  if (desc.includes('script') || desc.includes('python') || desc.includes('javascript') ||
      desc.includes('transform') || desc.includes('process') || desc.includes('code')) {
    return 'script'
  }
  
  // Workflow patterns
  if (desc.includes('workflow') || desc.includes('automation') || desc.includes('orchestrate')) {
    return 'workflow'
  }
  
  // URL patterns
  if (desc.includes('url') || desc.includes('link') || desc.includes('redirect') ||
      desc.includes('navigate')) {
    return 'url'
  }
  
  // Configuration patterns
  if (desc.includes('config') || desc.includes('setting') || desc.includes('parameter') ||
      desc.includes('variable')) {
    return 'configuration'
  }
  
  // Default fallback
  return 'api'
}

// Extract tool reference from description
const extractToolRef = (description: string, type: string): string => {
  const desc = description.toLowerCase()
  
  // Common tool patterns
  if (desc.includes('jira')) return 'jira.search'
  if (desc.includes('confluence')) return 'confluence.update'
  if (desc.includes('slack')) return 'slack.post'
  if (desc.includes('github')) return 'github.api'
  if (desc.includes('aws')) return 'aws.cli'
  if (desc.includes('docker')) return 'docker.run'
  if (desc.includes('kubernetes') || desc.includes('k8s')) return 'kubectl'
  if (desc.includes('claude')) return 'claude-3.5-sonnet'
  if (desc.includes('gpt')) return 'gpt-4'
  
  // Default based on type
  switch (type) {
    case 'duckdb_sql': return 'duckdb.query'
    case 'llm_step': return 'llm.process'
    case 'sql': return 'database.query'
    case 'api': return 'http.request'
    case 'script': return 'python.execute'
    case 'prompt': return 'llm.completion'
    case 'workflow': return 'workflow.execute'
    default: return `${type}.execute`
  }
}

// Parse parameters from description
const extractParams = (description: string, type: string): any => {
  const params: any = {}
  
  // SQL query extraction
  const sqlMatch = description.match(/(?:query|sql)[:\s]*["']([^"']+)["']/i)
  if (sqlMatch && type === 'sql') {
    params.query = sqlMatch[1]
  }
  
  // API endpoint extraction
  const urlMatch = description.match(/(?:url|endpoint)[:\s]*["']([^"']+)["']/i)
  if (urlMatch && type === 'api') {
    params.url = urlMatch[1]
  }
  
  // Method extraction for APIs
  const methodMatch = description.match(/(?:method[:\s]*)?(?:GET|POST|PUT|DELETE|PATCH)/i)
  if (methodMatch && type === 'api') {
    params.method = methodMatch[0].toUpperCase()
  }
  
  // Project extraction (for Jira, etc.)
  const projectMatch = description.match(/project[=:\s]*([A-Z]+)/i)
  if (projectMatch) {
    params.project = projectMatch[1]
  }
  
  // Status extraction
  const statusMatch = description.match(/status[=:\s]*([A-Za-z]+)/i)
  if (statusMatch) {
    params.status = statusMatch[1]
  }
  
  return Object.keys(params).length > 0 ? params : undefined
}

// Parse natural language workflow description
export const parseNLWorkflow = (nlDescription: string): ParserResult => {
  try {
    const lines = nlDescription.trim().split('\n').map(line => line.trim()).filter(line => line.length > 0)
    
    if (lines.length === 0) {
      return { success: false, errors: ['Empty workflow description'] }
    }
    
    // Extract workflow name from first line if it follows pattern like "Fullflow 'Name':"
    let workflowName = 'Unnamed Workflow'
    const nameMatch = lines[0].match(/(?:fullflow|subflow|workflow)?\s*['"]([^'"]+)['"]:/i)
    if (nameMatch) {
      workflowName = nameMatch[1]
    }
    
    // Find steps (numbered lines like "1) Do something", "2) Do another thing")
    const steps: ParsedWorkflowStep[] = []
    const stepRegex = /^(\d+)\)\s*(.+)$/
    
    // Find wiring section (lines starting with "Wire:")
    const wiringLines: string[] = []
    let inWiringSection = false
    
    for (const line of lines) {
      if (line.toLowerCase().startsWith('wire:')) {
        inWiringSection = true
        const wiringContent = line.substring(5).trim()
        if (wiringContent) {
          wiringLines.push(wiringContent)
        }
        continue
      }
      
      if (inWiringSection) {
        wiringLines.push(line)
        continue
      }
      
      const stepMatch = line.match(stepRegex)
      if (stepMatch) {
        const stepNumber = parseInt(stepMatch[1])
        const description = stepMatch[2]
        const type = detectTemplateType(description)
        const toolRef = extractToolRef(description, type)
        const params = extractParams(description, type)
        
        steps.push({
          stepNumber,
          description,
          type,
          toolRef,
          params
        })
      }
    }
    
    // Parse wiring information
    const wiring: ParsedWiring[] = []
    const wiringText = wiringLines.join(' ')
    
    // Match patterns like "1→2", "1->2", "1 to 2", "(pass data)", etc.
    const wiringRegex = /(\d+)(?:\s*[→\-]>\s*|\s+to\s+)(\d+)(?:\s*\([^)]+\))?/g
    let wiringMatch
    
    while ((wiringMatch = wiringRegex.exec(wiringText)) !== null) {
      const from = parseInt(wiringMatch[1])
      const to = parseInt(wiringMatch[2])
      const description = wiringMatch[0]
      
      // Extract data mapping if present
      const dataMapMatch = description.match(/\(([^)]+)\)/)
      const dataMapping = dataMapMatch ? dataMapMatch[1] : undefined
      
      wiring.push({
        from,
        to,
        description,
        dataMapping
      })
    }
    
    const workflow: ParsedWorkflow = {
      name: workflowName,
      steps,
      wiring
    }
    
    // Convert to ReactFlow nodes and edges
    const nodes: Node[] = []
    const edges: Edge[] = []
    
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
    
    // Add step nodes
    const stepSpacing = 200
    steps.forEach((step, index) => {
      const node: Node = {
        id: `step-${step.stepNumber}`,
        type: 'default',
        position: { 
          x: 100 + (index % 3) * stepSpacing, 
          y: 150 + Math.floor(index / 3) * 100 
        },
        data: {
          label: `${getTemplateIcon(step.type)} ${step.description}`,
          stepNumber: step.stepNumber,
          templateType: step.type,
          toolRef: step.toolRef,
          params: step.params,
          originalDescription: step.description
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
      nodes.push(node)
    })
    
    // Add edges based on wiring
    wiring.forEach(wire => {
      const sourceId = `step-${wire.from}`
      const targetId = `step-${wire.to}`
      
      // Check if both nodes exist
      const sourceExists = nodes.some(node => node.id === sourceId)
      const targetExists = nodes.some(node => node.id === targetId)
      
      if (sourceExists && targetExists) {
        edges.push({
          id: `edge-${wire.from}-${wire.to}`,
          source: sourceId,
          target: targetId,
          animated: true,
          style: { stroke: '#10b981', strokeWidth: 2 },
          label: wire.dataMapping || '',
        })
      }
    })
    
    // If no explicit wiring, create sequential flow
    if (edges.length === 0 && steps.length > 0) {
      // Connect start to first step
      edges.push({
        id: 'edge-start-1',
        source: 'start',
        target: `step-${steps[0].stepNumber}`,
        animated: true,
        style: { stroke: '#10b981', strokeWidth: 2 },
      })
      
      // Connect steps sequentially
      for (let i = 0; i < steps.length - 1; i++) {
        edges.push({
          id: `edge-${steps[i].stepNumber}-${steps[i + 1].stepNumber}`,
          source: `step-${steps[i].stepNumber}`,
          target: `step-${steps[i + 1].stepNumber}`,
          animated: true,
          style: { stroke: '#10b981', strokeWidth: 2 },
        })
      }
    }
    
    return {
      success: true,
      workflow,
      nodes,
      edges
    }
    
  } catch (error) {
    return {
      success: false,
      errors: [`Parsing failed: ${error instanceof Error ? error.message : 'Unknown error'}`]
    }
  }
}

// Helper functions for template styling
const getTemplateIcon = (templateType: string): string => {
  const iconMap: Record<string, string> = {
    duckdb_sql: '⚫🟡',
    llm_step: '✨',
    sql: '🗄️',
    api: '🌐',
    workflow: '⚡',
    script: '📜',
    url: '🔗',
    cli: '💻',
    prompt: '🤖',
    configuration: '⚙️',
    graphql: '📊',
    nosql: '🍃',
  }
  return iconMap[templateType] || '📋'
}

const getTemplateColor = (templateType: string): string => {
  const colorMap: Record<string, string> = {
    duckdb_sql: '#0891b2',
    llm_step: '#be185d',
    sql: '#3b82f6',
    api: '#10b981',
    workflow: '#8b5cf6',
    script: '#f59e0b',
    url: '#06b6d4',
    cli: '#6b7280',
    prompt: '#ec4899',
    configuration: '#84cc16',
    graphql: '#f97316',
    nosql: '#14b8a6',
  }
  return colorMap[templateType] || '#6b7280'
}

// Generate natural language description from parsed workflow
export const generateNLFromWorkflow = (workflow: ParsedWorkflow): string => {
  let nl = `Fullflow '${workflow.name}':\n`
  
  // Add steps
  workflow.steps.forEach(step => {
    nl += `${step.stepNumber}) ${step.description}\n`
  })
  
  // Add wiring section if there are connections
  if (workflow.wiring.length > 0) {
    nl += '\nWire: '
    const wiringStrings = workflow.wiring.map(wire => {
      let wiringStr = `${wire.from}→${wire.to}`
      if (wire.dataMapping) {
        wiringStr += ` (${wire.dataMapping})`
      }
      return wiringStr
    })
    nl += wiringStrings.join(', ')
  }
  
  return nl
}