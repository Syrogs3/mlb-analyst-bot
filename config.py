import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("⚠️ TELEGRAM_BOT_TOKEN no encontrado en .env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")