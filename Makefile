.PHONY: help install test lint format typecheck check-headers audit ci build clean run run-stdio

.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync --group dev

test: ## Run tests with coverage
	uv run coverage run -m pytest
	uv run coverage report

lint: ## Lint source and tests
	uv run ruff check src tests

format: ## Auto-format source and tests
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck: ## Run static type checker
	uv run pyright src

check-headers: ## Check AGPL copyright headers
	find src/ scripts/ -name '*.py' -exec uv run python scripts/check_copyright_header.py {} +

audit: ## Run security audit
	uv run pip-audit

ci: lint typecheck check-headers test audit ## Run full CI pipeline locally

build: ## Build wheel
	uv build

clean: ## Remove build artifacts and caches
	rm -rf dist build .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +

run: ## Run with streamable-http transport on port 8000
	uv run gedcom-mcp --transport streamable-http --host 127.0.0.1 --port 8000

run-stdio: ## Run with stdio transport
	uv run gedcom-mcp
