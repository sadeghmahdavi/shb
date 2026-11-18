import enum
import socket
import struct
from pathlib import Path
from typing import BinaryIO

import dpkt
from pcap.errors import PcapParseError
from pcap.models import FlowKey, FlowRecord, ParsedCapture

from utils.logging_setup import get_logger

logger = get_logger(__name__)


class DatalinkType(enum.IntEnum):
    """DLT (datalink type) stored in the libpcap file header: it says what precedes the IP packet in each record.

    ETHERNET (1): a 14-byte Ethernet header precedes the IP packet — captures made on a physical network card.
    RAW_IP (101): the IP packet starts at byte zero — captures made on tun/VPN interfaces. The pcap file
        format always stores 101 for raw IP; 12/14 are BSD-era values that never appear in capture files.
    LINUX_SLL (113): a 16-byte Linux cooked header precedes the IP packet — captures made with `tcpdump -i any`.
    """

    ETHERNET = 1
    RAW_IP = 101
    LINUX_SLL = 113


class _FlowAccumulator:
    """Mutable per-flow bookkeeping the parser folds into one FlowRecord: byte counters plus the TCP-only
    retransmission, zero-window and handshake state."""

    def __init__(self, flow_key: FlowKey) -> None:
        """Start with empty counters, no recorded handshake and no sent byte ranges."""
        self.flow_key = flow_key
        self.total_frame_bytes = 0
        self.payload_bytes = 0
        self.retransmission_count = 0
        self.zero_window_event_count = 0
        self.reset_count = 0
        self.handshake_rtt: float | None = None
        self._syn_timestamp: float | None = None
        self._sent_ranges: dict[str, list[tuple[int, int]]] = {}

    def add_tcp_segment(self, timestamp: float, segment: dpkt.tcp.TCP, frame_length: int, source_ip: str) -> None:
        # TODO
        pass

    def add_udp_datagram(self, datagram: dpkt.udp.UDP, frame_length: int) -> None:
        # TODO
        pass

    def record(self) -> FlowRecord:
        """Freeze the bookkeeping into the flow's immutable record."""
        return FlowRecord(
            flow_key=self.flow_key,
            total_frame_bytes=self.total_frame_bytes,
            payload_bytes=self.payload_bytes,
            retransmission_count=self.retransmission_count,
            zero_window_event_count=self.zero_window_event_count,
            reset_count=self.reset_count,
            handshake_rtt=self.handshake_rtt,
        )




class PcapParser:
    """Parses pcap/pcapng captures into per-flow records using dpkt (no external tools)."""

    DISSECTION_ERRORS: tuple[type[Exception], ...] = (dpkt.UnpackError, struct.error, IndexError)

    def parse(self, pcap_path: Path) -> ParsedCapture:
        """Dissect a capture into one record per TCP/UDP flow, plus the non-flow byte total.

        Flows are keyed by their canonical five-tuple, so both directions of a flow and both
        protocols on the same four-tuple are handled. Non-flow traffic (ARP, ICMP, ...) only
        counts its frame bytes. Individually malformed packets are skipped and counted; an
        unreadable file raises PcapParseError.
        """
        try:
            capture = self._parse(pcap_path)
        except OSError as error:
            raise PcapParseError(f"cannot read {pcap_path}: {error}") from error
        if capture.malformed_packet_count:
            logger.warning("%s: skipped %d malformed packet(s).", pcap_path.name, capture.malformed_packet_count)
        return capture

    def _parse(self, pcap_path: Path) -> ParsedCapture:
        # TODO
        pass
