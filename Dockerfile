FROM python:3.10-slim

WORKDIR /app

# Install system deps (safe + lightweight)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command (keeps container alive for manual runs)
CMD ["sleep", "3600"]
