FROM python:3.14-slim AS base
WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install runtime dependencies first (cache layer)
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache \
    alembic fastapi httpx pydantic pydantic-settings pyyaml rich \
    sqlmodel structlog typer uvicorn jinja2 python-multipart websockets textual

# Copy source and project files
COPY README.md ./
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini ./
COPY topologies/ topologies/

# Install the project itself (resolves entry points)
RUN uv pip install --system --no-cache .

# Default: run the stitch-workbench (main backend)
EXPOSE 8000
CMD ["uvicorn", "stitch_workbench.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
