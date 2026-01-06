compose

Docker Compose stacks for local and lab environments.

Current entrypoint UX (via the nginx `proxy` service on port 8080):

- `/` -> TheHive (single frontend)
- `/api/v1/` -> TheHive API
- `/ui/` -> BloodHound (read-only investigation surface)
- `/api/` + `/ws` -> BloodHound backend/WebSocket support (needed for BloodHound UI under `/ui/`)

Local configuration:

- Copy `.env.example` to `.env` at the repo root to set passwords/secrets for your environment.
- `.env` is intentionally gitignored.
