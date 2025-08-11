# Frontend-React Integration Guide

This guide provides step-by-step instructions for integrating the links, pages, and functionality from the `frontend-react` application into your existing application.

## Overview

The `frontend-react` application is a **Natural Language Cache Framework** dashboard with the following main features:
- Cache entry management (CRUD operations)
- Usage logs and analytics  
- Test completion functionality
- Data upload capabilities
- Dashboard with statistics

## Core Dependencies

Before integration, ensure your existing application has these dependencies:

```json
{
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-router-dom": "^7.6.2",
    "react-hot-toast": "^2.5.2",
    "next-themes": "^0.4.6",
    "lucide-react": "^0.514.0",
    "chart.js": "^4.4.9",
    "recharts": "^2.15.3",
    "@radix-ui/react-label": "^2.1.7",
    "@radix-ui/react-select": "^2.2.5",
    "@radix-ui/react-slot": "^1.2.3",
    "@radix-ui/react-switch": "^1.2.5",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.3.1",
    "tailwindcss": "^3.4.17",
    "tailwindcss-animate": "^1.0.7"
  }
}
```

## Page Routes & Links Structure

### Main Navigation Routes

The application has the following primary routes:

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Dashboard | Main dashboard with statistics |
| `/cache-entries` | CacheEntries | Cache entries listing with CRUD |
| `/cache-entries/create` | CreateCacheEntry | Create new cache entry |
| `/cache-entries/:id` | ViewCacheEntry | View specific cache entry |
| `/cache-entries/:id/edit` | EditCacheEntry | Edit specific cache entry |
| `/test-completion` | TestCompletion | Test cache completion functionality |
| `/data-upload` | DataUpload | Upload data files |
| `/usage-logs` | UsageLogs | View system usage logs |
| `/analytics` | Analytics (Placeholder) | Analytics dashboard |
| `/settings` | Settings (Placeholder) | Application settings |

### Navigation Links Configuration

The sidebar navigation includes these links with their icons:

```tsx
const navigationLinks = [
  {
    to: "/",
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: "Dashboard"
  },
  {
    to: "/cache-entries", 
    icon: <Database className="h-4 w-4" />,
    label: "Cache Entries"
  },
  {
    to: "/test-completion",
    icon: <TestTube className="h-4 w-4" />,
    label: "Test Completion"
  },
  {
    to: "/data-upload",
    icon: <Upload className="h-4 w-4" />,
    label: "Data Upload"
  },
  {
    to: "/usage-logs",
    icon: <Clock className="h-4 w-4" />,
    label: "Usage Logs"
  },
  {
    to: "/settings",
    icon: <Settings className="h-4 w-4" />,
    label: "Settings"
  }
]
```

## Step-by-Step Integration

### 1. Copy Core Components

Copy these essential components from `frontend-react/src/components/`:

- `layout.tsx` - Main layout wrapper
- `sidebar.tsx` - Navigation sidebar
- `header.tsx` - Top header
- `theme-provider.tsx` - Theme management
- `logo.tsx` - Application logo
- `theme-toggle.tsx` - Dark/light mode toggle

### 2. Copy UI Components

Copy the entire `frontend-react/src/components/ui/` directory containing:
- `button.tsx`, `card.tsx`, `input.tsx`, `label.tsx`
- `select.tsx`, `switch.tsx`, `table.tsx`, `textarea.tsx`
- `tabs.tsx`, `alert.tsx`
- Custom components: `CacheEntryModal.tsx`, `CacheEntryList.tsx`, etc.

### 3. Copy Page Components

Copy all pages from `frontend-react/src/pages/`:
- `Dashboard.tsx` - Main dashboard
- `CacheEntries.tsx` - Cache management (includes sub-routes)
- `TestCompletion.tsx` - Testing functionality
- `DataUpload.tsx` - File upload
- `UsageLogs.tsx` - Usage analytics

### 4. Copy Services & Contexts

Copy these essential services:
- `frontend-react/src/services/api.ts` - API service layer
- `frontend-react/src/contexts/SearchContext.tsx` - Search functionality
- `frontend-react/src/lib/utils.ts` - Utility functions

### 5. Update Your App.tsx

Replace or modify your main App component:

```tsx
import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import { ThemeProvider } from "@/components/theme-provider"
import { SearchProvider } from "@/contexts/SearchContext"
import { Layout } from "@/components/layout"
import { Toaster } from "react-hot-toast"

// Import your pages
import Dashboard from "@/pages/Dashboard"
import CacheEntriesRoutes from "@/pages/CacheEntries"
import DataUpload from "@/pages/DataUpload"
import TestCompletion from "@/pages/TestCompletion"
import UsageLogs from "@/pages/UsageLogs"

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-3xl font-bold text-white">{title}</h1>
}

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      <SearchProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/*" element={<CacheEntriesRoutes />} />
              <Route path="/test-completion" element={<TestCompletion />} />
              <Route path="/data-upload" element={<DataUpload />} />
              <Route path="/usage-logs" element={<UsageLogs />} />
              <Route path="/analytics" element={<Placeholder title="Analytics" />} />
              <Route path="/settings" element={<Placeholder title="Settings" />} />
            </Routes>
          </Layout>
        </Router>
      </SearchProvider>
      <Toaster position="top-right" />
    </ThemeProvider>
  )
}

export default App
```

### 6. Configure Tailwind CSS

Ensure your `tailwind.config.js` includes the necessary configuration:

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',  
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

### 7. Copy CSS Styles

Copy the CSS from `frontend-react/src/index.css` and `frontend-react/src/App.css` to your application's global styles.

### 8. Environment Configuration

Set up environment variables for API configuration:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 9. API Integration

The application expects a backend API with these endpoints:
- `GET /v1/cache` - List cache entries
- `POST /v1/cache` - Create cache entry
- `GET /v1/cache/{id}` - Get specific cache entry
- `PUT /v1/cache/{id}` - Update cache entry
- `DELETE /v1/cache/{id}` - Delete cache entry
- `GET /v1/cache/search` - Search cache entries
- `POST /v1/complete` - Test completion
- `GET /v1/usage-logs` - Get usage logs
- `GET /v1/catalog-values` - Get catalog values

## Key Features Per Page

### Dashboard (`/`)
- Overview statistics cards
- Template type distribution
- Usage metrics
- Charts and visualizations

### Cache Entries (`/cache-entries`)
- Full CRUD operations
- Advanced filtering and search
- Similarity search capability
- Pagination and sorting
- Export functionality

### Test Completion (`/test-completion`)  
- Natural language query testing
- Similarity threshold configuration
- LLM integration toggle
- Results history

### Data Upload (`/data-upload`)
- File upload functionality
- Data validation
- Progress tracking

### Usage Logs (`/usage-logs`)
- System usage analytics
- Filtering by status, confidence, etc.
- Date range filtering
- Export capabilities

## Customization Options

### Theming
The application supports dark/light themes via `next-themes`. Customize colors in your CSS variables:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  /* ... other CSS variables */
}

.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  /* ... other CSS variables */
}
```

### Branding
- Replace the `Logo` component with your brand
- Update colors in `tailwind.config.js`
- Modify the header title in `header.tsx`

### API Endpoints
Update the API base URL in `services/api.ts` to match your backend.

## Deployment Considerations

1. **Environment Variables**: Set up proper environment configuration
2. **Build Process**: Ensure all dependencies are installed
3. **Routing**: Configure your server to handle client-side routing
4. **API CORS**: Configure your backend for cross-origin requests

## Troubleshooting

### Common Issues

1. **Missing Dependencies**: Ensure all required packages are installed
2. **Routing Issues**: Verify React Router is properly configured
3. **Theme Issues**: Check CSS variables are properly defined
4. **API Errors**: Verify backend endpoints and CORS configuration

### Path Alias Configuration

Ensure your bundler (Vite/Webpack) is configured for the `@/` path alias:

```ts
// vite.config.ts
import path from "path"

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```

This guide provides everything needed to successfully integrate the frontend-react application's complete navigation structure and functionality into your existing application. 