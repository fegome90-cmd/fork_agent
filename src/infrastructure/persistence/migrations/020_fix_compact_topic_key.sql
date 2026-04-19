-- Migration 020: Fix compact topic_key and type for bridge-saved entries
-- Bridge saved entries with content prefix but no topic_key/type entity fields.
-- Must handle UNIQUE constraint on (topic_key, project) by deduplicating.

-- Step 1: Delete older bridge-saved session summaries (keep only newest per project)
-- The newest has the highest rowid
DELETE FROM observations
WHERE content LIKE 'compact/session-summary:%'
  AND topic_key IS NULL
  AND rowid NOT IN (
    SELECT MAX(rowid) FROM observations
    WHERE content LIKE 'compact/session-summary:%'
      AND topic_key IS NULL
    GROUP BY COALESCE(project, '')
  );

-- Step 2: Set topic_key and type for remaining bridge-saved session summaries
UPDATE observations
SET topic_key = 'compact/session-summary',
    type = 'session-summary'
WHERE content LIKE 'compact/session-summary:%'
  AND (topic_key IS NULL OR type IS NULL OR type != 'session-summary');

-- Step 3: Delete older bridge-saved file-ops (keep only newest per project)
DELETE FROM observations
WHERE content LIKE 'compact/file-ops:%'
  AND topic_key IS NULL
  AND rowid NOT IN (
    SELECT MAX(rowid) FROM observations
    WHERE content LIKE 'compact/file-ops:%'
      AND topic_key IS NULL
    GROUP BY COALESCE(project, '')
  );

-- Step 4: Set topic_key and type for remaining bridge-saved file-ops
UPDATE observations
SET topic_key = 'compact/file-ops',
    type = 'file-ops'
WHERE content LIKE 'compact/file-ops:%'
  AND (topic_key IS NULL OR type IS NULL);

-- Step 5: Set topic_key and type for bridge-saved artifacts-index (if any)
UPDATE observations
SET topic_key = 'compact/artifacts-index',
    type = 'artifacts-index'
WHERE content LIKE 'compact/artifacts-index:%'
  AND (topic_key IS NULL OR type IS NULL);
