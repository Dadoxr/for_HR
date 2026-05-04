.PHONY: help install test test-cov run dev clean venv

VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest
UVICORN = $(VENV)/bin/uvicorn

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test        - Run tests"
	@echo "  make test-cov    - Run tests with coverage"
	@echo "  make run         - Run application"
	@echo "  make dev         - Run application in development mode"
	@echo "  make clean       - Clean temporary files"
	@echo "  make venv        - Create virtual environment"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
	fi

install: venv
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip -q
	$(PIP) install -q -r requirements.txt
	$(PIP) install -q -r test_requirements.txt
	@echo "Dependencies installed"

test: venv
	@if [ ! -f "$(PYTEST)" ]; then \
		echo "Installing test dependencies..."; \
		$(MAKE) install; \
	fi
	@echo "Running tests..."
	$(PYTEST) tests/ -v

test-cov: venv
	@if [ ! -f "$(PYTEST)" ]; then \
		echo "Installing test dependencies..."; \
		$(MAKE) install; \
	fi
	@echo "Running tests with coverage..."
	$(PYTEST) tests/ --cov=app --cov-report=html --cov-report=term -v

run: venv
	@if [ ! -f "$(UVICORN)" ]; then \
		echo "Installing dependencies..."; \
		$(MAKE) install; \
	fi
	@echo "Starting application..."
	$(UVICORN) main:app --host 0.0.0.0 --port 8000

dev: venv
	@if [ ! -f "$(UVICORN)" ]; then \
		echo "Installing dependencies..."; \
		$(MAKE) install; \
	fi
	@echo "Starting application in development mode..."
	$(UVICORN) main:app --host 0.0.0.0 --port 8000 --reload

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.db" -delete 2>/dev/null || true
	find . -type f -name "*.sqlite" -delete 2>/dev/null || true
	@echo "Cleanup complete"

