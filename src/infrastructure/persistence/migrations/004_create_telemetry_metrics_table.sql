-- Migration 004: Create telemetry_metrics table
-- Pre-aggregated metrics for fast queries (Prometheus-style)

CREATE TABLE telemetry_metrics (
    id TEXT PRIMARY KEY,
    
    -- Metric identification
    metric_name TEXT NOT NULL,          -- e.g., "hook.fire.count", "agent.spawn.total"
    metric_type TEXT NOT NULL,          -- counter/gauge/histogram
    
    -- Labels (for Prometheus-style metrics)
    labels TEXT,                        -- JSON object: {"hook_name": "workspace-init", "event_type": "SessionStart"}
    labels_hash TEXT,                   -- Hash of labels for deduplication
    
    -- Time bucket (for time-series aggregation)
    bucket_start INTEGER NOT NULL,      -- Start of time bucket (Unix timestamp in seconds)
    bucket_duration INTEGER NOT NULL,   -- Duration of bucket in seconds (60=1min, 3600=1hr, 86400=1day)
    
    -- Values
    value_count INTEGER DEFAULT 0,      -- Number of observations in this bucket
    value_sum REAL DEFAULT 0,           -- Sum of values (for histograms/averages)
    value_min REAL,                     -- Min value in bucket
    value_max REAL,                     -- Max value in bucket
    value_last REAL,                    -- Last value (for gauges)
    
    -- Metadata
    updated_at INTEGER NOT NULL         -- Last update timestamp
);

-- Indexes
CREATE INDEX idx_telemetry_metrics_name ON telemetry_metrics(metric_name);
CREATE INDEX idx_telemetry_metrics_bucket ON telemetry_metrics(bucket_start);
CREATE INDEX idx_telemetry_metrics_name_bucket ON telemetry_metrics(metric_name, bucket_start);
CREATE INDEX idx_telemetry_metrics_type ON telemetry_metrics(metric_type);

-- Unique constraint for deduplication
CREATE UNIQUE INDEX idx_telemetry_metrics_unique ON telemetry_metrics(
    metric_name, labels_hash, bucket_start, bucket_duration
);
