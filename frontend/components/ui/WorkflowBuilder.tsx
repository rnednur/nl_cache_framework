'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  addEdge,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  Connection,
  BackgroundVariant,
  ReactFlowProvider,
  useReactFlow,
  Panel,
  getConnectedEdges,
  getNodesBounds,
  GetViewport,
} from 'reactflow';

// Comment out the CSS import since we've added it to globals.css
// import 'reactflow/dist/style.css';
import { CompatibleStep } from './StepPalette';
import BottomStepPalette from './BottomStepPalette';
import api, { CacheItem } from '../../app/services/api';
import { Button } from '../../app/components/ui/button';
import { Wand2, Trash2, Upload, FileText } from 'lucide-react';
import GenerateWorkflowDialog from './GenerateWorkflowDialog';
import RecipeImportDialog from './RecipeImportDialog';

// Default initial node if no workflow data is provided
const defaultInitialNodes: Node[] = [
  {
    id: 'start',
    type: 'input',
    data: { label: 'Workflow Start' },
    position: { x: 250, y: 50 },
  },
];

interface WorkflowBuilderProps {
  catalogType?: string;
  catalogSubType?: string;
  catalogName?: string;
  initialNodes?: Node[];
  initialEdges?: Edge[];
  onWorkflowChange?: (nodes: Node[], edges: Edge[]) => void;
}

let id = 1; // Simple ID generator for new nodes
const getNextNodeId = () => `dndnode_${id++}`;

const WorkflowBuilderComponent: React.FC<WorkflowBuilderProps> = ({
  catalogType,
  catalogSubType,
  catalogName,
  initialNodes: propInitialNodes,
  initialEdges: propInitialEdges,
  onWorkflowChange,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null); // Ref for the wrapper div
  const { screenToFlowPosition } = useReactFlow(); // Hook for coordinate conversion

  const [nodes, setNodes, onNodesChange] = useNodesState(propInitialNodes || defaultInitialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(propInitialEdges || []);
  const [compatibleSteps, setCompatibleSteps] = useState<CompatibleStep[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isGenerateDialogOpen, setIsGenerateDialogOpen] = useState<boolean>(false);
  const [isRecipeImportDialogOpen, setIsRecipeImportDialogOpen] = useState<boolean>(false);

  // Refs to store the previous initial props to compare against
  const prevPropInitialNodesRef = useRef<Node[] | undefined>();
  const prevPropInitialEdgesRef = useRef<Edge[] | undefined>();
  const onWorkflowChangeRef = useRef(onWorkflowChange);

  useEffect(() => {
    // Keep the ref updated with the latest callback from props
    onWorkflowChangeRef.current = onWorkflowChange;
  }, [onWorkflowChange]);

  useEffect(() => {
    const propNodesChanged = 
      JSON.stringify(propInitialNodes || defaultInitialNodes) !== 
      JSON.stringify(prevPropInitialNodesRef.current || defaultInitialNodes);

    const propEdgesChanged = 
      JSON.stringify(propInitialEdges || []) !== 
      JSON.stringify(prevPropInitialEdgesRef.current || []);

    if (propNodesChanged) {
      setNodes(propInitialNodes || defaultInitialNodes);
    }

    if (propEdgesChanged) {
      setEdges(propInitialEdges || []);
    }

    // Update refs for the next render
    prevPropInitialNodesRef.current = propInitialNodes;
    prevPropInitialEdgesRef.current = propInitialEdges;
  }, [propInitialNodes, propInitialEdges, setNodes, setEdges]);

  // Fetch compatible cache entries for workflow steps
  useEffect(() => {
    // Get IDs of nodes to exclude (avoid adding a step that's already in the workflow)
    const excludeIds = nodes
      .filter(node => node.data?.originalStepId)
      .map(node => Number(node.data.originalStepId));
      
    const fetchCompatibleEntries = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const cacheEntries = await api.getCompatibleCacheEntries(
          catalogType,
          catalogSubType,
          catalogName,
          excludeIds
        );
        
        // Map CacheItem objects to CompatibleStep objects
        const steps: CompatibleStep[] = cacheEntries.map((entry: CacheItem) => ({
          id: entry.id.toString(),
          name: entry.nl_query || `${entry.template_type} Template`,
          type: entry.template_type,
          data: {
            template: entry.template,
            catalogType: entry.catalog_type,
            catalogSubtype: entry.catalog_subtype,
            catalogName: entry.catalog_name,
            // Include any other relevant data from the cache entry
          }
        }));
        
        setCompatibleSteps(steps);
      } catch (err) {
        console.error('Failed to fetch compatible steps:', err);
        setError('Failed to load compatible steps. Please try again.');
        
        // Fallback to simulated data for demo purposes
        // Remove this in production
        const simulatedSteps: CompatibleStep[] = [
          {
            id: 'cache-entry-1',
            name: 'Fetch User Data (Demo)',
            type: 'api',
            data: { url: '/api/users/{{userId}}', method: 'GET' },
          },
          {
            id: 'cache-entry-2',
            name: 'Process SQL Query (Demo)',
            type: 'sql',
            data: { query: 'SELECT * FROM orders WHERE customer_id = {{customerId}}' },
          },
          {
            id: 'cache-entry-3',
            name: 'Transform Data Script (Demo)',
            type: 'script',
            data: { language: 'python', code: 'def transform(data): return data * 2' },
          },
        ];
        setCompatibleSteps(simulatedSteps);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchCompatibleEntries();
  }, [catalogType, catalogSubType, catalogName, nodes]);

  useEffect(() => {
    // Call onWorkflowChange via the ref when nodes or edges change
    if (onWorkflowChangeRef.current) {
      onWorkflowChangeRef.current(nodes, edges);
    }
  }, [nodes, edges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();

      if (!reactFlowWrapper.current) return;

      const type = event.dataTransfer.getData('application/reactflow');
      if (typeof type === 'undefined' || !type) {
        return;
      }

      const draggedStep: CompatibleStep = JSON.parse(type);
      const position = screenToFlowPosition({
        x: event.clientX - reactFlowWrapper.current.getBoundingClientRect().left,
        y: event.clientY - reactFlowWrapper.current.getBoundingClientRect().top,
      });

      // Clamp position to stay within the wrapper bounds so that the node is visible.
      const wrapperRect = reactFlowWrapper.current.getBoundingClientRect();
      const NODE_WIDTH = 150; // approximate default width we use when rendering nodes
      const NODE_HEIGHT = 75; // average node height – adjust as necessary

      const clampedX = Math.min(
        Math.max(position.x, 0),
        wrapperRect.width - NODE_WIDTH
      );
      const clampedY = Math.min(
        Math.max(position.y, 0),
        wrapperRect.height - NODE_HEIGHT
      );

      const finalPosition = { x: clampedX, y: clampedY };

      const newNode: Node = {
        id: getNextNodeId(),
        type: 'default', // Or a custom type based on draggedStep.type
        position: finalPosition,
        data: { 
            label: `${draggedStep.name} (Type: ${draggedStep.type})`,
            originalStepId: draggedStep.id,
            originalStepType: draggedStep.type,
            ...draggedStep.data 
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [screenToFlowPosition, setNodes]
  );
  
  const handleDeleteSelected = useCallback(() => {
    // Prevent deleting start node
    const nodeIdsToRemove = new Set(nodes.filter(n => n.selected && n.id !== 'start').map(n => n.id));
    const edgeIdsToRemove = new Set(edges.filter(e => e.selected).map(e => e.id));

    if (nodeIdsToRemove.size === 0 && edgeIdsToRemove.size === 0) return;

    setNodes((nds) => nds.filter((node) => !nodeIdsToRemove.has(node.id)));
    setEdges((eds) => eds.filter((edge) => {
      if (edgeIdsToRemove.has(edge.id)) return false;
      // Remove edges connected to removed nodes
      if (nodeIdsToRemove.has(edge.source) || nodeIdsToRemove.has(edge.target)) return false;
      return true;
    }));
  }, [nodes, edges]);
  
  const handleGeneratedWorkflow = (generatedNodes: any[], generatedEdges: any[]) => {
    // Reset node counter
    id = 1;
    
    // Set the nodes and edges from the generated workflow
    setNodes(generatedNodes);
    setEdges(generatedEdges);
  };
  
  const handleRecipeImport = (importedNodes: any[], importedEdges: any[]) => {
    // Reset node counter
    id = 1;
    
    // Set the nodes and edges from the imported recipe
    setNodes(importedNodes);
    setEdges(importedEdges);
  };
  
  return (
    <div className="flex flex-col h-[600px] border rounded-md" ref={reactFlowWrapper}>
      {/* Main Flow Area */}
      <div className="flex-grow relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          fitView
        >
          <Controls />
          <MiniMap />
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
          
          {/* Workflow Controls Panel */}
          <Panel position="top-right">
            <div className="flex gap-2">
              <Button 
                onClick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  setIsGenerateDialogOpen(true);
                }}
                className="flex items-center gap-1"
                variant="outline"
                size="sm"
              >
                <Wand2 className="h-4 w-4" />
                Generate from NL
              </Button>
              <Button 
                onClick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  setIsRecipeImportDialogOpen(true);
                }}
                className="flex items-center gap-1"
                variant="outline"
                size="sm"
              >
                <FileText className="h-4 w-4" />
                Import Recipe
              </Button>
              <Button
                onClick={handleDeleteSelected}
                disabled={nodes.every(n=>!n.selected || n.id==='start') && edges.every(e=>!e.selected)}
                variant="outline"
                size="sm"
                className="flex items-center gap-1"
                title="Delete Selected (cannot delete Start node)"
              >
                <Trash2 className="h-4 w-4" />
                Delete Selected
              </Button>
            </div>
          </Panel>
        </ReactFlow>
      </div>
      
      {/* Bottom Step Palette */}
      <BottomStepPalette 
        compatibleSteps={compatibleSteps}
        isLoading={isLoading}
        error={error}
      />
      
      {/* Generate Workflow Dialog */}
      <GenerateWorkflowDialog
        open={isGenerateDialogOpen}
        onOpenChange={setIsGenerateDialogOpen}
        onWorkflowGenerated={handleGeneratedWorkflow}
        catalogType={catalogType}
        catalogSubtype={catalogSubType}
        catalogName={catalogName}
      />
      
      {/* Recipe Import Dialog */}
      <RecipeImportDialog
        open={isRecipeImportDialogOpen}
        onOpenChange={setIsRecipeImportDialogOpen}
        onRecipeImported={handleRecipeImport}
      />
    </div>
  );
};

// Wrap with ReactFlowProvider to use useReactFlow hook
const WorkflowBuilder: React.FC<WorkflowBuilderProps> = (props) => (
  <ReactFlowProvider>
    <WorkflowBuilderComponent {...props} />
  </ReactFlowProvider>
);

export default WorkflowBuilder; 