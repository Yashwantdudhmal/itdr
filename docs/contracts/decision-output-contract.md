# Decision Output Contract

This contract defines the output of Decision Engine v0.

- Deterministic and static.
- `identity_ref` is treated as an opaque string by the engine.
- No execution implied.

## Input (example)

```json
{
  "identity_ref": "opaque://identity/12345",
  "reachable_assets": [],
  "critical_paths": []
}
```

## Output (JSON)

```json
{
  "recommendations": [
    {
      "action": "revoke_sessions",
      "safety": "safe",
      "reversible": true,
      "impact": "No service disruption expected"
    },
    {
      "action": "remove_specific_role",
      "safety": "medium",
      "reversible": true,
      "impact": "Some access may be removed for the identity"
    },
    {
      "action": "disable_identity",
      "safety": "high_risk",
      "reversible": true,
      "impact": "Identity will be unable to authenticate"
    }
  ]
}
```
