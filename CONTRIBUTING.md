# Contributing

## Workflow

1. Create focused branch.
2. Keep scope surgical.
3. Run targeted tests for touched surfaces.
4. Update docs when public behavior changes.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Test Minimum

```bash
pytest tests/test_bootstrap_terminal.py tests/test_ui_layer.py tests/test_cli_productization.py
```

Add broader runtime tests when CLI, startup, or lab behavior changes.
