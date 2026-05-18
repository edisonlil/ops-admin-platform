INSERT INTO audit_logging_settings (
    tenant_id, api_log_enabled, operation_log_enabled, sql_log_enabled, visitor_log_enabled, system_log_enabled,
    slow_sql_threshold_ms, queue_max_size, batch_size, flush_interval_ms,
    plaintext_ip_retention_days, log_retention_days, include_request_headers, include_response_body,
    external_sink_enabled, external_sink_type, config_json, creator, editor
)
SELECT
    0, TRUE, TRUE, TRUE, TRUE, TRUE,
    500, 10000, 100, 1000,
    30, 180, FALSE, FALSE,
    FALSE, '', '{}', 'system', 'system'
WHERE NOT EXISTS (
    SELECT 1 FROM audit_logging_settings WHERE tenant_id = 0 AND deleted = FALSE
);
