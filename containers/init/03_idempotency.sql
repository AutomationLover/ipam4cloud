-- Idempotency table for tracking duplicate requests
-- This table stores request IDs and their associated parameters/responses
-- to implement idempotent API operations

CREATE TABLE idempotency_record (
    request_id TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    request_params JSONB NOT NULL,
    response_data JSONB NOT NULL,
    status_code INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Indexes for efficient querying
CREATE INDEX idx_idempotency_expires_at ON idempotency_record(expires_at);
CREATE INDEX idx_idempotency_endpoint_method ON idempotency_record(endpoint, method);

-- Function to clean up expired idempotency records
CREATE OR REPLACE FUNCTION cleanup_expired_idempotency_records()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM idempotency_record 
    WHERE expires_at < now();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create a comment explaining the table purpose
COMMENT ON TABLE idempotency_record IS 'Stores idempotent request tracking data to prevent duplicate operations';
COMMENT ON COLUMN idempotency_record.request_id IS 'Unique identifier for the request (UUID or client-provided)';
COMMENT ON COLUMN idempotency_record.endpoint IS 'API endpoint path that was called';
COMMENT ON COLUMN idempotency_record.method IS 'HTTP method (POST, PUT, etc.)';
COMMENT ON COLUMN idempotency_record.request_hash IS 'SHA256 hash of request parameters for comparison';
COMMENT ON COLUMN idempotency_record.request_params IS 'Original request parameters as JSON';
COMMENT ON COLUMN idempotency_record.response_data IS 'Cached response data as JSON';
COMMENT ON COLUMN idempotency_record.status_code IS 'HTTP status code of the original response';
COMMENT ON COLUMN idempotency_record.expires_at IS 'Expiration timestamp for automatic cleanup';

-- Example cleanup job (can be scheduled via cron or application)
-- SELECT cleanup_expired_idempotency_records();


