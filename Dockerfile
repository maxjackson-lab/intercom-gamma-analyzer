# Stage 1: Build Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
# Copy only package files first for caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
# Copy frontend source
COPY frontend/ .
# Build SvelteKit app
RUN npm run build

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

# Cache-busting: Create unique file to force COPY layer rebuild
# Update timestamp below to invalidate Docker cache for COPY step
RUN echo "2025-11-28-20:35-template-debug" > /tmp/cache-bust.txt

# Copy rest of source code (respects .dockerignore)
COPY . .

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
