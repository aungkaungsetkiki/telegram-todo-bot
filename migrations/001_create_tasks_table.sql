CREATE TABLE IF NOT EXISTS tasks (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  task TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  completed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS tasks_user_id_idx ON tasks(user_id);
