TRUNCATE_ALL_TABLES = "TRUNCATE app_metrics, reviews, network_metrics, applications RESTART IDENTITY CASCADE;"

INSERT_APPLICATION_RETURNING_ID = (
    "INSERT INTO applications (title, package_name, category, is_active) VALUES (%s, %s, 'Games', %s) RETURNING id;"
)

COUNT_NETWORK_METRICS = "SELECT count(*) FROM network_metrics;"

SELECT_NETWORK_METRIC_ROWS = (
    "SELECT app_id, scenario, pcap_filename, pcap_hash, handshake_rtt_avg,"
    " retransmission_count, zero_window_event_count, tcp_reset_drops,"
    " total_transferred_bytes, total_payload_bytes, overhead_ratio, dominant_server_port"
    " FROM network_metrics ORDER BY id;"
)

SELECT_PCAP_FILENAMES = "SELECT pcap_filename FROM network_metrics ORDER BY id;"
