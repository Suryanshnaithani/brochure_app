# Production Dockerfile for Brochure Analyzer on Render
FROM python:3.11-slim

# Install system dependencies & Node.js for Reflex compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Initialize and compile Reflex app
RUN reflex init
RUN reflex compile

# Expose port
EXPOSE 8000

# Run Reflex in production mode
CMD ["reflex", "run", "--env", "prod"]
