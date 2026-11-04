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
