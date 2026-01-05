"""BloodHound access graph adapter (read-only).

Connects to the BloodHound HTTP API, retrieves identities and reachable assets,
computes critical paths via the API, and returns normalized dictionaries that
match docs/contracts/access-graph-adapter.md.

No Neo4j/Postgres access. No caching. No business logic.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional


class BloodHoundClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session_token: Optional[str] = None

    def login(self) -> str:
        body = {
            "login_method": "secret",
            "username": self.username,
            "secret": self.password,
        }
        data = self._request("/api/v2/login", method="POST", body=body)
        token = data["data"]["session_token"]
        self.session_token = token
        return token

    def get_identity(self, query: str, node_type: str = "user") -> Dict:
        """Resolve an identity by search query (UPN, display name, object id)."""
        params = urllib.parse.urlencode({"query": query, "type": node_type})
        data = self._request(f"/api/v2/graph-search?{params}", method="GET")
        items = data.get("data", [])
        if not items:
            raise LookupError(f"No identity found for query: {query}")
        return items[0]

    def get_reachable_assets(self, object_id: str, limit: int = 100) -> List[Dict]:
        """Use BloodHound cypher API to fetch directly reachable assets.

        This uses the official API endpoint `/api/v2/graphs/cypher` (still a
        BloodHound-controlled call) to avoid direct Neo4j connections.
        """
        cypher = (
            "MATCH (n {objectid: $oid})-[r]->(m) "
            "RETURN m.objectid AS id, labels(m)[0] AS kind, m.name AS name, type(r) AS via "
            "LIMIT $limit"
        )
        payload = {"query": cypher, "parameters": {"oid": object_id, "limit": limit}}
        data = self._request("/api/v2/graphs/cypher", method="POST", body=payload)
        assets = []
        for row in data.get("data", []):
            assets.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "kind": (row.get("kind") or "asset").lower(),
                    "via": (row.get("via") or "edge").lower(),
                    "confidence": "graph",
                }
            )
        return assets

    def get_critical_path(self, start_id: str, target_id: str) -> Optional[Dict]:
        """Fetch a shortest path between two nodes using the BloodHound pathfinding API."""
        body = {"start_node": start_id, "end_node": target_id}
        data = self._request("/api/v2/pathfinding", method="GET", body=body)
        path = data.get("data")
        if not path:
            return None
        hops = []
        for hop in path.get("path", []):
            hops.append(
                {
                    "id": hop.get("objectid") or hop.get("id"),
                    "type": (hop.get("type") or "node").lower(),
                    "edge": hop.get("relationship") or hop.get("edge"),
                }
            )
        return {
            "from": start_id,
            "to": target_id,
            "length": len(hops),
            "hops": hops,
        }

    def build_identity_report(self, identity_ref: Dict, critical_target_id: Optional[str] = None) -> Dict:
        """High-level helper that assembles the contract-compliant payload."""
        if not self.session_token:
            self.login()
        resolved = self.get_identity(identity_ref.get("id") or identity_ref.get("upn") or "")
        oid = resolved.get("objectid") or resolved.get("id")
        reachable = self.get_reachable_assets(oid)
        critical = []
        if critical_target_id:
            path = self.get_critical_path(oid, critical_target_id)
            if path:
                critical.append(path)
        privileges = [
            {
                "target_id": asset.get("id"),
                "privilege": "admin" if "admin" in (asset.get("name") or "").lower() else "read",
                "evidence": "graph_edge",
                "source": "bloodhound",
            }
            for asset in reachable
        ]
        return {
            "identity": {
                "id": oid,
                "upn": resolved.get("properties", {}).get("userprincipalname") or resolved.get("name"),
                "display_name": resolved.get("name"),
                "type": (resolved.get("type") or "identity").lower(),
            },
            "reachable_assets": reachable,
            "critical_paths": critical,
            "privilege_classification": privileges,
        }

    def _request(self, path: str, method: str = "GET", body: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        data_bytes = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                return json.loads(resp_body) if resp_body else {}
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"BloodHound API error {exc.code} for {path}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"BloodHound API unreachable for {path}: {exc.reason}") from exc
