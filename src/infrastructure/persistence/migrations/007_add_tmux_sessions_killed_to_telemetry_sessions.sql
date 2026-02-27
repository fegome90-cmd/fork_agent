-- Migration 007: Add tmux_sessions_killed to telemetry_sessions table

ALTER TABLE telemetry_sessions
ADD COLUMN tmux_sessions_killed INTEGER DEFAULT 0;
