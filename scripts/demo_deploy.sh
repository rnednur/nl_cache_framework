#!/bin/bash

# ThinkForge Demo Deployment Script
# This script sets up a complete ThinkForge demo environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Demo configuration
DEMO_VERSION="1.0.0"
POSTGRES_PASSWORD="demo_password_2024"
FRONTEND_PORT="3001"
BACKEND_PORT="8000"

print_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                     ThinkForge Demo Setup                   ║"
    echo "║                         Version $DEMO_VERSION                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_requirements() {
    print_step "Checking system requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required but not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is required but not installed."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if ports are available
    if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $FRONTEND_PORT is already in use. Demo frontend may not start properly."
    fi
    
    if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $BACKEND_PORT is already in use. Demo backend may not start properly."
    fi
    
    print_success "System requirements check completed"
}

create_demo_config() {
    print_step "Creating demo configuration..."
    
    # Create .env file for demo
    cat > .env.demo << EOF
# ThinkForge Demo Configuration
POSTGRES_DB=thinkforge_demo
POSTGRES_USER=thinkforge
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DEMO_MODE=true
AUTO_SEED_DATA=true
NEXT_PUBLIC_API_BASE_URL=http://localhost:$BACKEND_PORT
EOF

    print_success "Demo configuration created"
}

export_current_data() {
    print_step "Checking for existing data to export..."
    
    if [ -f "mcp_cache.db" ] || [ -d "demo_data_export" ]; then
        read -p "$(echo -e ${YELLOW}Export existing data for demo? [y/N]: ${NC})" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Exporting existing data..."
            python scripts/export_demo_data.py
            print_success "Data exported to demo_data_export/"
        fi
    fi
}

build_demo_images() {
    print_step "Building Docker images for demo..."
    
    # Build images using demo docker-compose
    docker-compose -f docker-compose.demo.yml build --no-cache
    
    print_success "Docker images built successfully"
}

start_demo_services() {
    print_step "Starting ThinkForge demo services..."
    
    # Start services in background
    docker-compose -f docker-compose.demo.yml up -d
    
    print_success "Demo services started"
}

wait_for_services() {
    print_step "Waiting for services to be ready..."
    
    # Wait for backend to be ready
    echo -n "Waiting for backend API"
    for i in {1..60}; do
        if curl -s -f http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo
    
    # Wait for frontend to be ready
    echo -n "Waiting for frontend"
    for i in {1..30}; do
        if curl -s -f http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo
    
    print_success "All services are ready"
}

show_demo_info() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                 🎉 ThinkForge Demo Ready! 🎉                ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║                                                              ║"
    echo "║  🌐 Frontend:  http://localhost:$FRONTEND_PORT                     ║"
    echo "║  🔧 Backend:   http://localhost:$BACKEND_PORT                       ║"
    echo "║  📊 Database:  PostgreSQL on localhost:5432                 ║"
    echo "║                                                              ║"
    echo "║  Demo Features Available:                                    ║"
    echo "║  • Sample Tools & APIs                                       ║"
    echo "║  • Recipe Creation & Management                              ║"
    echo "║  • Natural Language Processing                               ║"
    echo "║  • Tool Discovery & Mapping                                  ║"
    echo "║  • Usage Analytics                                           ║"
    echo "║                                                              ║"
    echo "║  📖 Demo Guide: README.md                                    ║"
    echo "║  🛠️  Logs: docker-compose -f docker-compose.demo.yml logs   ║"
    echo "║  🛑 Stop: docker-compose -f docker-compose.demo.yml down    ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

create_demo_guide() {
    print_step "Creating demo guide..."
    
    cat > DEMO_GUIDE.md << 'EOF'
# ThinkForge Demo Guide

Welcome to the ThinkForge demonstration! This guide will walk you through the key features and capabilities.

## 🚀 Getting Started

1. **Access the Application**
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:8000

2. **Demo Data**
   The system comes pre-loaded with:
   - 5+ sample tools (database, API, functions, agents)
   - 2 complete recipe workflows
   - Sample usage data and analytics

## 🎯 Key Demo Features

### 1. Tool Hub
- **Location**: Tools → Tool Hub
- **Features**: Browse available tools, filter by catalog, test tool functionality
- **Demo Tools**: PostgreSQL connector, JSON transformer, REST APIs, AI agents

### 2. Recipe Creation
- **Location**: Recipes → Create Recipe
- **Key Feature**: Natural Language Recipe Creation
- **Demo**: 
  1. Click "Natural Language" tab
  2. Enter: "Process customer data by extracting from database, validating fields, and sending notification"  
  3. Click "Analyze Recipe" to see AI-powered step mapping
  4. Review suggested tools and confidence scores

### 3. Recipe Management
- **Location**: Recipes → Recipe Hub
- **Features**: View existing recipes, execution statistics, workflow visualization
- **Demo Recipes**: Customer data processing, User onboarding automation

### 4. Test Completion
- **Location**: Complete Test
- **Features**: Test natural language queries against the cache
- **Demo Queries**:
  - "Get customer information from database"
  - "Transform JSON data to different format"
  - "Send notification email"

### 5. Usage Analytics
- **Location**: Usage Logs
- **Features**: View query patterns, success rates, tool usage statistics
- **Demo Data**: Pre-populated with realistic usage patterns

## 🔍 Advanced Features

### Natural Language Processing
- Real semantic similarity search using sentence transformers
- Confidence scoring for tool matches
- Context-aware step classification

### Tool Discovery
- Catalog-based organization (type, subtype, name)
- Health monitoring and status tracking
- Capability-based filtering

### Recipe Intelligence
- Automatic step dependency detection
- Complexity scoring and time estimation
- Tool conflict resolution

## 💡 Demo Scenarios

### Scenario 1: Create a Data Processing Recipe
1. Go to Recipes → Create Recipe
2. Use Natural Language tab
3. Enter a workflow description
4. Watch AI analyze and map tools
5. Review and accept the generated recipe

### Scenario 2: Explore Tool Capabilities
1. Go to Tools → Tool Hub
2. Filter by different catalog types
3. Click on tools to see detailed information
4. Test tool functionality

### Scenario 3: Analyze Usage Patterns
1. Go to Usage Logs
2. Review query patterns and success rates
3. Check which tools are most popular
4. Analyze confidence scores

## 🔧 Technical Details

- **Backend**: FastAPI with PostgreSQL
- **Frontend**: React with TypeScript
- **AI**: Sentence transformers for semantic similarity
- **Data**: Exportable/importable for demos

## 📊 Performance Notes

- First queries may be slower due to model loading
- Embeddings are generated on-demand for new entries
- Demo optimized for clarity over performance

## 🛟 Troubleshooting

- **Services not starting**: Check Docker logs
- **Connection issues**: Verify ports 3001 and 8000 are available
- **Data issues**: Restart with `docker-compose -f docker-compose.demo.yml restart`

Enjoy exploring ThinkForge! 🚀
EOF

    print_success "Demo guide created (DEMO_GUIDE.md)"
}

cleanup_on_exit() {
    if [ $? -ne 0 ]; then
        print_error "Demo setup failed. Cleaning up..."
        docker-compose -f docker-compose.demo.yml down 2>/dev/null || true
    fi
}

main() {
    trap cleanup_on_exit EXIT
    
    print_header
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.demo.yml" ]; then
        print_error "Please run this script from the ThinkForge root directory"
        exit 1
    fi
    
    check_requirements
    create_demo_config
    export_current_data
    build_demo_images
    start_demo_services
    wait_for_services
    create_demo_guide
    show_demo_info
    
    # Optional: Open browser
    read -p "$(echo -e ${CYAN}Open demo in browser? [y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v open &> /dev/null; then
            open http://localhost:$FRONTEND_PORT
        elif command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:$FRONTEND_PORT
        else
            print_warning "Please open http://localhost:$FRONTEND_PORT in your browser"
        fi
    fi
}

# Run main function
main "$@"