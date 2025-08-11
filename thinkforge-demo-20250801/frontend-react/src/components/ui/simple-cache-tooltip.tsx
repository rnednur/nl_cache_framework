import { useState, useRef, useCallback, useEffect, ReactNode, MouseEvent } from "react";

interface SimpleCacheTooltipProps {
  children: ReactNode;
  content: ReactNode;
}

export function SimpleCacheTooltip({ children, content }: SimpleCacheTooltipProps) {
  const [isHovering, setIsHovering] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Calculate and constrain tooltip position within viewport
  const calculatePosition = useCallback((e: MouseEvent | globalThis.MouseEvent) => {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let xPos = e.clientX + 10;
    let yPos = e.clientY + 10;

    const tooltipWidth = tooltipRef.current ? tooltipRef.current.offsetWidth : 300;
    const tooltipHeight = tooltipRef.current ? tooltipRef.current.offsetHeight : 200;

    if (xPos + tooltipWidth > viewportWidth - 20) {
      xPos = Math.max(20, e.clientX - tooltipWidth - 10);
    }
    if (yPos + tooltipHeight > viewportHeight - 20) {
      yPos = Math.max(20, e.clientY - tooltipHeight - 10);
    }

    setPosition({ x: xPos, y: yPos });
  }, []);

  const handleMouseEnter = useCallback(() => setIsHovering(true), []);
  const handleMouseLeave = useCallback(() => setIsHovering(false), []);
  const handleMouseMove = useCallback((e: MouseEvent) => calculatePosition(e), [calculatePosition]);

  // Hide tooltip on scroll to avoid mis-placement
  useEffect(() => {
    const onScroll = () => isHovering && setIsHovering(false);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, [isHovering]);

  return (
    <span
      className="inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
    >
      {children}
      {isHovering && (
        <div
          ref={tooltipRef}
          className="fixed z-50 bg-neutral-900 border border-neutral-700 rounded-md shadow-lg p-4 text-sm"
          style={{ left: position.x, top: position.y, maxWidth: 300, maxHeight: 300, overflow: "auto" }}
        >
          {content}
        </div>
      )}
    </span>
  );
} 