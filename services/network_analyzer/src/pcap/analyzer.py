from pathlib import Path

from metrics.aggregator import PcapMetricsAggregator
from metrics.models import PcapMetrics
from pcap.parser import PcapParser


class PcapAnalyzer:
    """Analyzes one capture end to end: packet rows from the parser, aggregate metrics from the aggregator."""

    def __init__(self) -> None:
        """Own a parser and an aggregator, one capture at a time."""
        self._parser = PcapParser()
        self._aggregator = PcapMetricsAggregator()

    def analyze(self, pcap_path: Path) -> PcapMetrics:
        """Parse one capture into flows, then reduce them into aggregate metrics."""
        return self._aggregator.aggregate(self._parser.parse(pcap_path))
