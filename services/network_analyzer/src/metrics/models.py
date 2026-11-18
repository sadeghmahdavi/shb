from dataclasses import dataclass, replace
from typing import Any

from pcap.models import DiscoveredPcap


@dataclass(frozen=True)
class PcapMetrics:
    """Aggregate metrics for one capture; identity fields default to None and are bound in by with_capture."""

    handshake_rtt_avg: float | None
    retransmission_count: int
    zero_window_event_count: int
    tcp_reset_drops: int
    total_transferred_bytes: int
    total_payload_bytes: int
    overhead_ratio: float | None
    dominant_server_port: int | None
    scenario: str | None = None
    pcap_filename: str | None = None
    pcap_hash: str | None = None

    def with_capture(self, capture: DiscoveredPcap) -> "PcapMetrics":
        """Return a copy of these metrics bound to one analyzed capture's identity."""
        return replace(
            self,
            scenario=capture.scenario,
            pcap_filename=capture.pcap_path.name,
            pcap_hash=capture.pcap_hash,
        )

    def to_record(self) -> dict[str, Any]:
        """Return the dict shape consumed by utils.db.insert_network_metrics."""
        return {
            "scenario": self.scenario,
            "pcap_filename": self.pcap_filename,
            "pcap_hash": self.pcap_hash,
            "handshake_rtt_avg": self.handshake_rtt_avg,
            "retransmission_count": self.retransmission_count,
            "zero_window_event_count": self.zero_window_event_count,
            "tcp_reset_drops": self.tcp_reset_drops,
            "total_transferred_bytes": self.total_transferred_bytes,
            "total_payload_bytes": self.total_payload_bytes,
            "overhead_ratio": self.overhead_ratio,
            "dominant_server_port": self.dominant_server_port,
        }
