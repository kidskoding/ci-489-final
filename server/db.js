let db;

try {
  const Database = require('better-sqlite3');
  db = new Database('data.db');

  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE,
      password TEXT
    )
  `);
} catch (error) {
  console.warn(`SQLite unavailable; using in-memory auth store. ${error.message}`);
  const users = new Map();
  let nextId = 1;

  db = {
    prepare(sql) {
      if (sql.startsWith('INSERT INTO users')) {
        return {
          run(username, password) {
            if (users.has(username)) {
              throw new Error('Username already exists');
            }
            const id = nextId++;
            users.set(username, { id, username, password });
            return { lastInsertRowid: id };
          },
        };
      }

      if (sql.startsWith('SELECT * FROM users')) {
        return {
          get(username) {
            return users.get(username);
          },
        };
      }

      throw new Error(`Unsupported in-memory SQL: ${sql}`);
    },
  };
}

module.exports = db;
