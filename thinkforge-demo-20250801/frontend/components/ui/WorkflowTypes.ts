/**
 * Workflow Template Types for the workflow builder
 */

// Execution mode for steps
export enum ExecutionMode {
  SEQUENTIAL = "sequential",
  PARALLEL = "parallel"
}

// Reference to output from previous step
export interface StepOutputRef {
  source: string;      // ID of the source step
  key: string;         // Output key from the source step
  type: "placeholder"; // Marker to indicate this is a placeholder
}

// Input type (can be a literal value or reference to another step's output)
export type StepInput = string | number | boolean | null | StepOutputRef;

// A single step in the workflow
export interface WorkflowStep {
  id: string;
  templateType: string;               // e.g., "sql", "api", "transform"
  inputs: Record<string, StepInput>;  // Input values or placeholders
  dependencies: string[];             // IDs of steps this step depends on
  outputKey: string;                  // Key to store this step's output
  metadata?: Record<string, any>;     // Additional configuration
}

// A group of steps to be executed together
export interface ExecutionGroup {
  mode: ExecutionMode;  // Sequential or parallel execution
  steps: string[];      // IDs of steps in this group
}

// Complete workflow template
export interface WorkflowTemplate {
  name: string;
  steps: Record<string, WorkflowStep>;
  executionPlan: ExecutionGroup[];
}

/**
 * Converts a ReactFlow node/edge structure to a WorkflowTemplate
 */
export function buildWorkflowFromReactFlow(
  nodes: any[], 
  edges: any[]
): WorkflowTemplate {
  // Initialize the workflow template
  const template: WorkflowTemplate = {
    name: "workflow_template",
    steps: {},
    executionPlan: []
  };

  // Map nodes to steps (excluding the start node)
  nodes.forEach(node => {
    if (node.id === "start") return;
    
    const data = node.data;
    const step: WorkflowStep = {
      id: node.id,
      templateType: data.originalStepType || "unknown",
      inputs: { template: data.template },
      dependencies: [],
      outputKey: `${node.id}_result`,
      metadata: {
        label: data.label,
        originalStepId: data.originalStepId,
        catalogType: data.catalogType,
        catalogSubtype: data.catalogSubtype,
        catalogName: data.catalogName
      }
    };
    
    template.steps[node.id] = step;
  });

  // Add dependencies from edges
  edges.forEach(edge => {
    const source = edge.source;
    const target = edge.target;
    if (source === "start" || !template.steps[target]) return;
    
    template.steps[target].dependencies.push(source);
  });

  // Build execution plan
  const buildExecutionPlan = (): ExecutionGroup[] => {
    const executionGroups: ExecutionGroup[] = [];
    const processed = new Set<string>();
    const remaining = new Set(Object.keys(template.steps));

    // Helper for creating execution groups
    const createGroups = () => {
      const parallelGroup: string[] = [];
      const sequentialGroup: string[] = [];

      remaining.forEach(stepId => {
        const step = template.steps[stepId];
        
        // Check if all dependencies are processed
        const allDependenciesProcessed = step.dependencies.every(dep => 
          processed.has(dep)
        );
        
        if (allDependenciesProcessed) {
          // Check if step can run in parallel with others in the group
          const canRunParallel = Array.from(remaining)
            .filter(id => id !== stepId)
            .every(otherId => {
              const other = template.steps[otherId];
              // No direct dependency between steps
              const noDependency = !step.dependencies.includes(otherId) && 
                                  !other.dependencies.includes(stepId);
              // No shared dependency that could cause conflicts
              const noSharedDependency = step.dependencies.every(dep => 
                !other.dependencies.includes(dep)
              );
              
              return noDependency && noSharedDependency;
            });
          
          if (canRunParallel && parallelGroup.length > 0) {
            parallelGroup.push(stepId);
          } else {
            sequentialGroup.push(stepId);
          }
        }
      });

      // Add parallel group if it exists and has more than one step
      if (parallelGroup.length > 1) {
        executionGroups.push({
          mode: ExecutionMode.PARALLEL,
          steps: parallelGroup
        });
        parallelGroup.forEach(id => {
          processed.add(id);
          remaining.delete(id);
        });
      }

      // Add sequential groups
      sequentialGroup.forEach(stepId => {
        executionGroups.push({
          mode: ExecutionMode.SEQUENTIAL,
          steps: [stepId]
        });
        processed.add(stepId);
        remaining.delete(stepId);
      });
      
      return remaining.size > 0;
    };

    // Process nodes with no dependencies first
    const noDepSteps = Object.entries(template.steps)
      .filter(([_, step]) => step.dependencies.length === 0)
      .map(([id]) => id);
    
    if (noDepSteps.length > 0) {
      // If multiple no-dependency steps, they can run in parallel
      if (noDepSteps.length > 1) {
        executionGroups.push({
          mode: ExecutionMode.PARALLEL,
          steps: noDepSteps
        });
      } else {
        executionGroups.push({
          mode: ExecutionMode.SEQUENTIAL,
          steps: noDepSteps
        });
      }
      
      noDepSteps.forEach(id => {
        processed.add(id);
        remaining.delete(id);
      });
    }

    // Process remaining steps until all are processed
    while (remaining.size > 0) {
      const hasRemaining = createGroups();
      if (!hasRemaining) break;
    }

    return executionGroups;
  };

  // Set the execution plan
  template.executionPlan = buildExecutionPlan();

  // Augment inputs with placeholders for dependencies
  Object.values(template.steps).forEach(step => {
    step.dependencies.forEach(depId => {
      const depStep = template.steps[depId];
      const placeholderKey = `${depId}_output`;
      
      step.inputs[placeholderKey] = {
        source: depId,
        key: depStep.outputKey,
        type: "placeholder"
      };
    });
  });

  return template;
}

/**
 * Serializes a ReactFlow graph to a workflow template
 */
export function serializeWorkflow(nodes: any[], edges: any[]): string {
  const template = buildWorkflowFromReactFlow(nodes, edges);
  return JSON.stringify(template, null, 2);
} 