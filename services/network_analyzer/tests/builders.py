import socket
import struct
from pathlib import Path

import dpkt
from metrics.models import PcapMetrics
from pcap.models import DiscoveredPcap

DEVICE_MAC_ADDRESS = b"\x02" * 6
BROADCAST_MAC_ADDRESS = b"\xff" * 6

CLIENT_IP = "192.168.10.24"
SERVER_IP = "142.250.185.174"
CLIENT_PORT = 54321
SERVER_PORT = 443


def sample_metrics(pcap_hash: str) -> PcapMetrics:
    """Build one aggregate-metrics object bound to a fixed synthetic capture's identity."""
    return PcapMetrics(
        handshake_rtt_avg=0.05,
        retransmission_count=1,
        zero_window_event_count=2,
        tcp_reset_drops=0,
        total_transferred_bytes=262,
        total_payload_bytes=100,
        overhead_ratio=0.618,
        dominant_server_port=443,
    ).with_capture(
        DiscoveredPcap(app_name="Baham", scenario="upload", pcap_path=Path("capture.pcap"), pcap_hash=pcap_hash)
    )


def tcp_packet(
    source_ip: str,
    destination_ip: str,
    source_port: int,
    destination_port: int,
    *,
    sequence_number: int = 0,
    acknowledgment_number: int = 0,
    flags: int = 0,
    window_size: int = 65535,
    payload: bytes = b"",
) -> bytes:
    """Build one Ethernet + IPv4 + TCP frame."""
    tcp = dpkt.tcp.TCP(
        sport=source_port,
        dport=destination_port,
        seq=sequence_number,
        ack=acknowledgment_number,
        flags=flags,
        win=window_size,
        data=payload,
    )
    ip = dpkt.ip.IP(
        src=socket.inet_aton(source_ip),
        dst=socket.inet_aton(destination_ip),
        p=dpkt.ip.IP_PROTO_TCP,
        ttl=64,
        data=tcp,
    )
    ip.len = 20 + len(bytes(tcp))
    return bytes(
        dpkt.ethernet.Ethernet(src=DEVICE_MAC_ADDRESS, dst=DEVICE_MAC_ADDRESS, type=dpkt.ethernet.ETH_TYPE_IP, data=ip)
    )


def udp_packet(
    source_ip: str, destination_ip: str, source_port: int, destination_port: int, payload: bytes = b""
) -> bytes:
    """Build one Ethernet + IPv4 + UDP frame."""
    udp = dpkt.udp.UDP(sport=source_port, dport=destination_port, data=payload)
    udp.ulen = 8 + len(payload)
    ip = dpkt.ip.IP(
        src=socket.inet_aton(source_ip),
        dst=socket.inet_aton(destination_ip),
        p=dpkt.ip.IP_PROTO_UDP,
        ttl=64,
        data=udp,
    )
    ip.len = 20 + len(bytes(udp))
    return bytes(
        dpkt.ethernet.Ethernet(src=DEVICE_MAC_ADDRESS, dst=DEVICE_MAC_ADDRESS, type=dpkt.ethernet.ETH_TYPE_IP, data=ip)
    )


def arp_packet() -> bytes:
    """Build one Ethernet ARP frame (non-IP traffic)."""
    arp = dpkt.arp.ARP()
    return bytes(
        dpkt.ethernet.Ethernet(
            src=DEVICE_MAC_ADDRESS, dst=BROADCAST_MAC_ADDRESS, type=dpkt.ethernet.ETH_TYPE_ARP, data=arp
        )
    )


def malformed_packet_bytes() -> bytes:
    """Build a 3-byte frame too short to dissect; dpkt raises on it, so the parser counts it as malformed."""
    return b"\x00\x01\x02"


def write_pcap(path: Path, packets: list[tuple[float, bytes]], linktype: int = dpkt.pcap.DLT_EN10MB) -> None:
    """Write packets into a classic pcap file with the given linktype."""
    with path.open("wb") as handle:
        writer = dpkt.pcap.Writer(handle, linktype=linktype)
        for timestamp, packet_bytes in packets:
            writer.writepkt(packet_bytes, ts=timestamp)


def truncated_record_pcap_bytes() -> bytes:
    """Build a classic pcap file (little-endian magic, Ethernet linktype) whose first record header is cut short."""
    return b"\xd4\xc3\xb2\xa1" + struct.pack("<HHiIII", 2, 4, 0, 0, 65535, 1) + b"\x00\x00\x00"


def pcapng_block(block_type: int, body: bytes) -> bytes:
    """Build one generic pcapng block: type + total length + body + trailing total length."""
    total_length = 12 + len(body)
    return struct.pack("<II", block_type, total_length) + body + struct.pack("<I", total_length)


def pcapng_section_header_block() -> bytes:
    """Build a pcapng Section Header Block (little-endian byte-order magic)."""
    return pcapng_block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))


def pcapng_interface_description_block(linktype: int) -> bytes:
    """Build a pcapng Interface Description Block for the given linktype."""
    return pcapng_block(1, struct.pack("<HHI", linktype, 0, 0x40000))


def pcapng_enhanced_packet_block(timestamp_seconds: float, packet: bytes) -> bytes:
    """Build a pcapng Enhanced Packet Block; timestamps use the default if_tsresol=6 (microseconds)."""
    timestamp_raw = int(timestamp_seconds * 1e6)
    padded = packet + b"\x00" * (-len(packet) % 4)
    body = struct.pack("<IIIII", 0, timestamp_raw >> 32, timestamp_raw & 0xFFFFFFFF, len(packet), len(packet)) + padded
    return pcapng_block(6, body)


def handshake_packets() -> list[tuple[float, bytes]]:
    """Build a SYN, SYN-ACK and data exchange on one stream (rtt 0.05s, 100-byte payload)."""
    syn = (
        1.0,
        tcp_packet(CLIENT_IP, SERVER_IP, CLIENT_PORT, SERVER_PORT, flags=dpkt.tcp.TH_SYN, sequence_number=100),
    )
    syn_ack = (
        1.05,
        tcp_packet(
            SERVER_IP,
            CLIENT_IP,
            SERVER_PORT,
            CLIENT_PORT,
            flags=dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK,
            sequence_number=300,
            acknowledgment_number=101,
        ),
    )
    data = (
        1.1,
        tcp_packet(
            CLIENT_IP,
            SERVER_IP,
            CLIENT_PORT,
            SERVER_PORT,
            flags=dpkt.tcp.TH_ACK,
            sequence_number=101,
            acknowledgment_number=301,
            payload=b"x" * 100,
        ),
    )
    return [syn, syn_ack, data]
