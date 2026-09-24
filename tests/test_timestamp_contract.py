"""Regression tests for the timestamp contract in discovery and node modules."""

from datetime import UTC, datetime, timedelta, timezone

from src.discovery import DiscoveryAnnouncement
from src.node import Node, NodeStatus


def test_ttl_boundary_with_controlled_clock():
    """Verify is_expired behavior before, at, and after the TTL boundary using a controlled clock."""
    base_time = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    ttl = 300
    announcement = DiscoveryAnnouncement(
        node_id="utc-node",
        organ="IV",
        endpoint="http://localhost",
        capabilities=[],
        timestamp=base_time,
        ttl_seconds=ttl,
    )

    # Before TTL boundary (299s elapsed)
    now_before = base_time + timedelta(seconds=299)
    assert not announcement.is_expired(now=now_before)

    # At TTL boundary (exactly 300s elapsed - boundary semantics preserved)
    now_at = base_time + timedelta(seconds=300)
    assert not announcement.is_expired(now=now_at)

    # After TTL boundary (301s elapsed)
    now_after = base_time + timedelta(seconds=301)
    assert announcement.is_expired(now=now_after)


def test_non_utc_offset_timestamp():
    """Verify that equivalent non-UTC offset timestamps compare safely without error."""
    # 14:00 UTC+2 is equivalent to 12:00 UTC
    tz_plus_two = timezone(timedelta(hours=2))
    base_time_utc = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    base_time_non_utc = datetime(2026, 4, 15, 14, 0, 0, tzinfo=tz_plus_two)

    announcement = DiscoveryAnnouncement(
        node_id="non-utc-node",
        organ="IV",
        endpoint="http://localhost",
        capabilities=[],
        timestamp=base_time_non_utc,
        ttl_seconds=300,
    )

    now_before = base_time_utc + timedelta(seconds=100)
    now_after = base_time_utc + timedelta(seconds=350)

    assert not announcement.is_expired(now=now_before)
    assert announcement.is_expired(now=now_after)


def test_legacy_naive_timestamp():
    """Verify that legacy timezone-naive timestamps are handled compatibly without TypeError."""
    naive_base = datetime.now()
    announcement = DiscoveryAnnouncement(
        node_id="legacy-naive-node",
        organ="IV",
        endpoint="http://localhost",
        capabilities=[],
        timestamp=naive_base,
        ttl_seconds=300,
    )

    # Checking expiration against current time (aware UTC) must not raise TypeError
    assert not announcement.is_expired()

    # Expired naive timestamp
    announcement.timestamp = naive_base - timedelta(seconds=400)
    assert announcement.is_expired()


def test_default_announcement_timestamp_is_aware_utc():
    """Verify that new announcements generate timezone-aware UTC timestamps by default."""
    announcement = DiscoveryAnnouncement(
        node_id="default-tz-node",
        organ="IV",
        endpoint="http://localhost",
        capabilities=[],
    )

    assert announcement.timestamp.tzinfo is not None
    assert announcement.timestamp.tzinfo == UTC


def test_node_heartbeat_aware_utc_and_serialization():
    """Verify Node.heartbeat generates aware UTC timestamp and serializes correctly."""
    node = Node(node_id="heartbeat-node", organ="IV", endpoint="http://localhost")
    assert node.last_heartbeat is None

    node.heartbeat()

    assert node.status == NodeStatus.ONLINE
    assert node.last_heartbeat is not None
    assert node.last_heartbeat.tzinfo is not None
    assert node.last_heartbeat.tzinfo == UTC

    entry = node.to_registry_entry()
    assert entry["last_heartbeat"] is not None

    # Verify that the ISO string can be parsed back as an aware datetime
    parsed_dt = datetime.fromisoformat(entry["last_heartbeat"])
    assert parsed_dt.tzinfo is not None
