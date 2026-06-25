# Developer Guide

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Test Suites

Fast feedback:

```bash
pytest tests/test_bootstrap_terminal.py tests/test_ui_layer.py tests/test_cli_productization.py
```

Broader regression sweep:

```bash
pytest tests/test_attack_live_engine.py tests/test_start_orchestrator.py tests/e2e/test_runtime_commands.py
```

## Productization Files

- `README.md` for public GitHub landing page
- `docs/` for install, architecture, CLI, troubleshooting, runtime assets
- `.github/ISSUE_TEMPLATE/` for repo intake
- `src/nsddos/ui/static/brand/` for shared UI branding

## Scope Guardrails

- Preserve existing runtime, detection, mitigation, and packaging seams
- Prefer additive docs/UI polish over refactors
- Validate real CLI behavior after test success when startup or UI exposure changes
