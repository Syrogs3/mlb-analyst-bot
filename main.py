import logging
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import BOT_TOKEN
import database as db
from data_fetcher import fetch_all_data_for_today
from analyzer import generate_daily_analysis

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await db.add_user(update.effective_chat.id, update.effective_chat.username or "user")
    await update.message.reply_text(
        "⚾ *Analista MLB Matutino*\n\n"
        "📅 Reporte intenso generado a las 8:00 AM ET\n"
        "🔒 Mismo resultado todo el día\n"
        "/analisis - Ver reporte del día\n"
        "/estado - Tu uso\n\n"
        "⚠️ _Apuesta con responsabilidad._", parse_mode="Markdown")

async def analisis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    can_use, err = await db.can_user_analyze(chat_id)
    if not can_use:
        await update.message.reply_text(err, parse_mode="Markdown")
        return

    msg = await update.message.reply_text("⏳ Cargando reporte matutino cacheado...", parse_mode="Markdown")
    
    # Si es primera consulta del día, genera. Si no, sirve caché.
    data = await fetch_all_data_for_today()
    if "error" in data:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=f"❌ {data['error']}", parse_mode="Markdown")
        return

    text = await generate_daily_analysis(data)
    if len(text) > 4000: text = text[:3900] + "\n\n... _(truncado)_"
    await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=text, parse_mode="Markdown")

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    can_use, _ = await db.can_user_analyze(update.effective_chat.id)
    await update.message.reply_text(
        f"📊 *Estado*\n{'✅ Puedes consultar hoy' if can_use else '⏰ Ya usaste tu análisis hoy'}",
        parse_mode="Markdown")

async def suscribirse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = await db.toggle_subscription(update.effective_chat.id)
    await update.message.reply_text(f"🔔 Alertas: {'✅ ON' if st else '🔕 OFF'}", parse_mode="Markdown")

def main():
    if not BOT_TOKEN: raise ValueError("Falta TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analisis", analisis))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("suscribirse", suscribirse))
    logger.info("✅ Bot matutino listo")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, poll_interval=2.5, timeout=30)

if __name__ == "__main__":
    main()