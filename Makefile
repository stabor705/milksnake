.PHONY: help install install-dev test lint format run run-config run-dev build

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install project dependencies"
	@echo "  make install-dev  - Install project with dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter (ruff)"
	@echo "  make format       - Format code with black"
	@echo "  make run          - Run the milksnake application (default settings)"
	@echo "  make run-config   - Run with config.yaml"
	@echo "  make run-dev      - Run on port 8080 for development"
	@echo "  make build        - Build the package"

# Install project dependencies
install:
	uv sync

# Install with dev dependencies
install-dev:
	uv sync --dev

# Run tests
test:
	uv run pytest

# Run linter
lint:
	uv run ruff check .

# Format code
format:
	uv run black .

# Run the application
run:
	uv run python -m milksnake.main

# Run with config file
run-config:
	uv run python -m milksnake.main --config config.yaml

# Run on development port
run-dev:
	uv run python -m milksnake.main --port 8080

# Build the package
build:
	uv build
