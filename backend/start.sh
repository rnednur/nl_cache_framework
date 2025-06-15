#!/bin/bash

# This script assumes it is run from the backend directory

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if the virtual environment exists at the root
if [ ! -d "../venv" ]; then
    echo "Creating virtual environment in project root..."
    python3 -m venv ../venv
fi

# Activate the virtual environment
source ../venv/bin/activate

# Install requirements from the backend directory
echo "Installing requirements..."
pip install -r requirements.txt

# Install the NL cache framework from the backend directory
echo "Installing the NL cache framework (editable)..."
# Assuming setup.py is in backend/
pip install -e .

# Start the server using uvicorn directly
echo "Starting the MCP server with Uvicorn..."
export DEBUG=true
# PORT environment variable will be used by uvicorn if set, otherwise defaults to 8000
uvicorn app:app --reload --host 0.0.0.0 --port ${PORT:-8000} 