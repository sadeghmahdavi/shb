from configs import WELL_KNOWN_PORTS
from metrics.models import PcapMetrics
from pcap.models import FlowKey, FlowRecord, ParsedCapture


class PcapMetricsAggregator:
    """Reduces a parsed capture's flows into the aggregate metrics stored in the network_metrics table."""


