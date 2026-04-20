import sqlite3
import asyncio
import os

DB_PATH = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            subscribed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

async def add_user(chat_id: int, username: str):
    def _add():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (chat_id, username) VALUES (?, ?)', (chat_id, username))
        conn.commit()
        conn.close()
    await asyncio.to_thread(_add)

async def toggle_subscription(chat_id: int) -> bool:
    def _toggle():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT subscribed FROM users WHERE chat_id = ?', (chat_id,))
        row = cursor.fetchone()
        if row:
            new_status = not bool(row[0])
            cursor.execute('UPDATE users SET subscribed = ? WHERE chat_id = ?', (new_status, chat_id))
        else:
            new_status = True
            cursor.execute('INSERT INTO users (chat_id, subscribed) VALUES (?, ?)', (chat_id, True))
        conn.commit()
        conn.close()
        return new_status
    return await asyncio.to_thread(_toggle)

async def get_subscribed_users() -> list:
    def _get():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id FROM users WHERE subscribed = 1')
        return [row[0] for row in cursor.fetchall()]
    return await asyncio.to_thread(_get)

# Inicializa la DB
init_db()