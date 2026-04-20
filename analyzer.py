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
Eres un analista profesional de MLB especializado en encontrar valor en apuestas.

TU MISIÓN:
Analiza los datos y selecciona SOLO LOS 2 MEJORES PICKS del día.

REGLAS:
1. Sé MUY selectivo - solo elige si hay valor claro
2. Basa tus picks en: ERA, clima, splits, tendencias
3. Nivel de confianza: 1-10 (solo 7+ si hay valor real)
4. Explicación: MÁXIMO 2 líneas, directo al punto

FORMATO OBLIGATORIO:
📊 *MLB PICKS - [Fecha]*

🎯 **PICK 1**
• *Apuesta:* [Equipo/Línea]
• *Confianza:* ⭐⭐⭐⭐⭐⭐⭐⭐ (X/10)
• *Por qué:* [Explicación en 1-2 líneas]

🎯 **PICK 2**
• *Apuesta:* [Equipo/Línea]
• *Confianza:* ⭐⭐⭐⭐⭐⭐ (X/10)
• *Por qué:* [Explicación en 1-2 líneas]

⚠️ *Nota:* {Si no hay picks claros, di "Hoy no hay valor claro. Mejor no apostar."}

Sé honesto. Si no hay valor, no inventes picks.
"""

async def generate_analysis(data: dict) -> str:
    """Genera análisis con SOLO 2 picks principales."""
    if client is None:
        return "❌ Error: Groq no configurado. Revisa GROQ_API_KEY"
    
    if not data or "games" not in data or len(data["games"]) == 0:
        return "❌ No hay juegos hoy."
    
    try:
        # Preparar datos para IA (primeros 5 juegos)
        games_preview = data["games"][:5]
        
        clean_data = []
        for g in games_preview:
            clean_data.append({
                "matchup": f"{g['away_team']} @ {g['home_team']}",
                "pitchers": f"{g['away_pitcher_name']} vs {g['home_pitcher_name']}",
                "home_era": g.get('home_stats', {}).get('era', 'N/A'),
                "away_era": g.get('away_stats', {}).get('era', 'N/A'),
                "odds": g.get('odds'),
                "weather": g.get('weather')
            })
        
        data_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
        
        logger.info("🤖 Generando 2 picks con IA...")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Datos de hoy:\n{data_json}"}
            ],
            temperature=0.1,  # Más determinista
            max_tokens=500    # Respuesta corta
        )
        
        analysis = response.choices[0].message.content
        logger.info("✅ Picks generados")
        return analysis
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error Groq: {error_msg}")
        
        if "api_key" in error_msg.lower():
            return "❌ Error: Verifica GROQ_API_KEY"
        return f"❌ Error: {error_msg[:80]}"