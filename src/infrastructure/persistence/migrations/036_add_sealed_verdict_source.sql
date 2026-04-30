-- 036_add_sealed_verdict_source.sql
-- Add optional source column to sealed_verdicts for tracking seal origin (e.g. LEGACY_APPROVED).

ALTER TABLE sealed_verdicts ADD COLUMN source TEXT;
