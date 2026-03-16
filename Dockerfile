FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/

RUN uv sync --locked --no-dev --no-editable

FROM python:3.14-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["gedcom-mcp"]
