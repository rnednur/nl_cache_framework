#!/bin/bash

# ThinkForge Demo Package Creation Script
# Creates a distributable demo package

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PACKAGE_NAME="thinkforge-demo-$(date +%Y%m%d)"
EXCLUDE_FILE=".demo_exclude"

print_step() {
    echo -e "${BLUE}📦 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Create exclude file for packaging
create_exclude_file() {
    cat > $EXCLUDE_FILE << 'EOF'
# Exclude development and runtime files
node_modules
.git
.gitignore
*.log
__pycache__
*.pyc
.pytest_cache
.coverage
dist
build
.env
.env.*
.DS_Store
Thumbs.db

# Exclude development databases
*.db
*.sqlite
*.sqlite3

# Exclude large model files (will be downloaded on first run)
models/
.cache/

# Exclude personal configurations
config.local.*
.vscode/
.idea/

# Exclude temporary files
tmp/
temp/
*.tmp
*.swp
*.swo

# Exclude build artifacts
target/
.next/
out/

# Keep demo-specific files
!.env.demo
!docker-compose.demo.yml
!DEMO_README.md
!DEMO_GUIDE.md
EOF
}

export_demo_data() {
    print_step "Exporting current demo data..."
    
    if [ -f "scripts/export_demo_data.py" ]; then
        python scripts/export_demo_data.py || print_warning "Could not export existing data (this is OK for fresh installs)"
    fi
    
    print_success "Demo data export completed"
}

create_demo_package() {
    print_step "Creating demo package: $PACKAGE_NAME"
    
    # Create package directory
    mkdir -p "$PACKAGE_NAME"
    
    # Copy all files except excluded ones
    rsync -av \
        --exclude-from="$EXCLUDE_FILE" \
        --exclude="$PACKAGE_NAME" \
        . "$PACKAGE_NAME/"
    
    # Ensure demo files are included
    cp DEMO_README.md "$PACKAGE_NAME/" 2>/dev/null || print_warning "DEMO_README.md not found"
    cp docker-compose.demo.yml "$PACKAGE_NAME/" 2>/dev/null || print_warning "docker-compose.demo.yml not found"
    
    # Create quick start script
    cat > "$PACKAGE_NAME/QUICK_START.sh" << 'EOF'
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
EOF
    
    chmod +x "$PACKAGE_NAME/QUICK_START.sh"
    
    print_success "Demo package created in $PACKAGE_NAME/"
}

create_package_info() {
    print_step "Creating package information..."
    
    # Create package info file
    cat > "$PACKAGE_NAME/PACKAGE_INFO.txt" << EOF
ThinkForge Demo Package
=====================

Package: $PACKAGE_NAME
Created: $(date)
Version: 1.0.0

Contents:
- Complete ThinkForge system
- Docker deployment configuration
- Demo data and sample content
- Documentation and guides

Quick Start:
1. ./QUICK_START.sh
2. Open http://localhost:3001

For detailed instructions, see DEMO_README.md

System Requirements:
- Docker & Docker Compose
- 4GB+ RAM available
- Ports 3001, 8000, 5432 available

Package Size: $(du -sh "$PACKAGE_NAME" | cut -f1)
EOF

    print_success "Package information created"
}

create_archive() {
    print_step "Creating distributable archive..."
    
    # Create tarball
    tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME/"
    
    # Create zip for Windows users
    if command -v zip &> /dev/null; then
        zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME/" > /dev/null
        print_success "Created ZIP archive: ${PACKAGE_NAME}.zip"
    fi
    
    print_success "Created TAR.GZ archive: ${PACKAGE_NAME}.tar.gz"
}

show_package_summary() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                📦 Demo Package Created! 📦                  ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║                                                              ║"
    echo "║  📁 Directory: $PACKAGE_NAME                        ║"
    echo "║  📦 Archive:   ${PACKAGE_NAME}.tar.gz               ║"
    if [ -f "${PACKAGE_NAME}.zip" ]; then
    echo "║  📦 Archive:   ${PACKAGE_NAME}.zip                  ║"
    fi
    echo "║                                                              ║"
    echo "║  Package Size: $(du -sh "$PACKAGE_NAME" | cut -f1)                                      ║"
    echo "║  Archive Size: $(du -sh "${PACKAGE_NAME}.tar.gz" | cut -f1)                                     ║"
    echo "║                                                              ║"
    echo "║  Distribution Instructions:                                  ║"
    echo "║  1. Share the .tar.gz or .zip file                         ║"
    echo "║  2. Recipients extract the archive                          ║"
    echo "║  3. Run ./QUICK_START.sh for instant demo                   ║"
    echo "║                                                              ║"
    echo "║  📖 See DEMO_README.md for complete instructions            ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

cleanup() {
    # Remove temporary files
    rm -f $EXCLUDE_FILE
}

main() {
    trap cleanup EXIT
    
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                ThinkForge Demo Package Creator              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.demo.yml" ]; then
        echo "❌ Please run this script from the ThinkForge root directory"
        echo "   (docker-compose.demo.yml not found)"
        exit 1
    fi
    
    create_exclude_file
    export_demo_data
    create_demo_package
    create_package_info
    create_archive
    show_package_summary
    
    print_success "Demo package creation completed!"
}

# Run main function
main "$@"