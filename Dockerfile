FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if required (e.g. systemctl for simulations)
RUN apt-get update && apt-get install -y systemd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sre_pipeline/ /app/sre_pipeline/
