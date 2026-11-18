from pathlib import Path

from configs import PCAP_ROOT
from metrics.models import PcapMetrics
from pcap.analyzer import PcapAnalyzer
from pcap.discovery import discover_pcap_files
from pcap.errors import PcapParseError
from pcap.models import DiscoveredPcap

from utils.db import Application, fetch_active_apps, find_network_metrics_by_hash, insert_network_metrics
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class Pipeline:
    """Discovers pcap captures, matches them to active applications, then analyzes and persists them."""

    def __init__(self, pcap_root: Path = PCAP_ROOT) -> None:
        """Take the pcap root directory to scan; it defaults to the configured data directory."""
        self._pcap_root = pcap_root

    def run(self) -> None:
        """Discover captures under the pcap root, match them to active applications, then process each."""
        if not self._pcap_root.is_dir():
            logger.warning("pcap root directory not found: %s; nothing to analyze.", self._pcap_root)
            return

        applications = fetch_active_apps()
        files_by_app_name = self._group_by_app_name(discover_pcap_files(self._pcap_root))
        self._report_unmatched_folders(files_by_app_name, applications)

        for application in applications:
            self._process_application(application, files_by_app_name)

    def _group_by_app_name(self, captures: list[DiscoveredPcap]) -> dict[str, list[DiscoveredPcap]]:
        """Group discovered captures by their folder name, lowercased for case-insensitive matching."""
        grouped: dict[str, list[DiscoveredPcap]] = {}
        for capture in captures:
            grouped.setdefault(capture.app_name.lower(), []).append(capture)
        return grouped

    def _report_unmatched_folders(
        self, files_by_app_name: dict[str, list[DiscoveredPcap]], applications: list[Application]
    ) -> None:
        """Log every discovered folder whose name matches no active application's title."""
        known_titles = {application.title.lower() for application in applications}
        for app_name in files_by_app_name:
            if app_name not in known_titles:
                logger.error("pcap folder '%s' does not match any active application; skipping it.", app_name)

    def _process_application(
        self, application: Application, files_by_app_name: dict[str, list[DiscoveredPcap]]
    ) -> None:
        """Process every capture discovered for one application."""
        for capture in files_by_app_name.get(application.title.lower(), []):
            self._process_pcap(application, capture)

    def _process_pcap(self, application: Application, capture: DiscoveredPcap) -> None:
        """Hash-deduplicate, analyze and persist one capture; a failure on one capture does not stop the rest."""
        if find_network_metrics_by_hash(capture.pcap_hash) is not None:
            logger.info(
                "Skipping %s/%s: %s already analyzed (duplicate hash).",
                capture.app_name,
                capture.scenario,
                capture.pcap_path.name,
            )
            return

        logger.info("Analyzing %s/%s: %s", capture.app_name, capture.scenario, capture.pcap_path.name)
        try:
            metrics = PcapAnalyzer().analyze(capture.pcap_path)
        except PcapParseError as error:
            logger.error("Failed to analyze %s: %s", capture.pcap_path, error)
            return

        self._log_metrics(capture, metrics)

        try:
            insert_network_metrics(application.id, metrics.with_capture(capture).to_record())
        except Exception:
            logger.exception("Failed to persist metrics for %s", capture.pcap_path)
            return

        logger.info("Persisted metrics for %s", capture.pcap_path.name)

    def _log_metrics(self, capture: DiscoveredPcap, metrics: PcapMetrics) -> None:
        """Log one capture's aggregate metrics at info level."""
        logger.info(
            "[%s/%s] %s | handshake_rtt_avg=%s retransmissions=%d zero_windows=%d tcp_resets=%d "
            "transferred_bytes=%d payload_bytes=%d overhead_ratio=%s dominant_port=%s",
            capture.app_name,
            capture.scenario,
            capture.pcap_path.name,
            metrics.handshake_rtt_avg,
            metrics.retransmission_count,
            metrics.zero_window_event_count,
            metrics.tcp_reset_drops,
            metrics.total_transferred_bytes,
            metrics.total_payload_bytes,
            metrics.overhead_ratio,
            metrics.dominant_server_port,
        )
