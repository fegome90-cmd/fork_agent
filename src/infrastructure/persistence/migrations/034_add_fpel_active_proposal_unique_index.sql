-- 034_add_fpel_active_proposal_unique_index.sql
-- Partial UNIQUE index ensures at most one ACTIVE proposal per target_id.
-- Prevents TOCTOU race where concurrent freeze() calls could leave
-- multiple ACTIVE proposals for the same target (D7 freeze atomicity).

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_proposal_per_target
    ON frozen_proposals (target_id)
    WHERE lifecycle = 'ACTIVE';
