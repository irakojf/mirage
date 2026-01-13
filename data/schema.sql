-- Mirage Database Schema
-- Task management with brain dump, labeling, and review tracking

-- Core task storage
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    bucket TEXT CHECK(bucket IN ('action', 'project', 'idea', 'blocked')),
    status TEXT DEFAULT 'open' CHECK(status IN ('open', 'done', 'archived')),
    estimated_minutes INTEGER,
    times_added INTEGER DEFAULT 1,
    first_added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    blocked_on TEXT,                    -- Who/what it's blocked on
    follow_up_date DATE,                -- For blocked items
    parent_task_id TEXT,                -- For subtasks of projects
    energy_rating TEXT CHECK(energy_rating IN ('red', 'yellow', 'green')),
    notes TEXT,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id)
);

-- Track each brain dump session
CREATE TABLE IF NOT EXISTS dump_sessions (
    id TEXT PRIMARY KEY,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    raw_input TEXT                      -- Full transcript of dump
);

-- Link tasks to the sessions they were added in
CREATE TABLE IF NOT EXISTS task_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    mentioned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (session_id) REFERENCES dump_sessions(id)
);

-- Weekly review records
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    week_start DATE,
    completed_at DATETIME,
    notes TEXT,
    wins TEXT,                          -- JSON array of completed task summaries
    patterns TEXT,                      -- JSON of observed patterns
    next_week_priority TEXT,
    tasks_completed INTEGER,
    tasks_added INTEGER
);

-- Identity statements (who you want to become)
CREATE TABLE IF NOT EXISTS identity (
    category TEXT PRIMARY KEY CHECK(category IN ('love', 'relationships', 'work', 'health', 'wealth')),
    statement TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_bucket ON tasks(bucket);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_task_mentions_task ON task_mentions(task_id);
CREATE INDEX IF NOT EXISTS idx_task_mentions_session ON task_mentions(session_id);
