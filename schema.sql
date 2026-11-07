CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('trainer', 'client'))
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    goals TEXT NOT NULL DEFAULT '',
    trainer_id INTEGER REFERENCES users(id),
    client_user_id INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    workout_date TEXT NOT NULL,
    exercise TEXT NOT NULL,
    reps INTEGER NOT NULL CHECK (reps > 0),
    weight_lb TEXT NOT NULL,
    set_count INTEGER NOT NULL DEFAULT 1 CHECK (set_count > 0)
);

CREATE TABLE IF NOT EXISTS client_invitations (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    client_user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined'))
);

CREATE UNIQUE INDEX IF NOT EXISTS client_pending_invitation
ON client_invitations (client_id) WHERE status = 'pending';

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
    target_weight_lb TEXT,
    PRIMARY KEY (template_id, position)
);

CREATE TABLE IF NOT EXISTS cardio_workouts (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    workout_date TEXT NOT NULL,
    exercise TEXT NOT NULL,
    duration_min TEXT NOT NULL,
    distance_km TEXT,
    set_count INTEGER NOT NULL DEFAULT 1 CHECK (set_count > 0)
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY,
    trainer_id INTEGER NOT NULL REFERENCES users(id),
    source_template_id INTEGER REFERENCES templates(id) ON DELETE SET NULL,
    profile_id INTEGER REFERENCES clients(id),
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_exercises (
    plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_sets INTEGER NOT NULL CHECK (target_sets > 0),
    target_reps INTEGER NOT NULL CHECK (target_reps > 0),
    target_weight_lb TEXT,
    PRIMARY KEY (plan_id, position)
);
