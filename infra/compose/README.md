compose

Docker Compose stacks for local and lab environments.

Current entrypoint UX (via the nginx `proxy` service on port 8080):

- `/` -> TheHive (single frontend)
- `/api/v1/` -> TheHive API
- `/ui/` -> (blocked) BloodHound UI is not publicly reachable
- `/embed/bloodhound?identity=<ref>` -> Embed entrypoint (returns internal redirect to BloodHound)
- `/_internal/bloodhound/` -> BloodHound (internal-only; reachable only via X-Accel-Redirect)

Local configuration:

- Copy `.env.example` to `.env` at the repo root to set passwords/secrets for your environment.
- `.env` is intentionally gitignored.
- For the proxy token bootstrap, `BLOODHOUND_INTERNAL_LOGIN_USERNAME` should be the BloodHound principal name (typically `admin`), not the admin email.

TheHive licensing (important)

- TheHive 5 uses StrangeBee licenses.
- The **Community license is free**, but it still must be **requested and activated** (official workflow).
- On newer TheHive 5 versions (5.3+), TheHive may start with a time-limited trial; when it expires and no valid license is installed, the UI can become limited/read-only and will show license prompts.

OSS-compliant fix for license prompts

1. Request a Community license (free): https://docs.strangebee.com/thehive/installation/licenses/request-a-community-license/
2. In TheHive, go to **Platform Management → License** and copy the **challenge**.
3. Use the StrangeBee portal to generate the activation key from that challenge.
4. Paste the activation key into TheHive to activate the license: https://docs.strangebee.com/thehive/installation/licenses/license/

Notes

- This repo intentionally does not ship any license material. Do not add “fake” keys or bypass checks.
- Once a valid Community license is activated, license-gated UI elements should stop blocking workflows.
