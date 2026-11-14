# SafeMeds 3D Graph Studio — Production Dockerfile
# Multi-hop pharmacological safety graph engine powered by Relate by Neo4j

FROM python:3.11-slim

LABEL maintainer="fokrulanthro16-eng"
LABEL description="SafeMeds 3D Graph Studio - Relate by Neo4j Hackathon Winner"

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system utilities for health monitoring
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install lean runtime dependencies
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy application backend, frontend, and persistent Relate database
COPY server/ ./server/
COPY static/ ./static/
COPY data/ ./data/
COPY scripts/test_hardening.py ./scripts/
COPY verify_safemeds.py .

# Expose HTTP port
EXPOSE 8000

# Container healthcheck against local Relate store status
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/health || exit 1

# Launch FastAPI via uvicorn on 0.0.0.0:8000
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
