FROM python:3.11-slim

WORKDIR /app

COPY weather_ingest_uc4.py /app/weather_ingest_uc4.py

RUN pip install --no-cache-dir requests azure-storage-blob

CMD ["python", "/app/weather_ingest_uc4.py"]