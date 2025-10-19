# ---------- Base: Python 3.12 slim ----------
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files & enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (minimal). libpq5 = runtime for psycopg; build-essential only if wheels not available.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libpq5 build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------- Install uv (dependency manager) ----------
# Official installer puts uv into ~/.local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Use an in-project venv managed by uv (keeps runtime clean and easy)
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
# Recommended for Docker: copy venv contents instead of symlinking system libs
ENV UV_LINK_MODE=copy
# Make sure our venv is used by default
ENV PATH="/app/.venv/bin:${PATH}"

# ---------- Dependency layer (max cache) ----------
# Copy only files that affect dependency resolution first
COPY pyproject.toml uv.lock ./

# Install only dependencies (not the project) — best for caching
# --frozen ensures uv.lock is respected exactly
RUN uv sync --frozen --no-install-project

# ---------- App layer ----------
# Now copy the whole project
COPY . .

# Install the project itself (editable off by default, produces shortest image)
RUN uv sync --frozen

# Optional: create a non-root user (uncomment if you want non-root runtime)
# RUN useradd -m appuser && chown -R appuser:appuser /app
# USER appuser

# We don't copy .env; Compose will inject it via `env_file: .env`
# Default command (overridden by docker-compose for migrate/seed)
CMD ["python", "main.py"]
