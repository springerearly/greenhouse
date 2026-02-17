# Use Python 3.9 slim as base
FROM python:3.9-slim

# Install pg_isready (postgresql-client) for the entrypoint health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    passwd \
    && rm -rf /var/lib/apt/lists/*

# Создаём группу gpio с GID 997 (совпадает с Raspberry Pi OS),
# чтобы group_add: "997" в docker-compose работал корректно
RUN groupadd -g 997 gpio || true

# Set the working directory
WORKDIR /app

# Copy and install Python dependencies (layer cached separately)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY ./app ./app

# Copy Alembic configuration and migrations
COPY alembic.ini .
COPY alembic ./alembic

# Copy entrypoint script and make it executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose API port
EXPOSE 8001

# Default command — runs migrations then starts uvicorn
ENTRYPOINT ["./entrypoint.sh"]
