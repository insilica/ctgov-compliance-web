-- Foreign keys / joins
CREATE INDEX IF NOT EXISTS idx_trial_org_id ON trial(organization_id);
CREATE INDEX IF NOT EXISTS idx_trial_user_id ON trial(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_trial_compliance_trial_id ON trial_compliance(trial_id);
CREATE INDEX IF NOT EXISTS idx_trial_compliance_status ON trial_compliance(status);

-- Common sorts/filters
CREATE INDEX IF NOT EXISTS idx_trial_start_date ON trial(start_date DESC);
CREATE INDEX IF NOT EXISTS idx_trial_completion_date ON trial(completion_date);
CREATE INDEX IF NOT EXISTS idx_trial_due_date ON trial(reporting_due_date);

-- Enable trigram for ILIKE %...% searches
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_trial_title_trgm ON trial USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_org_name_trgm ON organization USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_user_email_trgm ON ctgov_user USING gin (email gin_trgm_ops);

-- user_organization join direction used in your queries
CREATE INDEX IF NOT EXISTS idx_user_org_by_org ON user_organization(organization_id, user_id);