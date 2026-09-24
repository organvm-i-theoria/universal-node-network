"""Discovery module for automatic node detection and registration.

Provides service discovery mechanisms that allow new nodes to announce
themselves and existing nodes to find peers by capability or organ affiliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .node import Node, NodeCapability, NodeStatus


@dataclass
class DiscoveryAnnouncement:
    """A broadcast announcement from a node seeking to join the network."""

    node_id: str
    organ: str
    endpoint: str
    capabilities: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl_seconds: int = 300

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if this announcement has exceeded its time-to-live."""
        current_time = (now if now is not None else datetime.now(UTC)).astimezone(UTC)
        announcement_time = self.timestamp.astimezone(UTC)
        return current_time > announcement_time + timedelta(seconds=self.ttl_seconds)


class DiscoveryService:
    """Manages node discovery, announcement processing, and peer resolution.

    Nodes announce themselves through this service, which validates
    announcements and facilitates peer-to-peer discovery.
    """

    def __init__(self) -> None:
        self._announcements: dict[str, DiscoveryAnnouncement] = {}
        self._known_nodes: dict[str, Node] = {}

    def announce(self, announcement: DiscoveryAnnouncement) -> Node:
        """Process a node announcement and register the node.

        Args:
            announcement: The discovery announcement to process.

        Returns:
            The registered (or updated) Node object.
        """
        self._announcements[announcement.node_id] = announcement

        if announcement.node_id in self._known_nodes:
            node = self._known_nodes[announcement.node_id]
            node.heartbeat()
            return node

        node = Node(
            node_id=announcement.node_id,
            organ=announcement.organ,
            endpoint=announcement.endpoint,
        )
        for cap_name in announcement.capabilities:
            node.register_capability(NodeCapability(name=cap_name, version="1.0"))
        node.heartbeat()
        self._known_nodes[announcement.node_id] = node
        return node

    def find_peers(self, organ: str | None = None, capability: str | None = None) -> list[Node]:
        """Find nodes matching organ and/or capability criteria.

        Args:
            organ: Filter by organ affiliation (optional).
            capability: Filter by capability name (optional).

        Returns:
            List of matching online nodes.
        """
        results = list(self._known_nodes.values())

        if organ is not None:
            results = [n for n in results if n.organ == organ]
        if capability is not None:
            results = [n for n in results if n.has_capability(capability)]

        return [n for n in results if n.status == NodeStatus.ONLINE]

    def prune_expired(self) -> int:
        """Remove expired announcements and mark their nodes offline.

        Returns:
            Number of nodes marked offline.
        """
        pruned = 0
        expired_ids = [
            aid for aid, ann in self._announcements.items() if ann.is_expired()
        ]
        for node_id in expired_ids:
            del self._announcements[node_id]
            if node_id in self._known_nodes:
                self._known_nodes[node_id].go_offline()
                pruned += 1
        return pruned

    @property
    def active_count(self) -> int:
        """Number of currently online nodes."""
        return sum(1 for n in self._known_nodes.values() if n.status == NodeStatus.ONLINE)


class LensDiscovery:
    """Discovers appropriate hierarchy lenses for a given task.

    Wraps the assembly protocol from assembly.py and exposes it
    through the discovery service pattern for consistency with
    the existing Node/Network/Discovery architecture.
    """

    def discover_lenses(
        self,
        task_description: str,
        max_lenses: int = 3,
        exclude: list[str] | None = None,
    ) -> list[str]:
        """Find the best lenses for a task description.

        Args:
            task_description: Natural language description of the task.
            max_lenses: Maximum lenses to return (hard cap: 3).
            exclude: Lens IDs to skip.

        Returns:
            List of lens_id strings for the selected lenses.
        """
        from .assembly import assemble

        result = assemble(task_description, max_lenses=max_lenses, exclude=exclude)
        return [lens.lens_id for lens in result.summoned_lenses]

    def discover_by_category(self, category_name: str) -> list[str]:
        """Find lenses belonging to a specific category.

        Args:
            category_name: One of: tooling, structure, authority, foundation, generative.

        Returns:
            List of lens_id strings in that category.
        """
        from .hierarchy import LENSES_BY_CATEGORY, LensCategory

        try:
            cat = LensCategory(category_name)
        except ValueError:
            return []
        return [h.lens_id for h in LENSES_BY_CATEGORY.get(cat, [])]

    def discover_by_stratum(self, stratum_value: str) -> list[str]:
        """Find lenses belonging to a specific stratum.

        Args:
            stratum_value: The stratum path (e.g., "/boot/").

        Returns:
            List of lens_id strings in that stratum.
        """
        from .hierarchy import LENSES_BY_STRATUM, Stratum

        for s in Stratum:
            if s.value == stratum_value:
                return [h.lens_id for h in LENSES_BY_STRATUM.get(s, [])]
        return []