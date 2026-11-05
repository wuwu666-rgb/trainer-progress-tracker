CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    workout_date TEXT NOT NULL,
    exercise TEXT NOT NULL,
    reps INTEGER NOT NULL CHECK (reps > 0),
    weight_lb TEXT NOT NULL
);

INSERT OR IGNORE INTO clients (id, name) VALUES (1, 'Sample Client');

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('trainer', 'client'))
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY,
    trainer_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS template_exercises (
    template_id INTEGER NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_sets INTEGER NOT NULL CHECK (target_sets > 0),
    target_reps INTEGER NOT NULL CHECK (target_reps > 0),
    PRIMARY KEY (template_id, position)
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY,
    trainer_id INTEGER NOT NULL REFERENCES users(id),
    source_template_id INTEGER REFERENCES templates(id) ON DELETE SET NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_exercises (
    plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_sets INTEGER NOT NULL CHECK (target_sets > 0),
    target_reps INTEGER NOT NULL CHECK (target_reps > 0),
    PRIMARY KEY (plan_id, position)
);
