from __future__ import annotations

from incident_coordinator import IncidentCoordinator


def main() -> None:
    coordinator = IncidentCoordinator()
    incident_id = coordinator.create_incident(
        identity_ref="totally-fake-identity-123",
        assumption="Assume this identity is compromised.",
        source="manual",
    )
    print(coordinator.get_incident(incident_id))


if __name__ == "__main__":
    main()
