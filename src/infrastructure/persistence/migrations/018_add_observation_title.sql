-- Migration 018: Add title column to observations table
-- Short searchable title for observations

ALTER TABLE observations ADD COLUMN title TEXT;
