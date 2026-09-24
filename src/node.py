"""Node module for representing and managing network participants.

Each node in the universal network represents an organ, repository,
or service endpoint that can send and receive messages through
the orchestration layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class NodeStatus(Enum):
    """Operational states for a network node."""

    INITIALIZING = "initializing"
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    DECOMMISSIONED = "decommissioned"


@dataclass
class NodeCapability:
    """A declared capability that a node can provide."""

    name: str
    version: str
    protocol: str = "http"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    """A participant in the universal node network.

    Nodes represent organs, services, or endpoints that participate
    in the orchestration mesh. Each node declares its capabilities
    and maintains heartbeat state.
    """

    node_id: str
    organ: str
    endpoint: str
    capabilities: list[NodeCapability] = field(default_factory=list)
    status: NodeStatus = NodeStatus.INITIALIZING
    last_heartbeat: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def register_capability(self, capability: NodeCapability) -> None:
        """Declare a new capability for this node.

        Args:
            capability: The capability to register.

        Raises:
            ValueError: If a capability with the same name already exists.
        """
        if any(c.name == capability.name for c in self.capabilities):
            raise ValueError(f"Capability '{capability.name}' already registered on node '{self.node_id}'")
        self.capabilities.append(capability)

    def heartbeat(self) -> None:
        """Update the last heartbeat timestamp and ensure ONLINE status."""
        self.last_heartbeat = datetime.now(UTC)
        if self.status == NodeStatus.INITIALIZING:
            self.status = NodeStatus.ONLINE

    def go_offline(self) -> None:
        """Transition the node to OFFLINE state."""
        self.status = NodeStatus.OFFLINE

    def has_capability(self, capability_name: str) -> bool:
        """Check if this node provides a specific capability."""
        return any(c.name == capability_name for c in self.capabilities)

    def to_registry_entry(self) -> dict[str, Any]:
        """Export node info as a registry-compatible dictionary."""
        return {
            "node_id": self.node_id,
            "organ": self.organ,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "capabilities": [c.name for c in self.capabilities],
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }
