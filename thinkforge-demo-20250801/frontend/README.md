# ThinkForge Frontend

A modern React-based web application for managing chain of thought templates, built with Next.js and TypeScript.

## Features

- Dashboard with key statistics and metrics
- View and manage cache entries
- Create and edit cache entries with various template types (SQL, API, URL, Workflow)
- Tag management for entries
- Search and filtering capabilities
- Statistics and analytics

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Custom components built with shadcn/ui
- **State Management**: React hooks (useState, useEffect)
- **Routing**: Next.js App Router
- **API Communication**: Fetch API through a centralized service

## Getting Started

### Prerequisites

- Node.js 18.x or higher
- npm or yarn

### Installation

1. Clone the repository
2. Navigate to the frontend directory

```bash
cd frontend
```

3. Install dependencies

```bash
npm install
# or
yarn install
```

4. Create a `.env.local` file in the root directory and add:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Development

To start the development server:

```bash
npm run dev
# or
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Building for Production

To create a production build:

```bash
npm run build
# or
yarn build
```

To start the production server:

```bash
npm run start
# or
yarn start
```

## Project Structure

- `/app`: Main Next.js application structure
  - `/(dashboard)`: Layout and pages for the main dashboard
  - `/components`: Reusable UI components
    - `/ui`: Basic UI building blocks
  - `/services`: API services and types
  - `/lib`: Utility functions

## API Integration

The frontend communicates with the ThinkForge backend API through the services defined in `/app/services/api.ts`, which includes:

- `getCacheEntries`: List entries with pagination and filtering
- `getCacheEntry`: Get a single entry by ID
- `createCacheEntry`: Create a new cache entry
- `updateCacheEntry`: Update an existing entry
- `deleteCacheEntry`: Delete an entry
- `getCacheStats`: Get usage statistics
- `testCacheEntry`: Test a cache entry
- `applyEntitySubstitution`: Apply entity substitution to a template 