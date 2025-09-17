#!/bin/bash

# Clear Vite cache and restart development server
echo "🔄 Clearing Vite cache and restarting development server..."

cd /Users/rnednur/code/nl_cache_framework/frontend-react

# Remove node_modules cache
echo "Removing node_modules/.vite cache..."
rm -rf node_modules/.vite

# Clear Vite cache directory
echo "Clearing Vite cache..."
rm -rf node_modules/.cache

# Restart dev server with clean cache
echo "✅ Cache cleared! Restart your dev server:"
echo "npm run dev"