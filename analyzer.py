import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    logger.error(f"Error inicializando Groq: {e}")
    client = None

SYSTEM_PROMPT = """
Eres un analista profesional de apuestas deportivas de Béisbol (MLB) con 10+ años de experiencia.
Tu especialidad es encontrar valor (+EV) en las líneas de apuestas.

REGLAS:
1. Analiza ERA, WHIP, K/9 de los pitchers
2. Considera el clima: viento >10mph afecta totals
3. Busca discrepancias entre odds y probabilidad real
4. Si hay "TBA" en pitchers, enfócate en estadísticas de equipo

FORMATO DE RESPUESTA:
📊 *ANÁLISIS MLB - [Fecha]*

🎯 *TOP PICK (Confianza X/10)*
• [Selección]
• *Razón:* [Explicación técnica]

🔥 **PARLAY SUGERIDO**
1. [Pick 1]
2. [Pick 2]
3. [Pick 3]
• *Explicación:* [Correlación]

⚠️ *RISGOS*
• [1-2 riesgos]

Sé específico y usa datos del JSON.
"""

async def generate_analysis(data: dict) -> str:
    """Genera el análisis usando Groq (Llama 3.3)."""
    if client is None:
        return "❌ Error: Groq no está configurado. Revisa tu GROQ_API_KEY en .env"
    
    if not data or "games" not in data or len(data["games"]) == 0:
        return "❌ No hay juegos disponibles para analizar."
    
    try:
        games_preview = data["games"][:5]
        
        clean_data = []
        for g in games_preview:
            clean_data.append({
                "matchup": f"{g['away_team']} @ {g['home_team']}",
                "pitchers": f"{g['away_pitcher_name']} vs {g['home_pitcher_name']}",
                "odds": g.get('odds'),
                "weather": g.get('weather'),
                "home_stats": g.get('home_stats'),
                "away_stats": g.get('away_stats')
            })
        
        data_json_str = json.dumps(clean_data, indent=2, ensure_ascii=False)
        
        logger.info("🤖 Enviando datos a Groq (Llama 3.3)...")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # ✅ MODELO ACTUALIZADO
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analiza estos juegos de MLB:\n\n{data_json_str}"}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        analysis = response.choices[0].message.content
        logger.info("✅ Análisis generado con Groq")
        return analysis
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error con Groq: {error_msg}")
        
        if "api_key" in error_msg.lower():
            return "❌ Error de API Key: Verifica GROQ_API_KEY en .env"
        return f"❌ Error al generar análisis: {error_msg[:100]}..."