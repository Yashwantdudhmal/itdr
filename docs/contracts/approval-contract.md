# Approval Contract

This contract defines the approval records stored by the Approval Gateway.

- Approval records are metadata only (who/when/what).
- Identity references are opaque strings when present.
- No execution implied.

## Approval record (JSON)

```json
{
  "incident_id": "4b6c3b5a-1df1-4ec7-8c40-2c7c7fba6c8a",
  "action_id": "revoke_sessions",
  "approver": "opaque://identity/approver-1",
  "recorded_at": "2026-01-06T12:05:00+00:00",
  "status": "approved"
}
```

## List approvals response (example)

```json
[
  {
    "incident_id": "4b6c3b5a-1df1-4ec7-8c40-2c7c7fba6c8a",
    "action_id": "revoke_sessions",
    "approver": "opaque://identity/approver-1",
    "recorded_at": "2026-01-06T12:05:00+00:00",
    "status": "approved"
  },
  {
    "incident_id": "4b6c3b5a-1df1-4ec7-8c40-2c7c7fba6c8a",
    "action_id": "disable_identity",
    "approver": "opaque://identity/approver-1",
    "recorded_at": "2026-01-06T12:06:00+00:00",
    "status": "rejected"
  }
]
```
