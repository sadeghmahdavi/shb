CREATE DATABASE metabase_db;

CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    package_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_metrics (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    min_installs BIGINT,
    real_installs BIGINT,
    score NUMERIC(3, 2),
    ratings BIGINT,
    reviews_count BIGINT,
    version VARCHAR(100),
    ad_supported BOOLEAN,
    store_updated_at TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id VARCHAR(255) PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    user_name VARCHAR(255),
    score INT,
    thumbs_up_count INT DEFAULT 0,
    content TEXT,
    review_at TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS network_metrics (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    scenario VARCHAR(20) NOT NULL,
    pcap_filename VARCHAR(255) NOT NULL,
    pcap_hash CHAR(64) NOT NULL UNIQUE,
    handshake_rtt_avg DOUBLE PRECISION,
    retransmission_count INTEGER NOT NULL,
    zero_window_event_count INTEGER NOT NULL,
    tcp_reset_drops INTEGER NOT NULL,
    total_transferred_bytes BIGINT NOT NULL,
    total_payload_bytes BIGINT NOT NULL,
    overhead_ratio DOUBLE PRECISION,
    dominant_server_port INTEGER,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_metrics_app_scraped ON app_metrics (app_id, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_metrics_scraped_at ON app_metrics (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_app_review_at ON reviews (app_id, review_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_app_score ON reviews (app_id, score);
CREATE INDEX IF NOT EXISTS idx_network_app_scenario ON network_metrics(app_id, scenario);

INSERT INTO applications (title, package_name, category, is_active)
VALUES
  ('Telegram', 'org.telegram.messenger', 'Messaging', TRUE),
  ('WhatsApp', 'com.whatsapp', 'Messaging', TRUE),
  ('MyIrancell', 'com.myirancell', 'Operator', TRUE),
  ('MyMci', 'ir.mci.ecareapp', 'Operator', TRUE),
  ('MyRightel', 'ir.rightel.myrightel', 'Operator', TRUE),
  ('Aparat', 'com.sabaidea.aparat', 'Video Streaming', TRUE),
  ('Filimo', 'com.sabaidea.filimo', 'Video Streaming', TRUE),
  ('Tamashakhonehtv', 'ir.tamashakhonehtv', 'Video Streaming', TRUE),
  ('Fandogh', 'com.plus9.fandogh', 'Word Game', TRUE),
  ('Amirza', 'com.BrainLadder.AmirzaGP', 'Word Game', TRUE),
  ('Samavar', 'com.plus9.samavar', 'Word Game', TRUE),
  ('Baham', 'ir.android.baham', 'Dating & Chat', TRUE),
  ('Pinno', 'app.pinno', 'Dating & Chat', TRUE),
  ('Instagram', 'com.instagram.android', 'Social Media', TRUE),
  ('Facebook', 'com.facebook.katana', 'Social Media', TRUE),
  ('TikTok', 'com.zhiliaoapp.musically', 'Social Media', TRUE)
ON CONFLICT (package_name) DO NOTHING;
