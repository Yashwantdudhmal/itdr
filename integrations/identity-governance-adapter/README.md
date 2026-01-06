identity-governance-adapter

Execution-only adapter for an identity governance engine.

Responsibilities:
- Translate approved actions into execution API calls
- Handle authentication, secrets, and limited retries
- Return execution result metadata

Non-responsibilities:
- No decision logic
- No approvals
- No identity discovery
- No state storage beyond execution result metadata

Supported actions (only):
- revoke_sessions
- disable_identity
- remove_role
