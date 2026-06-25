# Installation

## Requirements

- Python 3.11 or newer
- Docker Engine
- Docker Compose v1 or v2
- Local permissions to run Docker and expose loopback services

## PyPI Install

```bash
pip install nsddos
```

## Source Install

```bash
git clone https://github.com/ns7523/nsddos.git
cd nsddos
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## First Run

```bash
nsddos setup
nsddos start
nsddos health --verbose
```

`nsddos setup` creates config and runtime directories. `nsddos start` brings up Floodlight, sFlowRT, labhost, detector, then launches UI on `http://127.0.0.1:8010`.

## Runtime Assets

NSDDOS prefers bundled runtime payloads from repo root. If those assets are not present locally, download release bundle:

```bash
nsddos bootstrap download
```

## Cloudflare Tunnel

### Cloudflare Tunnel

`nsddos ui expose` requires preinstalled `cloudflared`.

Common macOS install:

```bash
brew install cloudflared
```

Then run:

```bash
nsddos ui expose
```

Expected output:

```text
Local UI:   http://127.0.0.1:8010
Public UI:  https://<random>.trycloudflare.com
```
