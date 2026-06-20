VENV ?= .venv
PYTHON ?= python3
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: install dev test lint format run clean

install:
	$(PYTHON) -m venv $(VENV) --system-site-packages
	. $(VENV)/bin/activate && pip install -e . --no-build-isolation

dev: install
	. $(VENV)/bin/activate && pip install -e ".[dev]" --no-build-isolation

test:
	. $(VENV)/bin/activate && pytest

lint:
	. $(VENV)/bin/activate && ruff check src tests && mypy src

format:
	. $(VENV)/bin/activate && isort src tests && black src tests

run:
	. $(VENV)/bin/activate && nsddos health --verbose

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
