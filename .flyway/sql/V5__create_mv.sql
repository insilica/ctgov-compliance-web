CREATE MATERIALIZED VIEW joined_trials AS
SELECT
  t.id AS trial_id,
  t.nct_id,
  o.id AS organization_id,
  u.id AS user_id,
  t.title,
  t.start_date,
  t.completion_date,
  t.reporting_due_date,
  tc.status AS compliance_status,
  tc.last_checked,
  o.name AS organization_name,
  o.created_at AS organization_created_at,
  u.email AS user_email,
  uo.role AS user_role
FROM trial t
LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
LEFT JOIN organization o ON o.id = t.organization_id
LEFT JOIN ctgov_user u ON u.id = t.user_id
LEFT JOIN user_organization uo ON u.id = uo.user_id AND o.id = uo.organization_id;

-- Required for CONCURRENT refresh
CREATE UNIQUE INDEX ON joined_trials (trial_id);

-- Helpful indexes for your filters/sorts
CREATE INDEX ON joined_trials (organization_id);
CREATE INDEX ON joined_trials (user_id);
CREATE INDEX ON joined_trials (compliance_status);
CREATE INDEX ON joined_trials (start_date DESC);
CREATE INDEX ON joined_trials (reporting_due_date);
CREATE INDEX ON joined_trials (completion_date);
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ON joined_trials USING gin (title gin_trgm_ops);
CREATE INDEX ON joined_trials USING gin (organization_name gin_trgm_ops);
CREATE INDEX ON joined_trials USING gin (user_email gin_trgm_ops);
-- Optional for ILIKE on nct_id if you do contains searches:
CREATE INDEX ON joined_trials USING gin (nct_id gin_trgm_ops);

CREATE MATERIALIZED VIEW compare_orgs AS
SELECT 
  o.id,
  o.name,
  o.email_domain,
  o.created_at,
  SUM(CASE WHEN tc.status = 'Compliant' THEN 1 ELSE 0 END) AS on_time_count,
  SUM(CASE WHEN tc.status = 'Incompliant' THEN 1 ELSE 0 END) AS late_count,
  -- Calculate reporting rate as percentage of trials with status
  ROUND(
      (COUNT(CASE WHEN tc.status IS NOT NULL THEN 1 END) * 100.0 / NULLIF(COUNT(t.id), 0)), 
      1
  ) AS reporting_rate,
  -- Placeholder for funding source (would need additional table)
  NULL AS funding_source,
  -- Placeholder for Wilson LCB score (would need calculation)
  NULL AS wilson_lcb_score
FROM organization o
LEFT JOIN trial t ON o.id = t.organization_id
LEFT JOIN trial_compliance tc ON t.id = tc.trial_id
GROUP BY o.id, o.name, o.email_domain, o.created_at;

-- Indexes to support compare_orgs usage and CONCURRENT refresh
CREATE UNIQUE INDEX ON compare_orgs (id);
CREATE INDEX ON compare_orgs (total_trials DESC);
CREATE INDEX ON compare_orgs (name);
CREATE INDEX ON compare_orgs (reporting_rate);