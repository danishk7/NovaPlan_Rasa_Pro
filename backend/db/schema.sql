CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'support')),
    bio TEXT,
    location TEXT,
    loyalty_tier TEXT NOT NULL DEFAULT 'Basic',
    auth_provider TEXT NOT NULL DEFAULT 'local',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contacts (
    con_id BIGSERIAL PRIMARY KEY,
    name TEXT,
    email TEXT,
    topic TEXT,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    ses_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    needs_human BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS conversations (
    cov_id BIGSERIAL PRIMARY KEY,
    ses_id TEXT REFERENCES sessions(ses_id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
    text TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS itineraries (
    itn_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    time TEXT,
    title TEXT NOT NULL,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contacts_created_at ON contacts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_session_timestamp ON conversations(ses_id, timestamp ASC);
CREATE INDEX IF NOT EXISTS idx_itineraries_user_created_at ON itineraries(user_id, created_at DESC);

INSERT INTO users (user_id, name, email, password_hash, role)
VALUES ('admin-uuid', 'Admin Nova', 'admin@novaplan.ai', crypt('admin123', gen_salt('bf', 10)), 'admin')
ON CONFLICT (email) DO NOTHING;
