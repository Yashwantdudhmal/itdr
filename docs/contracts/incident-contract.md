# Incident Contract

This contract defines the incident record stored by the Incident Coordinator for Feature #1: assumption-based incident declaration.

Core principles:

- `identity_ref` is an opaque string. The platform does not parse it, validate it, or resolve it.
- `assumption` is free text provided by the caller (for example: "Assume this identity is compromised.").
- The platform does not validate that compromise occurred and does not imply detection.
- Incident creation is declaration-only. No enrichment, no recommendations, and no execution are performed.

## Incident object (JSON)

```json
{
  "incident_id": "4b6c3b5a-1df1-4ec7-8c40-2c7c7fba6c8a",
  "identity_ref": "totally-fake-identity-123",
  "assumption": "Assume this identity is compromised.",
  "source": "manual",
  "status": "open",
  "created_at": "2026-01-06T12:00:00Z"
}
```

Constraints:

- `source` must be one of: `manual` | `api` | `soc_tool`.
- `status` is always `open` at creation.
- The incident record contains only the fields shown above.
