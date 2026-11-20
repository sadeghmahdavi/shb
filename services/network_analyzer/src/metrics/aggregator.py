from configs import WELL_KNOWN_PORTS
from metrics.models import PcapMetrics
from pcap.models import FlowKey, FlowRecord, ParsedCapture


class PcapMetricsAggregator:
    """Reduces a parsed capture's flows into the aggregate metrics stored in the network_metrics table."""

    def aggregate(self, capture: ParsedCapture) -> PcapMetrics:
        rtts = [flow.handshake_rtt for flow in capture.flows if flow.handshake_rtt is not None]
        handshake_rtt_avg = (sum(rtts) / len(rtts)) if rtts else None

        retransmission_count = sum(flow.retransmission_count for flow in capture.flows)
        zero_window_event_count = sum(flow.zero_window_event_count for flow in capture.flows)
        tcp_reset_drops = sum(flow.reset_count for flow in capture.flows)

        flow_frame_bytes = sum(flow.total_frame_bytes for flow in capture.flows)
        total_transferred_bytes = flow_frame_bytes + capture.other_frame_bytes
        total_payload_bytes = sum(flow.payload_bytes for flow in capture.flows)

        overhead_ratio = (
            (total_transferred_bytes - total_payload_bytes) / total_transferred_bytes
            if total_transferred_bytes > 0
            else None
        )

        dominant_server_port = self._find_dominant_server_port(capture.flows)

        return PcapMetrics(
            handshake_rtt_avg=handshake_rtt_avg,
            retransmission_count=retransmission_count,
            zero_window_event_count=zero_window_event_count,
            tcp_reset_drops=tcp_reset_drops,
            total_transferred_bytes=total_transferred_bytes,
            total_payload_bytes=total_payload_bytes,
            overhead_ratio=overhead_ratio,
            dominant_server_port=dominant_server_port,
        )

    def _infer_server_port(self, flow_key: FlowKey) -> int:
        first_port = flow_key.first_endpoint.port
        second_port = flow_key.second_endpoint.port

        first_known = first_port in WELL_KNOWN_PORTS
        second_known = second_port in WELL_KNOWN_PORTS

        if first_known and not second_known:
            return first_port
        if second_known and not first_known:
            return second_port
        return min(first_port, second_port)

    def _find_dominant_server_port(self, flows: tuple[FlowRecord, ...]) -> int | None:
        if not flows:
            return None

        bytes_by_port: dict[int, int] = {}
        for flow in flows:
            server_port = self._infer_server_port(flow.flow_key)
            bytes_by_port[server_port] = bytes_by_port.get(server_port, 0) + flow.total_frame_bytes

        return max(bytes_by_port.items(), key=lambda item: (item[1], -item[0]))[0]