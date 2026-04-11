FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.14-slim-bookworm

# OCI labels
LABEL org.opencontainers.image.title="GEDCOM MCP"
LABEL org.opencontainers.image.description="MCP server for local GEDCOM files — genealogy research via AI assistants"
LABEL org.opencontainers.image.url="https://gitlab.com/genealogy-mcp/gedcom-mcp"
LABEL org.opencontainers.image.source="https://gitlab.com/genealogy-mcp/gedcom-mcp"
LABEL org.opencontainers.image.documentation="https://gitlab.com/genealogy-mcp/gedcom-mcp/-/blob/main/README.md"
LABEL org.opencontainers.image.licenses="AGPL-3.0"
LABEL org.opencontainers.image.vendor="Genealogy-MCP"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["gedcom-mcp"]
