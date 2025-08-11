# 🛠️ Implementation Plan: Workflow Builder

## 🎯 Quick Start Implementation Path

### Phase 1: Core Infrastructure (Weeks 1-2)

#### 1.1 Database Schema Setup
```sql
-- Create workflow tables
CREATE TABLE workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  kind VARCHAR(50) NOT NULL CHECK (kind IN ('subflow', 'fullflow', 'copy_flow')),
  status VARCHAR(50) NOT NULL DEFAULT 'draft',
  version INTEGER NOT NULL DEFAULT 1,
  dsl_json JSONB NOT NULL,
  summary TEXT,
  created_by VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_workflows_kind ON workflows(kind);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_created_by ON workflows(created_by);
```

#### 1.2 Backend Models & Schemas
```python
# thinkforge/workflow_models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class WorkflowKind(str, Enum):
    SUBFLOW = "subflow"
    FULLFLOW = "fullflow"
    COPY_FLOW = "copy_flow"

class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class WorkflowStep(BaseModel):
    id: str
    title: str
    type: str  # 'tool', 'flow', 'llm', 'http', 'branch', 'parallel'
    ref_id: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    input_map: Optional[Dict[str, str]] = None
    output_pick: Optional[List[str]] = None
    retry: Optional[Dict[str, Any]] = None
    on_error: Optional[str] = "fail"

class WorkflowEdge(BaseModel):
    from_step: str
    to_step: str
    condition: Optional[str] = None
    map: Dict[str, str]  # targetField: sourcePathOrExpr

class Workflow(BaseModel):
    id: str
    name: str
    kind: WorkflowKind
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    steps: List[WorkflowStep]
    edges: List[WorkflowEdge] = Field(default_factory=list)
    version: int = 1
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### 1.3 Basic API Endpoints
```python
# backend/app.py - Add these endpoints

@app.post("/v1/workflows", response_model=Workflow)
async def create_workflow(workflow: Workflow, db: Session = Depends(get_db)):
    """Create a new workflow."""
    pass

@app.get("/v1/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Get workflow by ID."""
    pass

@app.put("/v1/workflows/{workflow_id}", response_model=Workflow)
async def update_workflow(workflow_id: str, workflow: Workflow, db: Session = Depends(get_db)):
    """Update existing workflow."""
    pass

@app.delete("/v1/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Delete workflow."""
    pass
```

### Phase 2: Natural Language Compiler (Weeks 3-4)

#### 2.1 NL Parser Service
```python
# thinkforge/workflow_nl_compiler.py
from typing import List, Dict, Any
import openai
from .workflow_models import Workflow, WorkflowStep, WorkflowEdge

class WorkflowNLCompiler:
    """Compiles natural language descriptions to workflow DSL."""
    
    def __init__(self, openai_api_key: str):
        self.client = openai.OpenAI(api_key=openai_api_key)
    
    async def compile_nl_to_workflow(
        self, 
        nl_description: str, 
        workflow_name: str,
        available_tools: List[Dict[str, Any]]
    ) -> Workflow:
        """Convert NL description to workflow DSL."""
        
        # Create system prompt with available tools
        system_prompt = self._build_system_prompt(available_tools)
        
        # User prompt with workflow description
        user_prompt = f"""
        Create a workflow called "{workflow_name}" with the following description:
        
        {nl_description}
        
        Please output a valid JSON workflow definition that follows the DSL schema.
        """
        
        # Call OpenAI with structured output
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Parse and validate response
        workflow_json = json.loads(response.choices[0].message.content)
        return self._validate_and_enhance_workflow(workflow_json, available_tools)
    
    def _build_system_prompt(self, available_tools: List[Dict[str, Any]]) -> str:
        """Build system prompt with tool registry context."""
        tools_context = "\n".join([
            f"- {tool['name']}: {tool['description']} (type: {tool['type']})"
            for tool in available_tools
        ])
        
        return f"""
        You are a workflow compiler that converts natural language descriptions to workflow DSL.
        
        Available tools:
        {tools_context}
        
        Output a valid JSON workflow definition with this structure:
        {{
            "name": "string",
            "kind": "subflow|fullflow|copy_flow",
            "steps": [
                {{
                    "id": "string",
                    "title": "string", 
                    "type": "tool|flow|llm|http|branch|parallel",
                    "ref_id": "string (tool name)",
                    "params": {{}},
                    "input_map": {{}},
                    "output_pick": []
                }}
            ],
            "edges": [
                {{
                    "from_step": "step_id",
                    "to_step": "step_id",
                    "map": {{"target_field": "source_path"}}
                }}
            ]
        }}
        """
```

#### 2.2 Tool Registry Integration
```python
# thinkforge/workflow_tool_registry.py
from typing import List, Dict, Any
from .controller import Text2SQLController

class WorkflowToolRegistry:
    """Manages available tools for workflow compilation."""
    
    def __init__(self, controller: Text2SQLController):
        self.controller = controller
    
    async def get_available_tools(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get available tools for workflow compilation."""
        # Use existing similarity search to find relevant tools
        tools = []
        
        # Get tools by type
        sql_tools = await self._get_tools_by_type("sql")
        api_tools = await self._get_tools_by_type("api")
        function_tools = await self._get_tools_by_type("function")
        
        tools.extend(sql_tools)
        tools.extend(api_tools)
        tools.extend(function_tools)
        
        return tools
    
    async def _get_tools_by_type(self, tool_type: str) -> List[Dict[str, Any]]:
        """Get tools filtered by type."""
        # Use existing controller methods
        pass
```

### Phase 3: Frontend Workflow Builder (Weeks 5-6)

#### 3.1 Workflow Canvas Component
```typescript
// frontend/app/components/WorkflowCanvas.tsx
'use client'

import React, { useState, useCallback } from 'react'
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { WorkflowNode } from './WorkflowNode'
import { WorkflowSidebar } from './WorkflowSidebar'

const nodeTypes = {
  workflowNode: WorkflowNode,
}

interface WorkflowCanvasProps {
  workflow: Workflow
  onWorkflowChange: (workflow: Workflow) => void
}

export function WorkflowCanvas({ workflow, onWorkflowChange }: WorkflowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

  // Convert workflow DSL to ReactFlow format
  const workflowToFlow = useCallback((workflow: Workflow) => {
    const flowNodes: Node[] = workflow.steps.map((step, index) => ({
      id: step.id,
      type: 'workflowNode',
      position: { x: index * 200, y: index * 100 },
      data: { step, workflow },
    }))

    const flowEdges: Edge[] = workflow.edges.map((edge) => ({
      id: `${edge.from_step}-${edge.to_step}`,
      source: edge.from_step,
      target: edge.to_step,
      data: edge,
    }))

    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [setNodes, setEdges])

  // Convert ReactFlow back to workflow DSL
  const flowToWorkflow = useCallback(() => {
    const steps = nodes.map((node) => node.data.step)
    const edges = edges.map((edge) => edge.data)

    const updatedWorkflow = {
      ...workflow,
      steps,
      edges,
    }

    onWorkflowChange(updatedWorkflow)
  }, [nodes, edges, workflow, onWorkflowChange])

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge(params, eds))
      flowToWorkflow()
    },
    [setEdges, flowToWorkflow]
  )

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
      >
        <Controls />
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>
      
      {selectedNode && (
        <WorkflowSidebar
          node={selectedNode}
          onNodeUpdate={(updatedNode) => {
            // Update node and workflow
          }}
        />
      )}
    </div>
  )
}
```

#### 3.2 Natural Language Input Component
```typescript
// frontend/app/components/NLWorkflowInput.tsx
'use client'

import React, { useState } from 'react'
import { Button } from '@/app/components/ui/button'
import { Textarea } from '@/app/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card'
import { Loader2, Sparkles } from 'lucide-react'

interface NLWorkflowInputProps {
  onWorkflowGenerated: (workflow: Workflow) => void
}

export function NLWorkflowInput({ onWorkflowGenerated }: NLWorkflowInputProps) {
  const [nlDescription, setNlDescription] = useState('')
  const [isCompiling, setIsCompiling] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])

  const handleCompile = async () => {
    if (!nlDescription.trim()) return

    setIsCompiling(true)
    try {
      const response = await fetch('/api/v1/workflows/compile-nl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: nlDescription }),
      })

      if (response.ok) {
        const workflow = await response.json()
        onWorkflowGenerated(workflow)
      }
    } catch (error) {
      console.error('Failed to compile workflow:', error)
    } finally {
      setIsCompiling(false)
    }
  }

  const exampleDescriptions = [
    "Create a workflow that fetches Jira issues, summarizes them with AI, and updates Confluence",
    "Build a data pipeline that extracts data from API, transforms it, and loads to database",
    "Automate incident response: detect issue, notify team, create ticket, and track resolution"
  ]

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          Natural Language Workflow Builder
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">
            Describe your workflow in natural language:
          </label>
          <Textarea
            value={nlDescription}
            onChange={(e) => setNlDescription(e.target.value)}
            placeholder="e.g., Create a workflow that fetches Jira issues, summarizes them with AI, and updates Confluence..."
            className="min-h-[120px]"
          />
        </div>

        <div className="flex gap-2">
          <Button 
            onClick={handleCompile} 
            disabled={isCompiling || !nlDescription.trim()}
            className="flex items-center gap-2"
          >
            {isCompiling ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Generate Workflow
          </Button>
        </div>

        <div>
          <h4 className="text-sm font-medium mb-2">Example Descriptions:</h4>
          <div className="space-y-2">
            {exampleDescriptions.map((example, index) => (
              <button
                key={index}
                onClick={() => setNlDescription(example)}
                className="text-sm text-blue-600 hover:text-blue-800 text-left block w-full"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### Phase 4: Execution Engine (Weeks 7-8)

#### 4.1 Workflow Executor
```python
# thinkforge/workflow_executor.py
import asyncio
from typing import Dict, Any, List
from .workflow_models import Workflow, WorkflowStep, WorkflowEdge

class WorkflowExecutor:
    """Executes workflows with support for wiring and parallel execution."""
    
    def __init__(self):
        self.execution_context = {}
    
    async def execute_workflow(
        self, 
        workflow: Workflow, 
        inputs: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a workflow with given inputs."""
        
        # Initialize execution context
        self.execution_context = inputs or {}
        
        # Build execution DAG
        dag = self._build_execution_dag(workflow)
        
        # Execute in topological order
        results = {}
        for step_id in dag.execution_order:
            step = next(s for s in workflow.steps if s.id == step_id)
            step_result = await self._execute_step(step, workflow, results)
            results[step_id] = step_result
        
        return {
            'workflow_id': workflow.id,
            'status': 'completed',
            'results': results,
            'summary': self._generate_summary(results)
        }
    
    def _build_execution_dag(self, workflow: Workflow):
        """Build directed acyclic graph for execution order."""
        # Implementation for topological sorting
        pass
    
    async def _execute_step(
        self, 
        step: WorkflowStep, 
        workflow: Workflow, 
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""
        
        # Map inputs from previous steps
        step_inputs = self._map_step_inputs(step, previous_results)
        
        # Execute based on step type
        if step.type == 'tool':
            return await self._execute_tool_step(step, step_inputs)
        elif step.type == 'flow':
            return await self._execute_subflow_step(step, step_inputs)
        elif step.type == 'llm':
            return await self._execute_llm_step(step, step_inputs)
        else:
            raise ValueError(f"Unsupported step type: {step.type}")
    
    def _map_step_inputs(
        self, 
        step: WorkflowStep, 
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map inputs from previous step results using input_map."""
        if not step.input_map:
            return {}
        
        mapped_inputs = {}
        for target_field, source_path in step.input_map.items():
            # Parse JSONPath expression
            value = self._extract_value_from_path(source_path, previous_results)
            mapped_inputs[target_field] = value
        
        return mapped_inputs
```

### Phase 5: Integration & Testing (Weeks 9-10)

#### 5.1 Update Existing Recipe Pages
```typescript
// frontend/app/(dashboard)/recipes/page.tsx - Add workflow builder button
import { NLWorkflowInput } from '@/app/components/NLWorkflowInput'
import { WorkflowCanvas } from '@/app/components/WorkflowCanvas'

export default function Recipes() {
  const [showWorkflowBuilder, setShowWorkflowBuilder] = useState(false)
  const [currentWorkflow, setCurrentWorkflow] = useState<Workflow | null>(null)

  // ... existing code ...

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Recipes & Workflows</h1>
        <div className="flex gap-2">
          <Button onClick={() => setShowWorkflowBuilder(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Workflow
          </Button>
          <Button onClick={() => router.push('/recipes/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Recipe
          </Button>
        </div>
      </div>

      {showWorkflowBuilder ? (
        <div className="space-y-6">
          <Button 
            variant="outline" 
            onClick={() => setShowWorkflowBuilder(false)}
          >
            ← Back to Recipes
          </Button>
          
          {!currentWorkflow ? (
            <NLWorkflowInput onWorkflowGenerated={setCurrentWorkflow} />
          ) : (
            <div className="h-[600px] border rounded-lg">
              <WorkflowCanvas 
                workflow={currentWorkflow}
                onWorkflowChange={setCurrentWorkflow}
              />
            </div>
          )}
        </div>
      ) : (
        // ... existing recipe list code ...
      )}
    </div>
  )
}
```

#### 5.2 API Integration
```python
# backend/app.py - Add workflow compilation endpoint

@app.post("/v1/workflows/compile-nl")
async def compile_nl_to_workflow(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Compile natural language description to workflow DSL."""
    
    try:
        # Initialize components
        controller = Text2SQLController(db_session=db)
        tool_registry = WorkflowToolRegistry(controller)
        compiler = WorkflowNLCompiler(openai_api_key=settings.OPENAI_API_KEY)
        
        # Get available tools
        available_tools = await tool_registry.get_available_tools()
        
        # Compile NL to workflow
        workflow = await compiler.compile_nl_to_workflow(
            nl_description=request['description'],
            workflow_name=request.get('name', 'Generated Workflow'),
            available_tools=available_tools
        )
        
        return workflow
        
    except Exception as e:
        logger.error(f"Failed to compile workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## 🚀 Quick Start Commands

```bash
# 1. Create database tables
psql -d your_database -f dbscripts/create_workflow_tables.sql

# 2. Install frontend dependencies
cd frontend
npm install reactflow @monaco-editor/react

# 3. Test the workflow builder
cd backend
python -m pytest tests/test_workflow_builder.py

# 4. Start development
cd backend && python app.py &
cd frontend && npm run dev
```

## 🔧 Configuration

Add to your `.env` file:
```bash
# Workflow Builder Settings
WORKFLOW_BUILDER_ENABLED=true
WORKFLOW_MAX_STEPS=50
WORKFLOW_MAX_COMPLEXITY=10
WORKFLOW_EXECUTION_TIMEOUT=3600
```

## 📋 Next Steps

1. **Review Vision Document**: Ensure alignment with team goals
2. **Start Phase 1**: Set up database schema and basic models
3. **Prototype NL Compiler**: Test with simple workflow examples
4. **Build Frontend Canvas**: Create basic workflow visualization
5. **Iterate & Refine**: Gather feedback and improve implementation

This implementation plan provides a concrete path from the current recipe system to a full-featured workflow builder while leveraging existing infrastructure and maintaining code quality.
