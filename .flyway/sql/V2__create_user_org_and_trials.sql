CREATE TABLE organization (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    email_domain VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_organization (
    user_id INTEGER NOT NULL REFERENCES ctgov_user(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'clinician',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, organization_id)
);

CREATE TABLE trial (
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR(20) NOT NULL UNIQUE,
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    title VARCHAR(255),
    start_date DATE,
    user_id INTEGER NOT NULL REFERENCES ctgov_user(id) ON DELETE CASCADE,
    completion_date DATE,
    reporting_due_date DATE
);

CREATE TABLE trial_compliance (
    id SERIAL PRIMARY KEY,
    trial_id INTEGER NOT NULL REFERENCES trial(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    last_checked TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
