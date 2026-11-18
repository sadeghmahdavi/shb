SELECT_HEALTH_CHECK = "SELECT 1;"

SELECT_ACTIVE_APPLICATIONS = """
    SELECT id, title, package_name
    FROM applications
    WHERE is_active = TRUE
    ORDER BY id;
"""

INSERT_APP_METRICS = """
    INSERT INTO app_metrics (
        app_id, min_installs, real_installs, score, ratings, reviews_count,
        version, ad_supported, store_updated_at, scraped_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

UPSERT_REVIEWS = """
    INSERT INTO reviews (
        review_id, app_id, user_name, score, thumbs_up_count,
        content, review_at, scraped_at
    )
    VALUES %s
    ON CONFLICT (review_id) DO UPDATE SET
        user_name = EXCLUDED.user_name,
        score = EXCLUDED.score,
        thumbs_up_count = EXCLUDED.thumbs_up_count,
        content = EXCLUDED.content,
        review_at = EXCLUDED.review_at,
        scraped_at = EXCLUDED.scraped_at;
"""

SELECT_NETWORK_METRICS_BY_PCAP_HASH = "SELECT id FROM network_metrics WHERE pcap_hash = %s LIMIT 1;"

INSERT_NETWORK_METRICS = """
    INSERT INTO network_metrics (
        app_id, scenario, pcap_filename, pcap_hash,
        handshake_rtt_avg, retransmission_count, zero_window_event_count,
        tcp_reset_drops, total_transferred_bytes, total_payload_bytes,
        overhead_ratio, dominant_server_port
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""
