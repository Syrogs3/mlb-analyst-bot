import sqlite3
import asyncio
import os
import datetime

DB_PATH = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            subscribed BOOLEAN DEFAULT 0,
            last_analysis_date TIMESTAMP,
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

async def can_user_analyze(chat_id: int) -> tuple[bool, str]:
    """
    Verifica si el usuario puede pedir análisis hoy.
    Retorna: (puede_usar, mensaje_error)
    """
    def _check():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Obtener último análisis
        cursor.execute('SELECT last_analysis_date FROM users WHERE chat_id = ?', (chat_id,))
        row = cursor.fetchone()
        
        if not row or row[0] is None:
            # Nunca ha pedido análisis
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            cursor.execute('UPDATE users SET last_analysis_date = ? WHERE chat_id = ?', (today, chat_id))
            conn.commit()
            conn.close()
            return True, ""
        
        # Verificar si es hoy
        last_date = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
        today = datetime.datetime.now().date()
        
        if last_date == today:
            # Ya pidió análisis hoy
            conn.close()
            return False, "⏰ Ya pediste un análisis hoy. Vuelve mañana para más picks."
        
        # Actualizar fecha
        today_str = today.strftime("%Y-%m-%d")
        cursor.execute('UPDATE users SET last_analysis_date = ? WHERE chat_id = ?', (today_str, chat_id))
        conn.commit()
        conn.close()
        return True, ""
    
    return await asyncio.to_thread(_check)

# Inicializa la DB
init_db()