cat << 'EOF' > ~/shb/services/network_analyzer/src/pcap/parser.py
import enum
import socket
import struct
from bisect import bisect_left
from pathlib import Path
from typing import BinaryIO

import dpkt
from pcap.errors import PcapParseError
from pcap.models import FlowKey, FlowRecord, ParsedCapture

from utils.logging_setup import get_logger

logger = get_logger(__name__)

PCAPNG_MAGIC = b"\x0a\x0d\x0d\x0a"


class DatalinkType(enum.IntEnum):
    """DLT (datalink type) stored in the libpcap file header: it says what precedes the IP packet in each record."""

    ETHERNET = 1
    RAW_IP = 101
    LINUX_SLL = 113


class _FlowAccumulator:
    """Mutable per-flow bookkeeping the parser folds into one FlowRecord."""

    def __init__(self, flow_key: FlowKey) -> None:
        self.flow_key = flow_key
        self.total_frame_bytes = 0
        self.payload_bytes = 0
        self.retransmission_count = 0
        self.zero_window_event_count = 0
        self.reset_count = 0
        self.handshake_rtt: float | None = None
        self._syn_timestamp: float | None = None
        self._sent_starts: dict[str, list[int]] = {}
        self._sent_ends: dict[str, list[int]] = {}

    def add_tcp_segment(self, timestamp: float, segment: dpkt.tcp.TCP, frame_length: int, source_ip: str) -> None:
        self.total_frame_bytes += frame_length
        payload_length = len(segment.data)
        self.payload_bytes += payload_length

        flags = segment.flags
        is_syn = bool(flags & dpkt.tcp.TH_SYN)
        is_ack = bool(flags & dpkt.tcp.TH_ACK)
        is_fin = bool(flags & dpkt.tcp.TH_FIN)
        is_rst = bool(flags & dpkt.tcp.TH_RST)

        if is_syn and not is_ack:
            if self._syn_timestamp is None:
                self._syn_timestamp = timestamp
        elif is_syn and is_ack:
            if self._syn_timestamp is not None and self.handshake_rtt is None:
                rtt = timestamp - self._syn_timestamp
                if rtt >= 0:
                    self.handshake_rtt = rtt

        if is_rst:
            self.reset_count += 1

        if segment.win == 0 and not is_rst:
            self.zero_window_event_count += 1

        seq_length = payload_length + (1 if is_syn else 0) + (1 if is_fin else 0)
        if seq_length > 0:
            seq_start = segment.seq
            seq_end = seq_start + seq_length
            starts = self._sent_starts.setdefault(source_ip, [])
            ends = self._sent_ends.setdefault(source_ip, [])

            idx = bisect_left(starts, seq_start)
            if (idx > 0 and ends[idx - 1] > seq_start) or (idx < len(starts) and starts[idx] < seq_end):
                self.retransmission_count += 1

            new_start, new_end = seq_start, seq_end
            left = idx
            if left > 0 and ends[left - 1] >= new_start:
                left -= 1
                new_start = min(new_start, starts[left])
                new_end = max(new_end, ends[left])

            right = idx
            while right < len(starts) and starts[right] <= new_end:
                new_end = max(new_end, ends[right])
                right += 1

            starts[left:right] = [new_start]
            ends[left:right] = [new_end]

    def add_udp_datagram(self, datagram: dpkt.udp.UDP, frame_length: int) -> None:
        self.total_frame_bytes += frame_length
        self.payload_bytes += len(datagram.data)

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
    FRAMING_ERRORS: tuple[type[Exception], ...] = (ValueError, EOFError, dpkt.UnpackError, struct.error)

    def parse(self, pcap_path: Path) -> ParsedCapture:
        try:
            capture = self._parse(pcap_path)
        except OSError as error:
            raise PcapParseError(f"cannot read {pcap_path}: {error}") from error
        if capture.malformed_packet_count:
            logger.warning("%s: skipped %d malformed packet(s).", pcap_path.name, capture.malformed_packet_count)
        return capture

    def _open_reader(self, handle: BinaryIO) -> dpkt.pcap.Reader | dpkt.pcapng.Reader:
        magic = handle.read(4)
        handle.seek(0)
        if magic == PCAPNG_MAGIC:
            return dpkt.pcapng.Reader(handle)
        return dpkt.pcap.Reader(handle)

    def _extract_ip_packet(
        self, raw_frame: bytes, datalink: int
    ) -> dpkt.ip.IP | dpkt.ip6.IP6 | None:
        if datalink == DatalinkType.ETHERNET:
            eth = dpkt.ethernet.Ethernet(raw_frame)
            return eth.data if isinstance(eth.data, (dpkt.ip.IP, dpkt.ip6.IP6)) else None

        if datalink == DatalinkType.LINUX_SLL:
            sll = dpkt.sll.SLL(raw_frame)
            return sll.data if isinstance(sll.data, (dpkt.ip.IP, dpkt.ip6.IP6)) else None

        if datalink == DatalinkType.RAW_IP:
            if not raw_frame:
                raise dpkt.UnpackError("empty raw IP frame")
            ip_version = raw_frame[0] >> 4
            if ip_version == 4:
                return dpkt.ip.IP(raw_frame)
            if ip_version == 6:
                return dpkt.ip6.IP6(raw_frame)
            raise dpkt.UnpackError(f"unknown IP version: {ip_version}")

        raise PcapParseError(f"unsupported datalink type: {datalink}")

    def _format_ip(self, ip_packet: dpkt.ip.IP | dpkt.ip6.IP6) -> tuple[str, str]:
        if isinstance(ip_packet, dpkt.ip.IP):
            return (
                socket.inet_ntop(socket.AF_INET, ip_packet.src),
                socket.inet_ntop(socket.AF_INET, ip_packet.dst),
            )
        return (
            socket.inet_ntop(socket.AF_INET6, ip_packet.src),
            socket.inet_ntop(socket.AF_INET6, ip_packet.dst),
        )

    def _parse(self, pcap_path: Path) -> ParsedCapture:
        accumulators: dict[FlowKey, _FlowAccumulator] = {}
        other_frame_bytes = 0
        malformed_packet_count = 0

        try:
            with pcap_path.open("rb") as handle:
                reader = self._open_reader(handle)
                for timestamp, raw_frame in reader:
                    frame_length = len(raw_frame)
                    datalink = reader.datalink()
                    try:
                        ip_packet = self._extract_ip_packet(raw_frame, datalink)
                        if ip_packet is None:
                            other_frame_bytes += frame_length
                            continue

                        source_ip, destination_ip = self._format_ip(ip_packet)
                        transport = ip_packet.data

                        if ip_packet.p == dpkt.ip.IP_PROTO_TCP:
                            segment = transport if isinstance(transport, dpkt.tcp.TCP) else dpkt.tcp.TCP(transport)
                            flow_key = FlowKey.from_packet(
                                "TCP", source_ip, segment.sport, destination_ip, segment.dport
                            )
                            acc = accumulators.setdefault(flow_key, _FlowAccumulator(flow_key))
                            acc.add_tcp_segment(timestamp, segment, frame_length, source_ip)
                        elif ip_packet.p == dpkt.ip.IP_PROTO_UDP:
                            datagram = transport if isinstance(transport, dpkt.udp.UDP) else dpkt.udp.UDP(transport)
                            flow_key = FlowKey.from_packet(
                                "UDP", source_ip, datagram.sport, destination_ip, datagram.dport
                            )
                            acc = accumulators.setdefault(flow_key, _FlowAccumulator(flow_key))
                            acc.add_udp_datagram(datagram, frame_length)
                        else:
                            other_frame_bytes += frame_length
                    except self.DISSECTION_ERRORS:
                        malformed_packet_count += 1
                        continue
        except PcapParseError:
            raise
        except self.FRAMING_ERRORS as error:
            raise PcapParseError(f"corrupt capture file {pcap_path}: {error}") from error

        flows = tuple(acc.record() for acc in accumulators.values())
        return ParsedCapture(
            flows=flows,
            other_frame_bytes=other_frame_bytes,
            malformed_packet_count=malformed_packet_count,
        )
EOF