import logging
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import BOT_TOKEN
import database as db
from data_fetcher import fetch_all_data_for_today
from analyzer import generate_analysis

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
        "⚾ *Soy tu Analista MLB con IA*\n\n"
        "Uso datos avanzados (ERA, FIP, Clima, Odds) y Machine Learning para encontrar valor en las apuestas.\n\n"
        "Comandos:\n"
        "/analisis - Genera reporte inteligente del día\n"
        "/suscribirse - Alertas diarias\n\n"
        "⚠️ _Apuesta con responsabilidad._",
        parse_mode="Markdown"
    )

async def analisis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = await update.message.reply_text(
            "🔍 *Analizando datos con IA...*\n⏳ Esto puede tomar 10-15 segundos",
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
        
        analysis_text = await generate_analysis(data)
        
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
    app.add_handler(CommandHandler("suscribirse", suscribirse))
    
    logger.info("✅ Bot con IA iniciado. Escuchando comandos...")
    
    # Para Render: usar polling con timeout
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=2.5,
        timeout=30
    )

if __name__ == "__main__":
    main()