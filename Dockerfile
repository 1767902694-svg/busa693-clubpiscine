# ClubPiscine MMM Pipeline Image
#
# One image, three jobs. Switch which runs via "Arguments override" in Azure:
#   Job 1: python jobs/clean_to_silver.py
#   Job 2: python jobs/weather_to_silver.py
#   Job 3: python jobs/silver_to_gold.py

FROM python:3.11-slim

LABEL maintainer="ClubPiscine Data Team"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal OS deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Install ONLY the jobs requirements (not the notebook one at repo root)
COPY jobs/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all job code
COPY jobs/ ./jobs/

# Default job — override Arguments in Azure Container App to run a different job
CMD ["python", "jobs/clean_to_silver.py"]