'use client';

import React, { useState } from 'react';
import { Input } from '../../app/components/ui/input';
import { Button } from '../../app/components/ui/button';
import { ScrollArea } from '../../app/components/ui/scroll-area';
import { Search } from 'lucide-react';
import { CompatibleStep } from './StepPalette';

interface BottomStepPaletteProps {
  compatibleSteps: CompatibleStep[];
  isLoading: boolean;
  error: string | null;
}

const BottomStepPalette: React.FC<BottomStepPaletteProps> = ({ 
  compatibleSteps,
  isLoading,
  error
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // Filter steps based on search query
  const filteredSteps = compatibleSteps.filter(step => {
    const query = searchQuery.toLowerCase();
    return (
      step.name.toLowerCase().includes(query) ||
      step.type.toLowerCase().includes(query) ||
      (step.data?.catalogType && step.data.catalogType.toLowerCase().includes(query)) ||
      (step.data?.catalogSubtype && step.data.catalogSubtype.toLowerCase().includes(query)) ||
      (step.data?.catalogName && step.data.catalogName.toLowerCase().includes(query))
    );
  });

  const onDragStart = (event: React.DragEvent<HTMLDivElement>, step: CompatibleStep) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(step));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="border-t p-3 bg-card w-full">
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div className="relative flex-grow">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search available steps..."
              className="pl-8"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button variant="outline" size="sm" onClick={() => setSearchQuery('')}>
            Clear
          </Button>
        </div>
        
        <div className="text-sm font-medium">Available Steps ({filteredSteps.length})</div>
        
        {isLoading ? (
          <div className="flex justify-center p-4">
            <div className="animate-spin h-5 w-5 border-2 border-current border-t-transparent rounded-full"></div>
          </div>
        ) : error ? (
          <div className="text-red-500 text-sm p-2">{error}</div>
        ) : filteredSteps.length === 0 ? (
          <div className="text-sm text-muted-foreground p-2">
            {searchQuery ? 'No matching steps found' : 'No steps available'}
          </div>
        ) : (
          <ScrollArea className="h-32">
            <div className="grid grid-cols-3 gap-2 p-1">
              {filteredSteps.map((step) => (
                <div
                  key={step.id}
                  className="p-2 border rounded-md shadow-sm hover:shadow-md cursor-grab bg-popover hover:bg-popover-foreground/10 transition-all duration-150 ease-in-out"
                  onDragStart={(event) => onDragStart(event, step)}
                  draggable
                >
                  <div className="font-medium truncate text-sm">{step.name}</div>
                  <div className="text-xs text-muted-foreground">Type: {step.type}</div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
};

export default BottomStepPalette; 