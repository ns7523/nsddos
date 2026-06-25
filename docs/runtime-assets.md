# Runtime Assets

NSDDOS runtime depends on Floodlight and sFlowRT payloads plus Docker templates.

## Required Files

- `external/floodlight/floodlight.jar`
- `external/floodlight/logback.xml`
- `external/floodlight/floodlightdefault.properties`
- `external/sflowrt/start.sh`
- `external/sflowrt/lib/sflowrt.jar`

## Required Directories

- `external/sflowrt/app`
- `external/sflowrt/resources`
- `external/sflowrt/store`
- `docker`

## Resolution Order

1. `NSDDOS_ASSET_ROOT` override
2. repo-local bundled payloads
3. cached runtime release under `~/.nsddos/cache/releases`
4. packaged templates

## Download

```bash
nsddos bootstrap download
```

Use this when local repo does not already carry runtime payloads.
