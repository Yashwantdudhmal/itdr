# UI Composition (OSS UI Only)

Approach chosen: Option B (side-by-side UI via proxy routing, same origin).

- BloodHound UI remains the primary UI shell at `/`.
- A minimal platform surface is exposed under `/platform/*` via the existing reverse proxy.
- No new frontend framework/app is introduced; pages are simple server-rendered HTML.

Navigation:
- Start in BloodHound (`/`)
- Click the injected link `Incidents` → `/platform/incidents`
- Drill into incident details, view decision, approve/reject actions, and view executions
- Use `Back to BloodHound` to return to `/`

Security/boundaries:
- Browser talks only to the proxy (same origin).
- UI does not connect to the execution engine directly.
- Execution is triggered server-side only after an approval is recorded.
