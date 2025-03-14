import sqlite3

class Database:
    def __init__(self, db_name="users.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER, horario TEXT, mensagem TEXT, last_sent TEXT, PRIMARY KEY (user_id, horario))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value INTEGER)")
        self.conn.commit()

    def get_user_reminders(self, user_id):
        self.cursor.execute("SELECT horario, mensagem FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    def add_reminder(self, user_id, horario, mensagem):
        self.cursor.execute("INSERT OR IGNORE INTO users (user_id, horario, mensagem) VALUES (?, ?, ?)", (user_id, horario, mensagem))
        self.conn.commit()

    def delete_user_reminders(self, user_id):
        self.cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_reminders_for_time(self, horario, day):
        self.cursor.execute("SELECT user_id, mensagem FROM users WHERE horario = ? AND (last_sent IS NULL OR last_sent != ?)", (horario, day))
        return self.cursor.fetchall()

    def update_last_sent(self, user_id, horario, day):
        self.cursor.execute("UPDATE users SET last_sent = ? WHERE user_id = ? AND horario = ?", (day, user_id, horario))
        self.conn.commit()

    def get_limit(self):
        self.cursor.execute("SELECT value FROM config WHERE key = 'limite'")
        result = self.cursor.fetchone()
        return result[0] if result else 3

    def set_limit(self, value):
        self.cursor.execute("INSERT OR REPLACE INTO config VALUES (?, ?)", ("limite", value))
        self.conn.commit()

    def close(self):
        self.conn.close()