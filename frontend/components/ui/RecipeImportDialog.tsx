'use client';

import React, { useState, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './dialog';
import { Button } from '@/app/components/ui/button';
import { Textarea } from '@/app/components/ui/textarea';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { Badge } from '@/app/components/ui/badge';
import { Progress } from '@/app/components/ui/progress';
import { Alert, AlertDescription } from '@/app/components/ui/alert';
import { 
  FileText, 
  Upload, 
  Wand2, 
  CheckCircle, 
  AlertTriangle, 
  Loader2,
  MapPin,
  Target,
  Zap
} from 'lucide-react';
import { Node, Edge } from 'reactflow';

interface RecipeStep {
  id: string;
  name: string;
  description: string;
  stepType: string;
  confidence: number;
  actionVerbs: string[];
  entities: string[];
  mappedTool?: {
    id: number;
    name: string;
    type: string;
    confidence: number;
    reasoning: string;
  };
}

interface RecipeAnalysis {
  recipeName: string;
  description: string;
  steps: RecipeStep[];
  totalSteps: number;
  complexityScore: number;
  estimatedDuration: number;
  requiredCapabilities: string[];
  recipeType: string;
}

interface RecipeImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRecipeImported: (nodes: Node[], edges: Edge[]) => void;
}

const RecipeImportDialog: React.FC<RecipeImportDialogProps> = ({
  open,
  onOpenChange,
  onRecipeImported,
}) => {
  const [activeTab, setActiveTab] = useState<'text' | 'csv'>('text');
  const [recipeText, setRecipeText] = useState('');
  const [recipeName, setRecipeName] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isMapping, setIsMapping] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<RecipeAnalysis | null>(null);
  const [mappingProgress, setMappingProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const resetState = useCallback(() => {
    setRecipeText('');
    setRecipeName('');
    setCsvFile(null);
    setIsAnalyzing(false);
    setIsMapping(false);
    setAnalysisResult(null);
    setMappingProgress(0);
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onOpenChange(false);
  }, [resetState, onOpenChange]);

  const analyzeRecipe = async () => {
    if (!recipeText.trim()) {
      setError('Please enter a recipe description');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      // Mock analysis - replace with actual API call to recipe analyzer
      await new Promise(resolve => setTimeout(resolve, 2000));

      const mockAnalysis: RecipeAnalysis = {
        recipeName: recipeName || 'Imported Recipe',
        description: recipeText.substring(0, 200) + '...',
        steps: [
          {
            id: 'step_1',
            name: 'Load customer data from database',
            description: 'Fetch customer information from the user database table',
            stepType: 'integration',
            confidence: 0.85,
            actionVerbs: ['fetch', 'load'],
            entities: ['customer', 'database', 'user_table'],
            mappedTool: {
              id: 123,
              name: 'PostgreSQL Query Tool',
              type: 'api',
              confidence: 0.92,
              reasoning: 'High semantic similarity; API tool excellent for integration steps; Tool is healthy and reliable'
            }
          },
          {
            id: 'step_2',
            name: 'Transform data to JSON format',
            description: 'Convert the retrieved customer data into JSON format for processing',
            stepType: 'transform',
            confidence: 0.78,
            actionVerbs: ['convert', 'transform'],
            entities: ['JSON', 'data'],
            mappedTool: {
              id: 456,
              name: 'Data Transformer Function',
              type: 'function',
              confidence: 0.88,
              reasoning: 'Good semantic match; Function tool excellent for transform steps; Popular, well-tested tool'
            }
          },
          {
            id: 'step_3',
            name: 'Validate data integrity',
            description: 'Check that all required fields are present and valid',
            stepType: 'validation',
            confidence: 0.65,
            actionVerbs: ['validate', 'check'],
            entities: ['fields', 'data'],
            mappedTool: {
              id: 789,
              name: 'Data Validation Agent',
              type: 'agent',
              confidence: 0.74,
              reasoning: 'Moderate semantic similarity; Agent tool suitable for validation steps; Some tool capabilities match step requirements'
            }
          }
        ],
        totalSteps: 3,
        complexityScore: 0.6,
        estimatedDuration: 8,
        requiredCapabilities: ['database-access', 'data-transformation', 'data-validation'],
        recipeType: 'data-processing'
      };

      setAnalysisResult(mockAnalysis);
    } catch (err) {
      setError('Failed to analyze recipe. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const importToWorkflow = async () => {
    if (!analysisResult) return;

    setIsMapping(true);
    setMappingProgress(0);

    try {
      // Simulate progressive mapping
      const steps = analysisResult.steps;
      const nodes: Node[] = [];
      const edges: Edge[] = [];

      // Add start node
      nodes.push({
        id: 'start',
        type: 'input',
        data: { label: `${analysisResult.recipeName} Start` },
        position: { x: 250, y: 50 },
      });

      // Process each step with simulated progress
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        
        // Simulate mapping delay
        await new Promise(resolve => setTimeout(resolve, 800));
        setMappingProgress(((i + 1) / steps.length) * 100);

        // Create node for step
        const stepNode: Node = {
          id: step.id,
          type: 'default',
          data: {
            label: `${step.name} (${step.mappedTool?.type || 'unmapped'})`,
            originalStepId: step.mappedTool?.id?.toString(),
            originalStepType: step.mappedTool?.type,
            confidence: step.mappedTool?.confidence || 0,
            reasoning: step.mappedTool?.reasoning || 'No tool mapped',
            stepDescription: step.description,
            actionVerbs: step.actionVerbs,
            entities: step.entities
          },
          position: { 
            x: 250 + (i % 2) * 300, 
            y: 150 + Math.floor(i / 2) * 150 
          }
        };

        nodes.push(stepNode);

        // Create edge from previous node
        const sourceId = i === 0 ? 'start' : steps[i - 1].id;
        edges.push({
          id: `${sourceId}-${step.id}`,
          source: sourceId,
          target: step.id,
          type: 'default'
        });
      }

      // Import to workflow
      onRecipeImported(nodes, edges);
      handleClose();

    } catch (err) {
      setError('Failed to import recipe to workflow. Please try again.');
    } finally {
      setIsMapping(false);
      setMappingProgress(0);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'text/csv') {
      setCsvFile(file);
      setError(null);
    } else {
      setError('Please select a valid CSV file');
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircle className="h-4 w-4 text-green-600" />;
    if (confidence >= 0.6) return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
    return <AlertTriangle className="h-4 w-4 text-red-600" />;
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Import Recipe to Workflow
          </DialogTitle>
          <DialogDescription>
            Import natural language recipes and automatically map them to available tools using AI-powered analysis.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'text' | 'csv')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="text" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Text Recipe
            </TabsTrigger>
            <TabsTrigger value="csv" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              CSV Upload
            </TabsTrigger>
          </TabsList>

          <TabsContent value="text" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="recipeName">Recipe Name (Optional)</Label>
              <Input
                id="recipeName"
                value={recipeName}
                onChange={(e) => setRecipeName(e.target.value)}
                placeholder="Enter a name for your recipe..."
                disabled={isAnalyzing || isMapping}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="recipeText">Recipe Description</Label>
              <Textarea
                id="recipeText"
                value={recipeText}
                onChange={(e) => setRecipeText(e.target.value)}
                placeholder="Enter your recipe in natural language. For example:
1. Load customer data from the database
2. Transform the data to JSON format
3. Validate data integrity
4. Send notification email to admin"
                className="min-h-[120px]"
                disabled={isAnalyzing || isMapping}
              />
            </div>

            {!analysisResult && (
              <Button 
                onClick={analyzeRecipe} 
                disabled={isAnalyzing || !recipeText.trim()}
                className="w-full"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing Recipe...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4 mr-2" />
                    Analyze Recipe
                  </>
                )}
              </Button>
            )}
          </TabsContent>

          <TabsContent value="csv" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="csvFile">CSV File</Label>
              <Input
                id="csvFile"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                disabled={isAnalyzing || isMapping}
              />
              <p className="text-sm text-muted-foreground">
                CSV should contain columns: recipe_name, recipe_text (or similar)
              </p>
            </div>

            {csvFile && (
              <div className="p-4 border rounded-lg">
                <p className="font-medium">Selected File:</p>
                <p className="text-sm text-muted-foreground">{csvFile.name}</p>
              </div>
            )}

            <Button 
              onClick={() => {/* TODO: Implement CSV analysis */}} 
              disabled={!csvFile || isAnalyzing}
              className="w-full"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing CSV...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Process CSV
                </>
              )}
            </Button>
          </TabsContent>
        </Tabs>

        {analysisResult && (
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Recipe Analysis Results</h3>
              <div className="flex gap-2">
                <Badge variant="outline">
                  {analysisResult.totalSteps} steps
                </Badge>
                <Badge variant="outline">
                  {analysisResult.recipeType}
                </Badge>
                <Badge variant="outline">
                  ~{analysisResult.estimatedDuration}min
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="font-medium text-muted-foreground">Complexity</p>
                <div className="flex items-center gap-2">
                  <Progress value={analysisResult.complexityScore * 100} className="flex-1" />
                  <span>{Math.round(analysisResult.complexityScore * 100)}%</span>
                </div>
              </div>
              <div>
                <p className="font-medium text-muted-foreground">Required Capabilities</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {analysisResult.requiredCapabilities.map((cap) => (
                    <Badge key={cap} variant="secondary" className="text-xs">
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="font-medium text-muted-foreground">Estimated Duration</p>
                <p className="text-lg font-semibold">{analysisResult.estimatedDuration} minutes</p>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="font-medium flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Step Mappings
              </h4>
              
              {isMapping && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Mapping steps to tools...</span>
                  </div>
                  <Progress value={mappingProgress} />
                </div>
              )}

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {analysisResult.steps.map((step, index) => (
                  <div key={step.id} className="border rounded-lg p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium">
                            {index + 1}. {step.name}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            {step.stepType}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                          {step.description}
                        </p>
                        
                        {step.mappedTool ? (
                          <div className="flex items-center gap-2">
                            <Target className="h-3 w-3 text-blue-600" />
                            <span className="text-xs font-medium">
                              {step.mappedTool.name} ({step.mappedTool.type})
                            </span>
                            <Badge 
                              className={`text-xs ${getConfidenceColor(step.mappedTool.confidence)}`}
                            >
                              {Math.round(step.mappedTool.confidence * 100)}%
                            </Badge>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <AlertTriangle className="h-3 w-3" />
                            <span className="text-xs">No tool mapped</span>
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {step.mappedTool && getConfidenceIcon(step.mappedTool.confidence)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={importToWorkflow}
                disabled={isMapping}
                className="flex-1"
              >
                {isMapping ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Importing to Workflow...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-2" />
                    Import to Workflow
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => setAnalysisResult(null)}
                disabled={isMapping}
              >
                Analyze Different Recipe
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default RecipeImportDialog;