# Access Graph Adapter Contract

This contract defines the read-only interface exposed by the access-graph adapter. It must remain stable even if BloodHound is replaced later.

## Identity reference (input)
Single object representing the identity to resolve:

```json
{
  "id": "<object-id-guid>",
  "upn": "<user-or-sp-upn>",
  "display_name": "<friendly name>",
  "type": "user|service_principal"
}
```

- At least one of `id` or `upn` MUST be provided.
- `type` is advisory; adapters SHOULD attempt to resolve even if missing.

## Output shape
Adapter responses are read-only snapshots from the upstream graph engine.

```json
{
  "identity": { "id": "...", "upn": "...", "display_name": "...", "type": "..." },
  "reachable_assets": [
    {
      "id": "<object-id-or-graph-id>",
      "name": "<resource name>",
      "kind": "application|group|role|subscription|resource",
      "via": "membership|role|ownership|path",
      "confidence": "graph"
    }
  ],
  "critical_paths": [
    {
      "from": "<identity-id>",
      "to": "<target-id>",
      "length": 4,
      "hops": [
        { "id": "<node-id>", "type": "user|group|role|device|application", "edge": "MemberOf" }
      ]
    }
  ],
  "privilege_classification": [
    {
      "target_id": "<asset-id>",
      "privilege": "admin|write|read|execute",
      "evidence": "role_assignment|ownership|risky_path",
      "source": "bloodhound"
    }
  ]
}
```

### Semantics
- `reachable_assets`: unique assets reachable from the identity by direct membership or explicit role assignment (no path computation required).
- `critical_paths`: shortest paths to high-value nodes (e.g., Global Administrator, subscription owner). The adapter returns raw hops; consumers do their own evaluation.
- `privilege_classification`: coarse labels derived from BloodHound path/role metadata; no policy decisions or scoring performed here.

## Error handling
- `404` if the identity cannot be resolved upstream.
- `502` if the upstream BloodHound API is unavailable.
- `500` for unexpected adapter failures (caller may retry).

## Non-goals
- No caching of graph data.
- No direct database access (Neo4j/Postgres).
- No business logic, ranking, or incident automation.
