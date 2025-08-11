import { Link } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface CacheBreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function CacheBreadcrumbs({ items, className }: CacheBreadcrumbsProps) {
  return (
    <nav className={["flex items-center text-sm text-neutral-400", className].filter(Boolean).join(" ")}>
      <ol className="flex items-center space-x-1">
        <li>
          <Link 
            to="/" 
            className="flex items-center hover:text-neutral-100 transition-colors"
          >
            <Home className="h-4 w-4" />
            <span className="sr-only">Home</span>
          </Link>
        </li>
        <li>
          <ChevronRight className="h-4 w-4" />
        </li>
        {items.map((item, index) => (
          <li key={item.label} className="flex items-center">
            {item.href ? (
              <Link
                to={item.href}
                className="hover:text-neutral-100 transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className="text-neutral-100 font-medium">{item.label}</span>
            )}
            {index < items.length - 1 && (
              <>
                <ChevronRight className="h-4 w-4 mx-1" />
              </>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
} 