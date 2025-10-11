.PHONY: help install dev-install check-style test clean venv

VENV = alix-venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv:  ## Create virtual environment
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install: venv  ## Install alix in production mode
	$(PIP) install -e .

dev-install: venv  ## Install alix with dev dependencies
	$(PIP) install -e ".[dev]"

check-style: dev-install  ## Run style checks
	$(VENV)/bin/flake8 alix --count --show-source --statistics
	$(VENV)/bin/flake8 tests --count --show-source --statistics

test: dev-install  ## Run tests
	$(VENV)/bin/pytest

clean:  ## Clean up generated files
	rm -rf $(VENV)
	rm -rf *.egg-info
	rm -rf dist/
	rm -rf build/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

run: install  ## Run alix
	$(VENV)/bin/alix