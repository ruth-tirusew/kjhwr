# Build with the repository root as context: docker build -f backend/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
# The API never calls Elexon at runtime, so the blessed snapshot is baked into the image.
COPY data/snapshots ./data/snapshots
ENV SNAPSHOT_DIR=/app/data/snapshots
EXPOSE 8000
# Render injects $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
