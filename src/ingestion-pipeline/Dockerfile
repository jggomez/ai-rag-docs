# Use a multi-stage build for efficiency
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Final stage
FROM python:3.12-slim-bookworm

# Create non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup appuser

WORKDIR /app

# Copy the environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy the source code
COPY . .

# Pre-download the FlashRank model during build time
RUN .venv/bin/python -c "from flashrank import Ranker; Ranker(model_name='ms-marco-TinyBERT-L-2-v2', cache_dir='/tmp/flashrank_cache_v2')"

# Change ownership of /app to the non-root user
RUN chown -R appuser:appgroup /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER appuser

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
