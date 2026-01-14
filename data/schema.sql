-- Mirage Task Management Schema
-- For use with Turso (libSQL) cloud database

-- Tasks table - core task storage
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    bucket TEXT NOT NULL CHECK (bucket IN ('action', 'project', 'idea', 'blocked')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done', 'archived')),
    estimated_minutes INTEGER,
    times_added INTEGER DEFAULT 1,
    first_added_at TEXT NOT NULL,
    last_added_at TEXT NOT NULL,
    notes TEXT,
    energy_rating TEXT CHECK (energy_rating IN ('red', 'yellow', 'green'))
);

-- Dump sessions - track brain dump sessions
CREATE TABLE IF NOT EXISTS dump_sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    raw_input TEXT
);

-- Task mentions - link tasks to sessions they were mentioned in
CREATE TABLE IF NOT EXISTS task_mentions (
    task_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    mentioned_at TEXT NOT NULL,
    PRIMARY KEY (task_id, session_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (session_id) REFERENCES dump_sessions(id)
);

-- Identity statements - user's identity goals by category
CREATE TABLE IF NOT EXISTS identity (
    category TEXT PRIMARY KEY CHECK (category IN ('love', 'relationships', 'work', 'health', 'wealth')),
    statement TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Weekly reviews
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    week_start TEXT NOT NULL,
    energy_reflection TEXT,
    patterns_noted TEXT,
    wins TEXT,
    struggles TEXT,
    next_week_focus TEXT,
    created_at TEXT NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_bucket ON tasks(bucket);
CREATE INDEX IF NOT EXISTS idx_tasks_last_added ON tasks(last_added_at);
