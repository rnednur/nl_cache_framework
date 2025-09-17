#!/bin/bash

# Enhanced Spaces Setup Script for ThinkForge
# This script sets up the enhanced spaces functionality including migration and verification

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "add_enhanced_spaces_functionality.py" ]; then
    print_error "This script must be run from the dbscripts directory"
    print_error "Current directory: $(pwd)"
    exit 1
fi

print_status "🚀 Setting up Enhanced Spaces Functionality for ThinkForge"
print_status "=================================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
print_status "Python version: $python_version"

# Check if required Python packages are installed
print_status "Checking Python dependencies..."
required_packages=("sqlalchemy" "psycopg2" "python-dotenv")
missing_packages=()

for package in "${required_packages[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        missing_packages+=("$package")
    fi
done

if [ ${#missing_packages[@]} -ne 0 ]; then
    print_warning "Missing required Python packages: ${missing_packages[*]}"
    print_status "Installing missing packages..."
    pip install "${missing_packages[@]}"
fi

# Check if .env file exists
if [ ! -f "../backend/.env" ]; then
    print_warning ".env file not found in backend directory"
    print_warning "Please ensure your database configuration is set up properly"
fi

# Make scripts executable
print_status "Making scripts executable..."
chmod +x add_enhanced_spaces_functionality.py
chmod +x verify_enhanced_spaces_migration.py

# Option to run migration
echo ""
print_status "Migration Options:"
echo "1) Run Python migration (recommended)"
echo "2) Run SQL migration (faster, less error handling)"
echo "3) Skip migration (verification only)"
echo "4) Exit"
echo ""

read -p "Choose an option (1-4): " choice

case $choice in
    1)
        print_status "Running Python migration..."
        if python3 add_enhanced_spaces_functionality.py; then
            print_success "Python migration completed successfully!"
        else
            print_error "Python migration failed!"
            exit 1
        fi
        ;;
    2)
        print_status "Running SQL migration..."
        # Check if we have database connection info
        if [ -z "$DB_SCHEMA" ]; then
            export DB_SCHEMA=public
            print_warning "DB_SCHEMA not set, using 'public'"
        fi
        
        # This would require psql to be available and credentials to be set
        print_warning "SQL migration requires psql and proper database credentials"
        print_warning "Please run manually: psql -h localhost -U your_user -d your_db -v schema_name=$DB_SCHEMA -f add_enhanced_spaces_functionality.sql"
        ;;
    3)
        print_status "Skipping migration..."
        ;;
    4)
        print_status "Exiting..."
        exit 0
        ;;
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

# Run verification
echo ""
print_status "Running migration verification..."
if python3 verify_enhanced_spaces_migration.py; then
    print_success "✅ Verification completed successfully!"
    print_success "Enhanced spaces functionality is ready to use!"
else
    print_error "❌ Verification failed!"
    print_error "Please check the migration and try again"
    exit 1
fi

# Print next steps
echo ""
print_success "🎉 Enhanced Spaces Setup Complete!"
print_status "=================================================="
print_status "Next steps:"
print_status "1. Start your ThinkForge backend server"
print_status "2. Test the new spaces API endpoints at /v1/spaces"
print_status "3. Check out the new features:"
print_status "   • Template spaces with parameters"
print_status "   • Scheduled execution"
print_status "   • External storage (S3/GCS/Azure)"
print_status "   • Granular access control"
print_status "   • Space expiration and cleanup"
print_status ""
print_status "📚 Documentation:"
print_status "   • Migration guide: ENHANCED_SPACES_MIGRATION_GUIDE.md"
print_status "   • API documentation: ../backend/schemas/spaces.py"
print_status "   • Frontend integration: ../frontend-react/src/pages/Spaces.tsx"
print_status ""
print_success "Happy coding! 🚀"