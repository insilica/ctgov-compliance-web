CREATE TABLE ctgov_user (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    is_organization BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Index for email lookups
CREATE INDEX idx_ctgov_user_email ON ctgov_user(email);

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ctgov_user_updated_at
    BEFORE UPDATE ON ctgov_user
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
