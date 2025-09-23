# Dockerfile
FROM python:3.11-slim

# System setup
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install build deps only if needed (kept minimal here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Copy reqs and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . /app

# Expose (Fly will map externally)
ENV PORT=8000
EXPOSE 8000

# Start (one worker; scale with Fly)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
