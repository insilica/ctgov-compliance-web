CREATE TABLE password_reset (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES ctgov_user(id) ON DELETE CASCADE,
    token VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_password_reset_token ON password_reset(token);
