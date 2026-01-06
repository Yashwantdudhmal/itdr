# platform-app (Feature #1)

Minimal HTML + API server for assumption-based identity incident creation.

## Run

From repo root:

```powershell
python .\platform-app\server.py --host 127.0.0.1 --port 8090
```

## UI

- http://127.0.0.1:8090/platform/incidents
- http://127.0.0.1:8090/platform/incidents/new

## API

- `GET /api/incidents` → list incidents
- `POST /api/incidents` → create incident (`identity_ref`, `assumption`, `source`)
- `GET /api/incidents/{incident_id}` → get incident
