import logging
import datetime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import BOT_TOKEN
import database as db
from data_fetcher import fetch_all_data_for_today
from analyzer import generate_daily_analysis

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_chat.username or f"Usuario{chat_id}"
    await db.add_user(chat_id, username)

    await update.message.reply_text(
        f"¡Hola @{username}! 👋\n\n"
        "⚾ *Analista MLB Matutino*\n\n"
        "📅 Reporte intenso generado a las 8:00 AM ET\n"
        "🔒 Mismo resultado todo el día\n\n"
        "Comandos:\n"
        "/analisis - Ver reporte del día\n"
        "/estado - Tu uso\n"
        "/suscribirse - Alertas diarias\n\n"
        "⚠️ _Apuesta con responsabilidad._",
        parse_mode="Markdown"
    )

async def analisis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id

        msg = await update.message.reply_text(
            "⏳ Cargando reporte matutino...",
            parse_mode="Markdown"
        )

        data = await fetch_all_data_for_today()

        if "error" in data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                text=f"❌ {data['error']}",
                parse_mode="Markdown"
            )
            return

        analysis_text = await generate_daily_analysis(data)

        if len(analysis_text) > 4000:
            analysis_text = analysis_text[:3900] + "\n\n... _(mensaje truncado)_"

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=analysis_text,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error en /analisis: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}...")

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    def _get_status():
        import sqlite3
        conn = sqlite3.connect("bot_users.db")
        cursor = conn.cursor()
        cursor.execute('SELECT last_analysis_date, subscribed FROM users WHERE chat_id = ?', (chat_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return "📊 *Estado*\nNo tienes registro de uso."

        last_date = row[0]
        subscribed = row[1]

        status = "📊 *Estado*\n\n"
        status += f"Último análisis: {last_date or 'Nunca'}\n"
        status += f"Notificaciones: {'✅ Activadas' if subscribed else '🔕 Desactivadas'}\n\n"

        if last_date:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            if last_date == today:
                status += "✅ Ya consultaste hoy.\n⏰ Vuelve mañana."
            else:
                status += "✅ Puedes consultar hoy."
        else:
            status += "✅ Nunca has consultado. ¡Prueba /analisis!"

        return status

    try:
        status_text = await asyncio.to_thread(_get_status)
        await update.message.reply_text(status_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error en /estado: {e}")
        await update.message.reply_text("❌ Error al obtener estado")

async def suscribirse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nuevo_estado = await db.toggle_subscription(chat_id)
    estado_texto = "✅ ACTIVADAS" if nuevo_estado else "🔕 DESACTIVADAS"

    await update.message.reply_text(
        f"🔔 *Notificaciones diarias: {estado_texto}*\n\n"
        "Recibirás el análisis con IA automáticamente antes de los primeros juegos.",
        parse_mode="Markdown"
    )

def main():
    if not BOT_TOKEN:
        raise ValueError("⚠️ TELEGRAM_BOT_TOKEN no encontrado en .env")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analisis", analisis))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("suscribirse", suscribirse))

    logger.info("✅ Bot matutino iniciado. Escuchando comandos...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=2.5,
        timeout=30
    )

if __name__ == "__main__":
    main()
