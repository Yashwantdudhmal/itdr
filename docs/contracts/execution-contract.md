# Execution Contract

This contract defines the execution boundary.

- Input is approved-action oriented.
- `identity_ref` is an opaque string.
- Parameters are an opaque map.
- No execution implied by recording approvals alone.

## Input (JSON)

```json
{
  "incident_id": "4b6c3b5a-1df1-4ec7-8c40-2c7c7fba6c8a",
  "action_id": "disable_identity",
  "identity_ref": "opaque://identity/12345",
  "parameters": {
    "reason": "Containment"
  }
}
```

## Output (JSON)

```json
{
  "execution_id": "b7b3a0a2-2c8c-4e23-8e7b-0b0c9c5b9d5c",
  "status": "success",
  "reversible": true,
  "revert_hint": {}
}
```

## Status values

```json
{
  "status": "failed"
}
```

## Rollback placeholder

A future rollback call is expected to exist:

```json
{
  "execution_id": "b7b3a0a2-2c8c-4e23-8e7b-0b0c9c5b9d5c"
}
```

Rollback behavior is execution-engine dependent and not defined in this phase.
