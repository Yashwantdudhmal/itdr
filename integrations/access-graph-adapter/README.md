access-graph-adapter

Read-only client that calls BloodHound over HTTP and returns normalized identity reachability data.

## Usage
- Configure BloodHound base URL and credentials (e.g., `http://localhost:8080`, admin user/password).
- Use `client.py`:
	- `BloodHoundClient.login()` authenticates via the BloodHound API.
	- `build_identity_report(identity_ref, critical_target_id)` returns the contract shape defined in docs/contracts/access-graph-adapter.md.
	- No direct Neo4j/Postgres access; all calls go through BloodHound APIs.

## Notes
- Requires Python 3 standard library only; no extra dependencies.
- Critical target IDs are optional and can point to a high-value role/object when a path is needed.
