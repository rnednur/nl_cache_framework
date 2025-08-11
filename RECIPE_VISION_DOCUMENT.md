# 🚀 Recipe Functionality Vision Document

## 🎯 **Executive Summary**

Transform the existing recipe system into a comprehensive **Workflow Builder** that enables users to create complex automation workflows using natural language descriptions, visual design tools, and intelligent tool mapping. This system will **extend** the current recipe infrastructure rather than replace it, providing a superset of capabilities.

## 🔍 **Current State Analysis**

### ✅ **What Already Exists (Keep & Extend)**
- **Database**: `Text2SQLCache` table with recipe-specific fields (`recipe_steps`, `required_tools`, `execution_time_estimate`, etc.)
- **Template Types**: `RECIPE`, `RECIPE_STEP`, `RECIPE_TEMPLATE`, `WORKFLOW` already in `TemplateType` enum
- **Recipe Infrastructure**: `RecipeStepAnalyzer`, `RecipeToolMapper`, `RecipeCompiler` for NL processing
- **API Endpoints**: `/v1/recipes/analyze-natural-language`, `/v1/recipes/rewrite-step`, `/v1/recipes/{recipe_id}/compile`
- **Frontend Types**: `WorkflowStep`, `WorkflowTemplate`, `ExecutionGroup` interfaces exist

### 🚀 **What We're Adding (New Workflow Layer)**
- **Enhanced DSL**: Advanced workflow definition language building on existing recipe structure
- **Visual Builder**: React Flow integration for drag-and-drop workflow design
- **NL Compiler**: Natural language to DSL compilation with real-time validation
- **Execution Engine**: Workflow execution with wiring, parallelization, and monitoring
- **Copy Flow**: Template-based cloning with JSONPatch modifications

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Builder UI                      │
├─────────────────────────────────────────────────────────────┤
│  Dashboard  │  NL Editor  │  Visual Builder  │  Monitor   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Workflow Management Layer                   │
├─────────────────────────────────────────────────────────────┤
│  NL Compiler  │  DSL Validator  │  Tool Registry  │  Executor │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Existing Recipe Infrastructure                 │
├─────────────────────────────────────────────────────────────┤
│ RecipeStepAnalyzer │ RecipeToolMapper │ RecipeCompiler     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                          │
├─────────────────────────────────────────────────────────────┤
│  New Workflow Tables  │  Existing Text2SQLCache          │
└─────────────────────────────────────────────────────────────┘
```

## 🖥️ **Screen-by-Screen Breakdown**

### **Screen 1: Dashboard (Workflow Library)**
**Purpose**: Browse, search, and manage existing workflows and recipes

**Components**:
- **Search Bar**: Global search across workflow names, descriptions, and tags
- **Workflow Cards**: Visual representation with key metrics
  - Execution count and success rate
  - Last execution timestamp
  - Complexity level and tags
  - Quick actions (Edit, Clone, Execute)
- **Filters**: By type (subflow/fullflow/copy_flow), status, tags, author
- **New Flow Button**: Quick access to workflow creation

**Integration Points**:
- **Existing**: Leverages current recipe system for basic workflows
- **New**: Enhanced metadata and execution tracking

### **Screen 2: NL Editor (Natural Language Spec)**
**Purpose**: Create workflows using natural language descriptions

**Components**:
- **Natural Language Textarea**: Free-form workflow description
- **Real-time Compilation**: Instant feedback on NL→DSL conversion
- **Validation Panel**: Shows compilation status, detected steps, wiring
- **Cost Estimation**: Predicts execution costs based on tool usage
- **Action Buttons**: Compile, Save Draft, Test Run

**Example Input**:
```
Fullflow 'Post-Incident Review':
1) Fetch Jira issues with query "project=OPS AND status=Resolved"
2) Summarize issues with LLM using Claude
3) Update Confluence page with summary

Wire: 1→2 (pass issues), 2→3 (pass summary)
```

**Integration Points**:
- **Existing**: Uses `RecipeStepAnalyzer` for step parsing
- **New**: Enhanced NL→DSL compiler with wiring detection

### **Screen 3: Visual Builder (React Flow Canvas)**
**Purpose**: Visual workflow design with drag-and-drop interface

**Components**:
- **Canvas Area**: React Flow integration for visual workflow design
- **Node Types**: Action, Decision, Loop, Subflow, AI nodes
- **Edge Management**: Visual wiring with data flow indicators
- **Auto-layout**: Automatic positioning and alignment
- **Zoom Controls**: Canvas navigation and scaling

**Node Configuration**:
- **Tool Selection**: Dropdown for available tools from registry
- **Parameter Mapping**: JSONPath expressions for data flow
- **Output Selection**: Checkbox selection for desired outputs
- **Error Handling**: Retry logic and fallback actions

**Integration Points**:
- **Existing**: Imports existing recipes as workflow steps
- **New**: Visual workflow composition and wiring

### **Screen 4: Step Configuration Panel**
**Purpose**: Detailed configuration of individual workflow steps

**Components**:
- **Tool Selection**: Dropdown with available tools (API, SQL, Function, Agent)
- **Parameter Configuration**: Input mapping and validation
- **Wiring Specification**: JSONPath expressions for data flow
- **Output Picking**: Selection of desired outputs
- **Execution Settings**: Timeout, retries, error handling

**Example Configuration**:
```json
{
  "step_id": "s2",
  "tool": "claude-3.5-sonnet",
  "prompt": "Summarize these issues: {issues}",
  "input_mapping": {
    "issues": "$.s1.output.issues"
  },
  "output_picking": ["summary"],
  "retry": {"max_attempts": 3, "delay": 1000}
}
```

**Integration Points**:
- **Existing**: Maps to current tool registry and parameter schemas
- **New**: Enhanced wiring and configuration options

### **Screen 5: Execution Monitor (Live Tracking)**
**Purpose**: Real-time workflow execution monitoring and debugging

**Components**:
- **Execution Header**: Overall workflow status and progress
- **Step List**: Individual step execution status and timing
- **Live Logs**: Real-time execution logs with timestamps
- **Performance Metrics**: Execution time, resource usage
- **Control Panel**: Pause, Cancel, Replay functionality

**Status Indicators**:
- 🟢 **Success**: Step completed successfully
- 🟡 **Running**: Step currently executing
- 🔴 **Failed**: Step encountered an error
- ⏳ **Pending**: Step waiting for dependencies

**Integration Points**:
- **Existing**: Extends current recipe execution tracking
- **New**: Real-time monitoring and debugging capabilities

### **Screen 6: Copy Flow Creator (Clone & Tweak)**
**Purpose**: Template-based workflow cloning with modifications

**Components**:
- **Base Flow Selection**: Choose existing workflow as template
- **Patch Editor**: JSONPatch operations for modifications
- **Visual Diff**: Side-by-side comparison of changes
- **Validation**: Ensure modifications maintain workflow integrity
- **Version Control**: Track changes and maintain history

**Example Patches**:
```json
[
  {"op": "replace", "path": "/steps/s1/params/timeout", "value": 60000},
  {"op": "add", "path": "/steps/s1/params/priority", "value": "High"},
  {"op": "replace", "path": "/steps/s2/refId", "value": "claude-3.5-sonnet"}
]
```

**Integration Points**:
- **Existing**: Builds on current recipe templating
- **New**: Advanced cloning with safe modifications

## 🔧 **Technical Integration Requirements**

### **Backend Extensions (New)**
```python
# New workflow models extending existing infrastructure
class Workflow(Base):
    id: UUID
    name: str
    kind: WorkflowKind  # subflow, fullflow, copy_flow
    status: WorkflowStatus  # draft, published, archived
    version: int
    dsl_json: JSONB  # Workflow DSL definition
    source_recipe_id: Optional[int]  # Reference to existing recipe
    summary: str
    created_by: str
    created_at: datetime
    updated_at: datetime

class WorkflowVersion(Base):
    id: UUID
    workflow_id: UUID
    version: int
    dsl_json: JSONB
    summary: str
    changelog: str
    published_by: str
    published_at: datetime

class WorkflowExecution(Base):
    id: UUID
    workflow_id: UUID
    status: ExecutionStatus
    inputs: JSONB
    outputs: JSONB
    logs: JSONB
    metrics: JSONB
    started_at: datetime
    finished_at: datetime
```

### **Frontend Components (New)**
- **WorkflowCanvas**: React Flow integration for visual design
- **NLWorkflowInput**: Natural language input with real-time compilation
- **WorkflowSidebar**: Step configuration and parameter mapping
- **ExecutionMonitor**: Real-time execution tracking
- **CopyFlowCreator**: Template-based cloning interface

### **API Endpoints (New)**
```python
# Workflow management
POST /v1/workflows                    # Create workflow
GET /v1/workflows/{id}               # Get workflow
PUT /v1/workflows/{id}               # Update workflow
DELETE /v1/workflows/{id}            # Delete workflow

# Workflow compilation and execution
POST /v1/workflows/compile-nl        # NL to DSL compilation
POST /v1/workflows/{id}/execute      # Execute workflow
GET /v1/workflows/{id}/executions    # Get execution history

# Copy flow operations
POST /v1/workflows/{id}/copy         # Create copy with patches
POST /v1/workflows/{id}/diff         # Generate diff between versions
```

## 🔄 **Workflow Lifecycle**

### **Design Phase**
1. **Natural Language Input**: User describes workflow in plain English
2. **NL→DSL Compilation**: AI-powered conversion to structured format
3. **Visual Design**: Drag-and-drop refinement using React Flow
4. **Configuration**: Tool selection, parameter mapping, wiring setup

### **Validation Phase**
1. **Syntax Validation**: Ensure DSL conforms to schema
2. **Tool Compatibility**: Verify all referenced tools exist and are accessible
3. **Wiring Validation**: Check data flow between steps is valid
4. **Security Review**: Validate permissions and access controls

### **Testing Phase**
1. **Mock Execution**: Test with sample data
2. **Step-by-step Debugging**: Validate individual step behavior
3. **Integration Testing**: Verify data flow between steps
4. **Performance Testing**: Measure execution time and resource usage

### **Deployment Phase**
1. **Publish Workflow**: Make available for execution
2. **Version Control**: Track changes and maintain history
3. **Access Control**: Set permissions and sharing settings
4. **Monitoring Setup**: Configure alerts and notifications

### **Execution Phase**
1. **Real-time Monitoring**: Track execution progress
2. **Error Handling**: Manage failures and retries
3. **Performance Tracking**: Monitor resource usage and timing
4. **Logging**: Maintain detailed execution logs

## 📊 **Success Metrics**

### **Design Efficiency**
- **Time to Workflow**: Minutes from NL description to executable workflow
- **Compilation Success Rate**: Percentage of NL descriptions successfully compiled
- **User Satisfaction**: Feedback scores for workflow creation experience

### **Reusability**
- **Subflow Usage**: Number of times subflows are reused in other workflows
- **Template Adoption**: Usage of pre-built workflow templates
- **Community Contribution**: User-generated workflows shared

### **Execution Quality**
- **Success Rate**: Percentage of workflow executions completing successfully
- **Performance**: Execution time compared to manual processes
- **Error Recovery**: Ability to handle and recover from failures

### **Adoption**
- **Active Users**: Number of users creating workflows monthly
- **Workflow Volume**: Total workflows created and executed
- **Tool Integration**: Number of different tools used in workflows

## 🎯 **Implementation Phases**

### **Phase 1: Foundation (Weeks 1-2)**
- [ ] Create new workflow database tables
- [ ] Define enhanced workflow DSL schema
- [ ] Implement basic workflow CRUD operations
- [ ] Set up workflow versioning system

### **Phase 2: Natural Language Compiler (Weeks 3-4)**
- [ ] Build NL→DSL compiler using existing LLM service
- [ ] Integrate with existing tool registry
- [ ] Implement real-time validation and feedback
- [ ] Create parameter extraction and mapping

### **Phase 3: Visual Builder (Weeks 5-6)**
- [ ] Integrate React Flow for visual workflow design
- [ ] Build step configuration panels
- [ ] Implement drag-and-drop workflow composition
- [ ] Create wiring and data flow visualization

### **Phase 4: Execution Engine (Weeks 7-8)**
- [ ] Develop workflow execution engine
- [ ] Implement data flow and wiring execution
- [ ] Add parallel execution and error handling
- [ ] Create execution monitoring and logging

### **Phase 5: Advanced Features (Weeks 9-10)**
- [ ] Implement copy flow functionality
- [ ] Add workflow templates and sharing
- [ ] Create execution analytics and reporting
- [ ] Integrate with existing recipe system

### **Phase 6: Integration & Testing (Weeks 11-12)**
- [ ] Update existing recipe pages with workflow integration
- [ ] End-to-end testing of complete workflow lifecycle
- [ ] Performance optimization and scaling
- [ ] User training and documentation

## 🔗 **Integration with Existing System**

### **Recipe System Compatibility**
- **Existing recipes become workflow steps**: Current recipe system continues to work
- **Bidirectional integration**: Workflows can reference recipes, recipes can reference workflows
- **Gradual migration**: Users can migrate from recipes to workflows at their own pace

### **Tool Registry Integration**
- **Unified tool discovery**: Single source of truth for available tools
- **Enhanced metadata**: Additional workflow-specific tool information
- **Permission management**: Consistent access control across recipes and workflows

### **API Compatibility**
- **Backward compatibility**: Existing recipe endpoints continue to function
- **Enhanced endpoints**: New workflow endpoints extend current functionality
- **Unified response formats**: Consistent data structures across recipes and workflows

## 🚀 **Next Steps**

1. **Review and refine** this vision document based on stakeholder feedback
2. **Begin Phase 1 implementation** with database schema and basic models
3. **Establish feedback loops** for continuous improvement
4. **Create prototypes** of key components (NL compiler, visual builder)
5. **Plan user testing** and validation of workflow creation experience

---

*This vision document outlines the transformation of the existing recipe system into a comprehensive workflow builder while maintaining backward compatibility and leveraging existing infrastructure.*
