# syntax=docker/dockerfile:1
# Muse in one image: the React website is built in a Node stage, then served by the
# FastAPI backend at /app/, next to the API. The same result as the Render build.
#   docker build -t muse .        (or: docker compose up --build)

# ---- Stage 1: build the website ----
FROM node:22-bookworm-slim AS web
WORKDIR /web
# Install dependencies first, so Docker reuses this layer until the package files change
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: the backend, which serves the API and the website ----
FROM python:3.12.10-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FRONTEND_DIST=/srv/frontend/dist
WORKDIR /srv/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/app ./app
# Only the built website is copied from stage 1: no Node or node_modules in the final image
COPY --from=web /web/dist /srv/frontend/dist

# Never run as root inside the container
RUN useradd --create-home --uid 10001 muse
USER muse

EXPOSE 8000
# Docker (and docker compose --wait) mark the container unhealthy if /health stops answering
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
