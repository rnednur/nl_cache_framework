#!/bin/bash
echo "🚀 ThinkForge Demo Quick Start"
echo "=============================="
echo ""
echo "Starting demo deployment..."
echo "This will:"
echo "  • Build Docker containers"
echo "  • Start PostgreSQL database"  
echo "  • Initialize demo data"
echo "  • Launch frontend and backend"
echo ""
read -p "Continue? [Y/n]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    ./scripts/demo_deploy.sh
else
    echo "Demo deployment cancelled."
fi
