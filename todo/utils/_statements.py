CREATE_TABLE = """CREATE TABLE IF NOT EXISTS todo (
    user_id INT PRIMARY KEY,
    todos TEXT NOT NULL,
    completed TEXT NOT NULL,
    user_settings TEXT NOT NULL
);
""".strip()
CREATE_USER_DATA = "INSERT INTO todo VALUES (?, ?, ?, ?)"
SELECT_DATA = "SELECT todos, completed, user_settings FROM todo WHERE user_id = ?"
UPDATE_USER = """UPDATE todo
SET todos = ?, completed = ?, user_settings = ?
WHERE user_id = ?
""".strip()
