# Architecture

NSDDOS keeps backend seams intact and layers operator tooling on top of four runtime pillars:

- Floodlight for SDN controller state and flow programming
- sFlowRT for telemetry ingestion and flow analytics
- Mininet for deterministic lab topology and attack targets
- Open vSwitch for mitigation insertion and verification

## Runtime Flow

1. Docker Compose brings up `nsddos-floodlight`, `nsddos-sflowrt`, `nsddos-labhost`, and `nsddos-detector`.
2. Mininet topology exports telemetry toward sFlowRT.
3. Detection engine classifies live or replayed traffic.
4. Mitigation policy selects action and pushes controller plus OVS changes.
5. UI reads runtime state and evidence through existing read-only surfaces.

## Public Commands

- `nsddos start` boots stack and UI
- `nsddos demo` runs stack, launches live attack, evaluates detection, enforces mitigation
- `nsddos ui expose` tunnels local dashboard through Cloudflare

## Operator Surface

UI stays read-only and cyber-ops themed. Browser routes render from current FastAPI UI app while attack execution remains in existing runtime and lab seams.

## Design Constraints

- No backend architecture redesign
- No ML engine changes
- No packaging changes
- No new control-plane subsystem
