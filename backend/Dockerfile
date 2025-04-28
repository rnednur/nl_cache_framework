FROM python:3.9-slim

WORKDIR /app

# Copy backend and frontend code separately
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Install dependencies for the backend server
WORKDIR /app/backend
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install the NL cache framework (assuming setup.py is in backend/)
# If setup.py is at the root, this needs adjustment
RUN pip install --no-cache-dir -e .

# Set final working directory to the backend
WORKDIR /app/backend

# Environment variables
ENV PORT=8000
ENV MCP_DB_URL=sqlite:///./mcp_cache.db
ENV DEFAULT_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
ENV SIMILARITY_THRESHOLD=0.85
ENV SESSION_TTL=3600
ENV SESSION_CLEANUP_INTERVAL=300
# Set PYTHONPATH to the root app directory, editable install should handle the rest
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application from the backend directory
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 