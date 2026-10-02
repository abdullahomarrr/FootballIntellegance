ALTER TABLE shortlist_player
ADD COLUMN IF NOT EXISTS decision_evidence jsonb;

COMMENT ON COLUMN shortlist_player.decision_evidence IS
'Immutable-at-selection model evidence snapshot; later workflow-stage edits preserve it unless explicitly replaced.';
