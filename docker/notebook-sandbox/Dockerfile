# Dockerfile for Python Notebook Sandbox Environment
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 sandbox && \
    mkdir -p /sandbox/notebooks /sandbox/output && \
    chown -R sandbox:sandbox /sandbox

# Install Python dependencies for notebook execution
COPY requirements-sandbox.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-sandbox.txt

# Set working directory
WORKDIR /sandbox

# Copy sandbox execution scripts
COPY scripts/ /sandbox/scripts/
RUN chmod +x /sandbox/scripts/*.py

# Switch to non-root user
USER sandbox

# Set environment variables
ENV PYTHONPATH=/sandbox
ENV JUPYTER_ENABLE_LAB=yes
ENV JUPYTER_TOKEN=""

# Expose Jupyter port
EXPOSE 8888

# Default command - run Jupyter lab
CMD ["python", "/sandbox/scripts/run_notebook.py"]