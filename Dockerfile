# Stage 1: Build Frontend (optional - skip if frontend not ready)
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
# Copy all frontend files at once (handles missing package-lock.json gracefully)
COPY frontend/ ./
# Install dependencies (use npm install if package-lock.json missing)
RUN if [ -f package-lock.json ]; then npm ci; else npm install --no-save; fi
# Build SvelteKit app (only if package.json exists)
RUN if [ -f package.json ] && [ -d src ]; then npm run build || echo "Frontend build skipped"; else echo "No frontend to build"; fi

# Stage 2: Python Application
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Force rebuild timestamp: 2025-11-28-20:30-template-debug
# (Updated for frontend integration)
# Cache-busting: Update timestamp above to force COPY layer rebuild

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-railway.txt requirements.txt

# Copy the Intercom SDK (needed for installation)
COPY python-intercom-master/ /app/python-intercom-master/

# Install SDK dependencies first
RUN pip install --no-cache-dir -r /app/python-intercom-master/requirements.txt

# Install main application dependencies (now SDK is available)
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of source code (respects .dockerignore)
COPY . .

# Copy deploy/web LAST to always get latest templates.py
# This forces a cache miss when templates change, overwriting any cached version
COPY deploy/web/ /app/deploy/web/

# Copy frontend build artifacts from builder stage
COPY --from=frontend-builder /app/frontend/build /app/frontend/build

# Set Python path (include SDK)
ENV PYTHONPATH=/app:/app/src:/app/python-intercom-master/src

# Create output and static directories
RUN mkdir -p /app/outputs /app/static

# Ensure static files are present (legacy frontend)
COPY static/ /app/static/

# Expose port for web interface
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden by Railway)
CMD ["python", "deploy/railway_web.py"]
