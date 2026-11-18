from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class Endpoint:
    """One side of a flow: the IP address and port a packet came from or went to."""

    ip: str
    port: int


@dataclass(frozen=True)
class FlowKey:
    """Canonical five-tuple of one bidirectional flow: the protocol plus both endpoints in sorted order.

    The endpoint pair is sorted, so a packet produces the same key no matter which direction it
    travels in; the protocol is part of the key, so TCP and UDP traffic on the same four-tuple
    are distinct flows.
    """

    protocol: str
    first_endpoint: Endpoint
    second_endpoint: Endpoint

    @classmethod
    def from_packet(
        cls, protocol: str, source_ip: str, source_port: int, destination_ip: str, destination_port: int
    ) -> "FlowKey":
        """Build the canonical key of one packet's five-tuple, independent of its direction."""
        source = Endpoint(source_ip, source_port)
        destination = Endpoint(destination_ip, destination_port)
        first_endpoint, second_endpoint = sorted((source, destination))
        return cls(protocol=protocol, first_endpoint=first_endpoint, second_endpoint=second_endpoint)


@dataclass(frozen=True)
class FlowRecord:
    """One bidirectional flow of a capture, aggregated over all of its packets."""

    flow_key: FlowKey
    total_frame_bytes: int
    payload_bytes: int = 0
    retransmission_count: int = 0
    zero_window_event_count: int = 0
    reset_count: int = 0
    handshake_rtt: float | None = None


@dataclass(frozen=True)
class ParsedCapture:
    """Everything the parser extracted from one capture file."""

    flows: tuple[FlowRecord, ...]
    other_frame_bytes: int
    malformed_packet_count: int


@dataclass(frozen=True)
class DiscoveredPcap:
    """One capture file on disk: the app folder it sits in and its content hash."""

    app_name: str
    scenario: str
    pcap_path: Path
    pcap_hash: str
