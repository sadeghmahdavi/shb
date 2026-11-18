TRUNCATE_ALL_TABLES = "TRUNCATE app_metrics, reviews, network_metrics, applications RESTART IDENTITY CASCADE;"

INSERT_APPLICATION_RETURNING_ID = (
    "INSERT INTO applications (title, package_name, category, is_active) VALUES (%s, %s, 'Games', %s) RETURNING id;"
)

INSERT_ACTIVE_AND_INACTIVE_APPLICATIONS = (
    "INSERT INTO applications (title, package_name, category, is_active) VALUES"
    " ('Telegram', 'org.telegram.messenger', 'Messaging', TRUE),"
    " ('Inactive', 'com.inactive.app', 'Games', FALSE);"
)

COUNT_APP_METRICS = "SELECT count(*) FROM app_metrics;"
COUNT_APP_METRICS_FOR_APP = "SELECT count(*) FROM app_metrics WHERE app_id = %s;"
COUNT_REVIEWS = "SELECT count(*) FROM reviews;"
COUNT_REVIEWS_FOR_APP = "SELECT count(*) FROM reviews WHERE app_id = %s;"

SELECT_APP_IDS_WITH_METRICS = "SELECT app_id FROM app_metrics ORDER BY app_id;"
SELECT_APP_REVIEW_IDS = "SELECT app_id, review_id FROM reviews ORDER BY app_id, review_id;"
SELECT_APP_METRICS_ROW = "SELECT min_installs, score, version, ad_supported FROM app_metrics WHERE app_id = %s;"
SELECT_REVIEW_CONTENTS = "SELECT review_id, content FROM reviews WHERE app_id = %s ORDER BY review_id;"
