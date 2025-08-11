"use client"

import { useState, ReactNode, useCallback, useEffect, useRef } from "react";

interface SimpleCacheTooltipProps {
  children: ReactNode;
  content: ReactNode;
}

export function SimpleCacheTooltip({ children, content }: SimpleCacheTooltipProps) {
  const [isHovering, setIsHovering] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Position calculation with boundaries check
  const calculatePosition = useCallback((e: React.MouseEvent | MouseEvent) => {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Default positions
    let xPos = e.clientX + 10;
    let yPos = e.clientY + 10;
    
    // Get tooltip dimensions if available
    const tooltipWidth = tooltipRef.current ? tooltipRef.current.offsetWidth : 300;
    const tooltipHeight = tooltipRef.current ? tooltipRef.current.offsetHeight : 200;
    
    // Adjust horizontal position if needed
    if (xPos + tooltipWidth > viewportWidth - 20) {
      xPos = Math.max(20, e.clientX - tooltipWidth - 10);
    }
    
    // Adjust vertical position if needed
    if (yPos + tooltipHeight > viewportHeight - 20) {
      yPos = Math.max(20, e.clientY - tooltipHeight - 10);
    }
    
    setPosition({ x: xPos, y: yPos });
  }, []);

  const handleMouseEnter = useCallback(() => {
    setIsHovering(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsHovering(false);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    calculatePosition(e);
  }, [calculatePosition]);

  // Ensure tooltip stays visible and positioned correctly, even after scrolling
  useEffect(() => {
    const handleScroll = () => {
      if (isHovering) {
        setIsHovering(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [isHovering]);

  return (
    <div
      className="inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
    >
      {children}
      
      {isHovering && (
        <div 
          ref={tooltipRef}
          className="fixed z-50 bg-neutral-900 border border-neutral-700 rounded-md shadow-lg p-4 cache-tooltip"
          style={{ 
            left: `${position.x}px`, 
            top: `${position.y}px`,
            maxWidth: "300px",
            overflow: "auto",
            maxHeight: "300px"
          }}
        >
          {content}
        </div>
      )}
    </div>
  );
} 