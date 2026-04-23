import os
import json
import logging
import datetime
from groq import Groq
from dotenv import load_dotenv
import cache_manager

load_dotenv()
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
Eres un analista cuantitativo de MLB. Genera un reporte matutino riguroso, técnico y reproducible.

DATOS DE ENTRADA:
- Métricas avanzadas de pitcheo (ERA, K%, BB%, HardHit%, xERA si disponible)
- Fatiga de bullpen (innings últimos 3 días)
- Clima/Parque (viento, temperatura, factor de jonrones)
- Matchup R/L y tendencias recientes (últimos 3 OS)

REGLAS DE SALIDA:
1. Usa EXACTAMENTE este formato. No agregues intros ni despedidas.
2. Temperatura mental = 0. Sé determinista.
3. Solo 2 picks. Confianza numérica 1-10.
4. Razonamiento técnico en 1-2 líneas. Sin relleno.

FORMATO OBLIGATORIO:
📊 *ANÁLISIS MATUTINO MLB - {date}*

🔍 *PICK 1*
• Apuesta: [Equipo/Línea]
• Confianza: X/10
• Razonamiento: [Explicación técnica basada en métricas]

🔍 *PICK 2*
• Apuesta: [Equipo/Línea]
• Confianza: X/10
• Razonamiento: [Explicación técnica basada en métricas]

⚠️ *Gestión:* [Recomendación de stake o riesgo]
"""

async def generate_daily_analysis(data: dict) -> str:
    # 1. Verificar caché primero
    cached = cache_manager.get_cached_analysis()
    if cached:
        logger.info("📦 Sirviendo análisis cacheado del día")
        return cached

    if not data or "games" not in data:
        return "❌ Sin datos para generar reporte matutino."

    try:
        # Preparar datos avanzados para la IA
        clean_games = []
        for g in data["games"][:6]:
            h_stats = g.get("home_stats") or {}
            a_stats = g.get("away_stats") or {}
            clean_games.append({
                "matchup": f"{g['away_team']} @ {g['home_team']}",
                "pitchers": f"{g['away_pitcher_name']} vs {g['home_pitcher_name']}",
                "home_adv": {"era": h_stats.get("era"), "k_rate": h_stats.get("k_9"), "bb_rate": h_stats.get("walks")},
                "away_adv": {"era": a_stats.get("era"), "k_rate": a_stats.get("k_9"), "bb_rate": a_stats.get("walks")},
                "odds": g.get("odds"),
                "weather": g.get("weather")
            })

        payload = json.dumps(clean_games, indent=2, ensure_ascii=False)
        today = data.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))

        logger.info("🤖 Generando análisis matutino determinista...")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(date=today)},
                {"role": "user", "content": f"Datos matutinos:\n{payload}"}
            ],
            temperature=0.0,
            seed=42,
            max_tokens=450,
            top_p=0.9
        )

        analysis = response.choices[0].message.content.strip()
        cache_manager.save_analysis(analysis)
        logger.info("✅ Análisis matutino generado y cacheado")
        return analysis

    except Exception as e:
        logger.error(f"❌ Error generando análisis: {e}")
        return f"❌ Error: {str(e)[:80]}"
