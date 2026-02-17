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

# Копируем entrypoint ВНЕ /app — volume ./api:/app его не перезапишет
# sed удаляет \r (Windows CRLF)
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

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

# Expose API port
EXPOSE 8001

# entrypoint лежит в /entrypoint.sh — вне volume-mount /app
ENTRYPOINT ["sh", "/entrypoint.sh"]
