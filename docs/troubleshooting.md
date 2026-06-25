# Troubleshooting

## `nsddos demo` fails before startup

Run:

```bash
nsddos health --verbose
```

Common causes:

- Docker daemon not running
- runtime asset bundle missing
- compose file missing or overridden incorrectly
- Floodlight or sFlowRT artifacts unavailable

## `nsddos start` fails on service health

Check:

```bash
nsddos health --verbose
nsddos lab logs
```

Look for failures in:

- `containers`
- `floodlight`
- `sflowrt`
- `mininet`
- `ovs`

## `nsddos ui expose` fails

- Ensure local UI responds on `http://127.0.0.1:8010/ui/healthz`
- Ensure `cloudflared` exists in `PATH`
- Re-run after `brew install cloudflared` on macOS

## UI opens but looks stale

`nsddos ui start` already replaces stale listeners on port `8010`. If another process owns that port, stop it and rerun.

## Runtime assets missing

If bundled assets are not present:

```bash
nsddos bootstrap download
```
