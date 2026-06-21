# NS-DDoS

NS-DDoS is production-oriented cybersecurity framework for IoT DDoS detection, simulation, telemetry ingestion, mitigation orchestration.

Current scope in this scaffold:
- Python package foundation
- installable CLI
- YAML config system
- structured logging
- extensible module layout
- Docker runtime orchestration foundation
- provider-backed SDN lab runtime wiring

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Linux Quickstart

Single clone is enough. No sibling `floodlight`, `ns-ddos`, or `mininet` repo checkouts required.

```bash
git clone https://github.com/ns7523/nsddos.git
cd nsddos
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d floodlight labhost sflowrt detector
python -m nsddos health
python -m nsddos verify
```

## CLI Usage

```bash
nsddos version
nsddos health
nsddos health --verbose
nsddos doctor
nsddos doctor --deep
nsddos verify
nsddos lab status
nsddos lab start
nsddos lab stop
nsddos lab logs
nsddos lab snapshot
nsddos lab compare-snapshots <old> <new>
nsddos runtime timeline
nsddos runtime explain-timeline
nsddos runtime explain-correlation
nsddos runtime explain-stability
nsddos runtime explain-environment
nsddos runtime explain-pipeline
nsddos runtime explain-verification
nsddos runtime replay-verification
nsddos runtime explain-query
nsddos runtime query-snapshots
nsddos runtime query-evidence
nsddos runtime query-verification
nsddos runtime query-timeline
nsddos runtime query-graph
nsddos runtime query-replay
nsddos api routes
nsddos api explain
nsddos api start
nsddos runtime validate-traffic
nsddos runtime validate-bootstrap
nsddos runtime bootstrap
nsddos runtime shutdown
nsddos runtime use-preset minimal-lab
nsddos runtime evidence
nsddos runtime install-guide
nsddos runtime explain
nsddos runtime explain-ports
nsddos runtime explain-paths
nsddos runtime explain-controller
nsddos runtime explain-convergence
nsddos runtime export-environment
nsddos runtime export-graph
nsddos runtime export-history
nsddos runtime export-pipeline
nsddos runtime export-relationships
nsddos runtime export-bundle
```

## Architecture Vision

Framework organized around clear domains:
- `detector/` for detection engines
- `telemetry/` for collectors and parsers
- `mitigation/` for response orchestration
- `providers/` for external system adapters
- `api/` for service interfaces
- `ui/` for future user interface integration
- `models/` for runtime model metadata and loading contracts

Core bootstrap concerns stay in:
- `cli.py`
- `config.py`
- `logger.py`
- `constants.py`
- `health.py`
- `docker_manager.py`

## Runtime API

The API layer is read-only-first and query-backed. Endpoints expose runtime
state, verification, evidence, snapshots, graph, timeline, replay, convergence,
drift, and stability through the runtime query and verification engines only.
Providers and orchestration are not exposed directly.

```bash
nsddos api routes
nsddos api explain
nsddos api start --host 127.0.0.1 --port 8008
```

## Runtime Architecture

Local lab runtime uses Docker Compose as platform layer first.
Canonical runtime target is Linux-first, profile-aware, reproducibility-driven.
Runtime bootstrap now follows explicit canonical pipeline phases.

Current runtime services:
- `floodlight`
- `sflowrt`
- `detector`
- `mininet` via provider orchestration on host

<<<<<<< HEAD
Bundled runtime assets live inside repo:
- `external/floodlight/target/floodlight.jar`
- `external/floodlight/logback.xml`
- `external/sflowrt/`
=======
Clean clone deployment entrypoint:

```bash
docker compose up -d --build
docker compose ps
```

Canonical compose file lives at repository root as `docker-compose.yml`.
Compat copies remain under `code/nsddos/`.
>>>>>>> 7b0b4a3 (Initial NSDDOS v4.0 release candidate)

Runtime state persists in `~/.nsddos/runtime/state.json`.
Evidence bundles persist in `~/.nsddos/runtime/evidence/`.
Temporal history exports persist in `~/.nsddos/runtime/history/`.
Pipeline snapshots persist in `~/.nsddos/runtime/pipeline/`.

## Requirements

- Python 3.11+
- Docker Engine
- Docker Compose v2 (`docker compose`)

## Provider System

Provider layer defines stable contracts for external systems before real networking logic lands.
Current providers:
- Floodlight
- sFlow-RT
- Mininet
- OVS

## Environment Overrides

- `NSDDOS_HOME`
- `NSDDOS_CONFIG`
- `NSDDOS_COMPOSE_FILE`
- `NSDDOS_MININET_BIN`

## Runtime Profiles

Supported profile models:
- `linux-native`
- `docker-linux`
- `wsl2`
- `macos-degraded`

Canonical reproducible runtime artifacts live under `docker/runtime/`.

## Roadmap

- detection pipelines
- provider integrations
- API service layer
- dashboard backend/frontend split
- containerized local platform
- release workflow for PyPI
- layered verification and CI stabilization

## License

MIT
