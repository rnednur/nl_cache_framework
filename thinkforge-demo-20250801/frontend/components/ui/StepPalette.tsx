'use client';

import React from 'react';

// Define the structure of a compatible step (cache entry)
// This should align with the data you expect from your API
export interface CompatibleStep {
  id: string; // Unique ID of the cache entry
  name: string; // Display name (e.g., catalog_name or a specific title)
  type: string; // e.g., 'api', 'sql', 'script' - the template_type of the cache entry
  // Add any other relevant data you want to carry with the step
  data?: Record<string, any>; 
}

interface StepPaletteProps {
  compatibleSteps: CompatibleStep[];
}

const StepPalette: React.FC<StepPaletteProps> = ({ compatibleSteps }) => {
  const onDragStart = (event: React.DragEvent<HTMLDivElement>, step: CompatibleStep) => {
    // Set data to be transferred during drag
    // We'll stringify the step object; you can customize what data is needed
    event.dataTransfer.setData('application/reactflow', JSON.stringify(step));
    event.dataTransfer.effectAllowed = 'move';
  };

  if (!compatibleSteps || compatibleSteps.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        No compatible steps found for the current catalog configuration.
      </div>
    );
  }

  return (
    <div className="p-2 border-r h-full bg-card" style={{ minWidth: '200px', maxWidth: '300px' }}>
      <h3 className="text-lg font-semibold p-2 mb-2 border-b">Available Steps</h3>
      <div className="space-y-2">
        {compatibleSteps.map((step) => (
          <div
            key={step.id}
            className="p-3 border rounded-md shadow-sm hover:shadow-md cursor-grab bg-popover hover:bg-popover-foreground/10 transition-all duration-150 ease-in-out"
            onDragStart={(event) => onDragStart(event, step)}
            draggable
          >
            <div className="font-medium">{step.name}</div>
            <div className="text-xs text-muted-foreground">Type: {step.type}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default StepPalette; 