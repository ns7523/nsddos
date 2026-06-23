# NS-DDoS

NS-DDoS is Linux-first IoT DDoS lab and runtime verification framework. Standalone repo root is deployment root. No sibling `floodlight`, `ns-ddos`, or `mininet` checkout required.

## Quickstart

```bash
git clone https://github.com/ns7523/nsddos.git
cd nsddos
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
docker-compose up --build -d
python -m nsddos health
python -m nsddos verify
```

`docker compose up --build -d` works too. Canonical deploy entrypoint is repo-root `docker-compose.yml`.

## Bundled Runtime Assets

Repo carries runtime payload required for clean-clone deployment:
- `external/floodlight/floodlight.jar`
- `external/floodlight/logback.xml`
- `external/floodlight/floodlightdefault.properties`
- `external/sflowrt/start.sh`
- `external/sflowrt/lib/`
- `external/sflowrt/app/`
- `external/sflowrt/resources/`
- `external/sflowrt/store/`

## Runtime Surfaces

Primary commands:

```bash
nsddos health
nsddos verify
nsddos lab start
nsddos lab stop
nsddos lab logs
nsddos api routes
nsddos api explain
nsddos api start
nsddos runtime install-guide
nsddos runtime validate-bootstrap
nsddos runtime export-environment
```

Runtime services:
- `labhost`
- `floodlight`
- `sflowrt`
- `detector`

Runtime state persists under `.nsddos-home/` by default, or `NSDDOS_HOME` when set.

## Requirements

- Python 3.11+
- Docker Engine
- Docker Compose v1 (`docker-compose`) or v2 (`docker compose`)

## Environment Overrides

- `NSDDOS_HOME`
- `NSDDOS_CONFIG`
- `NSDDOS_COMPOSE_FILE`
- `NSDDOS_MININET_BIN`

## License

MIT
