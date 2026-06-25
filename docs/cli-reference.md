# CLI Reference

## Bootstrap

```bash
nsddos setup
nsddos start
nsddos stop
nsddos status
nsddos health
nsddos doctor
nsddos verify
```

## Demo

```bash
nsddos demo
nsddos demo --attack syn_flood
```

`nsddos demo` validates static prerequisites, starts runtime if needed, runs live attack traffic, evaluates detection, enforces mitigation, and opens dashboard automatically.

## UI

```bash
nsddos ui start
nsddos ui status
nsddos ui explain
nsddos ui expose
```

## Lab

```bash
nsddos lab start
nsddos lab stop
nsddos lab status
nsddos lab logs
nsddos lab snapshot
```

## Runtime

```bash
nsddos runtime detect
nsddos runtime mitigate
nsddos runtime enforce-mitigation
nsddos runtime attack-live
nsddos runtime provider-health
nsddos runtime install-guide
```

## Assets

```bash
nsddos bootstrap download
```
