FROM python:3.9-slim

WORKDIR /app

# Copy only backend code
COPY . /app/
# Copy README.md from root to resolve setup.py dependency
COPY ../README.md /app/../README.md

# Install dependencies for the backend server
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install the NL cache framework
RUN pip install --no-cache-dir -e .

# Environment variables
ENV PORT=8000
ENV MCP_DB_URL=sqlite:///./mcp_cache.db
ENV DEFAULT_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
ENV SIMILARITY_THRESHOLD=0.85
ENV SESSION_TTL=3600
ENV SESSION_CLEANUP_INTERVAL=300
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 