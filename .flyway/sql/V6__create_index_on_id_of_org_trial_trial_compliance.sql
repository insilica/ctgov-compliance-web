CREATE INDEX ON organization (id);

CREATE INDEX ON trial (id);
CREATE INDEX ON trial (organization_id);
CREATE INDEX ON trial (user_id);

CREATE INDEX ON trial_compliance (id);
CREATE INDEX ON trial_compliance (trial_id);
