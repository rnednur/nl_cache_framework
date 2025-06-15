'use client';

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./dialog";
import { Button } from "../../app/components/ui/button";
import { Input } from "../../app/components/ui/input";
import { Label } from "../../app/components/ui/label";
import { Textarea } from "../../app/components/ui/textarea";
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from "../../app/components/ui/alert";
import api, { GenerateWorkflowRequest } from '../../app/services/api';

interface GenerateWorkflowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onWorkflowGenerated: (nodes: any[], edges: any[]) => void;
  catalogType?: string;
  catalogSubtype?: string;
  catalogName?: string;
}

export default function GenerateWorkflowDialog({
  open,
  onOpenChange,
  onWorkflowGenerated,
  catalogType,
  catalogSubtype,
  catalogName
}: GenerateWorkflowDialogProps) {
  const [nlQuery, setNlQuery] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string>('');
  
  const handleGenerate = async () => {
    if (!nlQuery.trim()) {
      setError('Please enter a query');
      return;
    }
    
    setIsGenerating(true);
    setError(null);
    setExplanation('');
    
    try {
      const request: GenerateWorkflowRequest = {
        nl_query: nlQuery,
        catalog_type: catalogType,
        catalog_subtype: catalogSubtype,
        catalog_name: catalogName
      };
      
      const result = await api.generateWorkflowFromNL(request);
      
      // Set the explanation for the user
      setExplanation(result.explanation);
      
      // Pass the generated workflow back to the parent component
      onWorkflowGenerated(result.nodes, result.edges);
      
      // Close the dialog after a short delay to show the explanation
      setTimeout(() => {
        onOpenChange(false);
      }, 2000);
      
    } catch (err) {
      console.error('Error generating workflow:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate workflow');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(open) => {
      // Prevent event propagation before changing open state
      onOpenChange(open);
    }}>
      <DialogContent className="sm:max-w-[525px]" onClick={(e) => e.stopPropagation()}>
        <DialogHeader>
          <DialogTitle>Generate Workflow</DialogTitle>
          <DialogDescription>
            Describe what you want to accomplish, and we'll generate a workflow to solve it.
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="nl-query">What do you want the workflow to do?</Label>
            <Textarea
              id="nl-query"
              placeholder="E.g., Fetch customer orders, filter by date, and calculate total revenue"
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              className="min-h-[100px]"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          {explanation && (
            <Alert>
              <AlertDescription className="whitespace-pre-line">{explanation}</AlertDescription>
            </Alert>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
            onOpenChange(false);
          }}>
            Cancel
          </Button>
          <Button onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
            handleGenerate();
          }} disabled={isGenerating || !nlQuery.trim()}>
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              'Generate Workflow'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 