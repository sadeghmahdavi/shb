import dpkt
import pytest
from pcap.analyzer import PcapAnalyzer
from pcap.parser import DatalinkType

from tests.builders import (
    CLIENT_IP,
    CLIENT_PORT,
    SERVER_IP,
    SERVER_PORT,
    arp_packet,
    handshake_packets,
    malformed_packet_bytes,
    pcapng_enhanced_packet_block,
    pcapng_interface_description_block,
    pcapng_section_header_block,
    tcp_packet,
    udp_packet,
    write_pcap,
)


def test_counts_retransmissions_zero_windows_and_resets(tmp_path):
    pcap_path = tmp_path / "anomalies.pcap"
    packets = handshake_packets() + [
        # Retransmission of sequence 101..201
        (
            1.2,
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
        ),
        # ZeroWindow notification from receiver
        (
            1.3,
            tcp_packet(
                SERVER_IP,
                CLIENT_IP,
                SERVER_PORT,
                CLIENT_PORT,
                flags=dpkt.tcp.TH_ACK,
                sequence_number=301,
                acknowledgment_number=201,
                window_size=0,
            ),
        ),
        # TCP RST drop
        (
            1.4,
            tcp_packet(
                SERVER_IP,
                CLIENT_IP,
                SERVER_PORT,
                CLIENT_PORT,
                flags=dpkt.tcp.TH_RST,
                sequence_number=301,
            ),
        ),
    ]
    write_pcap(pcap_path, packets)

    metrics = PcapAnalyzer().analyze(pcap_path)

    assert metrics.handshake_rtt_avg == pytest.approx(0.05)
    assert metrics.retransmission_count == 1
    assert metrics.zero_window_event_count == 1
    assert metrics.tcp_reset_drops == 1
    assert metrics.total_payload_bytes == 200
    assert metrics.dominant_server_port == 443


def test_handles_udp_non_ip_and_malformed_packets(tmp_path):
    pcap_path = tmp_path / "mixed.pcap"
    udp_frame = udp_packet(CLIENT_IP, "8.8.8.8", 50000, 53, payload=b"dns-query")
    arp_frame = arp_packet()
    bad_frame = malformed_packet_bytes()

    write_pcap(pcap_path, [(1.0, udp_frame), (1.1, arp_frame), (1.2, bad_frame)])

    metrics = PcapAnalyzer().analyze(pcap_path)

    assert metrics.handshake_rtt_avg is None
    assert metrics.total_payload_bytes == len(b"dns-query")
    assert metrics.total_transferred_bytes == len(udp_frame) + len(arp_frame)
    assert metrics.dominant_server_port == 53


def test_parses_pcapng_with_raw_ip_datalink_like_pcapdroid(tmp_path):
    pcapng_path = tmp_path / "android_vpn.pcapng"
    eth_frame = tcp_packet(
        CLIENT_IP,
        SERVER_IP,
        CLIENT_PORT,
        SERVER_PORT,
        flags=dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK,
        sequence_number=1,
        acknowledgment_number=1,
        payload=b"hello",
    )
    raw_ip_packet = eth_frame[14:]  # Strip Ethernet header for DLT_RAW (101)

    content = (
        pcapng_section_header_block()
        + pcapng_interface_description_block(DatalinkType.RAW_IP)
        + pcapng_enhanced_packet_block(2.0, raw_ip_packet)
    )
    pcapng_path.write_bytes(content)

    metrics = PcapAnalyzer().analyze(pcapng_path)

    assert metrics.total_transferred_bytes == len(raw_ip_packet)
    assert metrics.total_payload_bytes == 5
    assert metrics.dominant_server_port == 443