import os
import aiohttp
import logging
import datetime
import asyncio
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN ---
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# --- CACHE ---
_cache = {}
_CACHE_TTL = 900

async def _fetch_with_cache(url: str, params: dict = None) -> Optional[Dict]:
    """Fetch JSON con caché."""
    cache_key = f"{url}_{str(params)}"
    now = datetime.datetime.now().timestamp()
    
    if cache_key in _cache:
        data, timestamp = _cache[cache_key]
        if now - timestamp < _CACHE_TTL:
            return data
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _cache[cache_key] = (data, now)
                    return data
                else:
                    logger.error(f"Error {resp.status} en {url}")
                    return None
    except Exception as e:
        logger.error(f"Excepción en {url}: {e}")
        return None

async def get_mlb_schedule() -> List[Dict]:
    """Obtiene juegos de hoy."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Buscando juegos para: {today}")
    
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "date": today,
        "gameTypes": "R",
        "sportId": "1"
    }
    
    logger.info(f"URL: {url}")
    logger.info(f"Params: {params}")
    
    data = await _fetch_with_cache(url, params)
    
    if not data:
        logger.error("API no devolvió datos")
        return []
    
    if "dates" not in data:
        logger.error(f"Estructura inesperada: {data.keys()}")
        return []
    
    if not data["dates"]:
        logger.warning(f"No hay juegos para {today}")
        return []
    
    games = []
    for d in data["dates"]:
        for g in d.get("games", []):
            try:
                home = g.get("teams", {}).get("home", {})
                away = g.get("teams", {}).get("away", {})
                
                game = {
                    "game_pk": g.get("gamePk"),
                    "home_team": home.get("team", {}).get("name", "Desconocido"),
                    "away_team": away.get("team", {}).get("name", "Desconocido"),
                    "home_pitcher_id": home.get("probablePitcher", {}).get("id"),
                    "home_pitcher_name": home.get("probablePitcher", {}).get("fullName", "TBA"),
                    "away_pitcher_id": away.get("probablePitcher", {}).get("id"),
                    "away_pitcher_name": away.get("probablePitcher", {}).get("fullName", "TBA"),
                    "venue": g.get("venue", {}).get("name", "Desconocido"),
                    "city": g.get("venue", {}).get("location", {}).get("city", ""),
                    "game_time": g.get("gameDate")
                }
                
                games.append(game)
                logger.info(f"Juego: {game['away_team']} @ {game['home_team']}")
                
            except Exception as e:
                logger.error(f"Error procesando juego: {e}")
                continue
    
    logger.info(f"Total juegos: {len(games)}")
    return games

async def get_pitcher_stats(pitcher_ids: List[int]) -> Dict[int, Dict]:
    """Obtiene stats de pitchers."""
    if not pitcher_ids:
        return {}
    
    valid_ids = [pid for pid in pitcher_ids if isinstance(pid, int) and pid > 0]
    if not valid_ids:
        return {}
    
    logger.info(f"Buscando stats para {len(valid_ids)} pitchers")
    stats = {}
    current_year = datetime.datetime.now().year
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for pid in valid_ids:
            url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats"
            params = {"stats": "season", "season": current_year}
            tasks.append((pid, session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15))))
        
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for i, (pid, _) in enumerate(tasks):
            try:
                res = results[i]
                if isinstance(res, Exception):
                    continue
                    
                if hasattr(res, 'status') and res.status == 200:
                    data = await res.json()
                    if "stats" in data and len(data["stats"]) > 0:
                        season_stats = data["stats"][0].get("stats", {})
                        stats[pid] = {
                            "era": season_stats.get("era", "N/A"),
                            "whip": season_stats.get("whip", "N/A"),
                            "wins": season_stats.get("wins", 0),
                            "losses": season_stats.get("losses", 0),
                            "strikeouts": season_stats.get("strikeOuts", 0)
                        }
            except Exception as e:
                logger.error(f"Error stats pitcher {pid}: {e}")
                continue
    
    return stats

async def get_mlb_odds() -> List[Dict]:
    """Obtiene odds."""
    if not ODDS_API_KEY:
        logger.warning("ODDS_API_KEY no configurada")
        return []
    
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    
    data = await _fetch_with_cache(url, params)
    if not data:
        return []
    
    odds = []
    for game in data:
        bookmakers = game.get("bookmakers", [])
        bk = bookmakers[0] if bookmakers else {}
        markets = bk.get("markets", [])
        
        ml = spread = total = None
        for m in markets:
            if m["key"] == "h2h":
                ml = m["outcomes"]
            elif m["key"] == "spreads":
                spread = m["outcomes"]
            elif m["key"] == "totals":
                total = m["outcomes"]
        
        odds.append({
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "moneyline": ml,
            "spread": spread,
            "total": total
        })
    
    return odds

async def get_weather(city: str) -> Optional[Dict]:
    """Obtiene clima."""
    if not WEATHER_API_KEY or not city:
        return None
    
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "es"
    }
    
    data = await _fetch_with_cache(url, params)
    if data:
        return {
            "temp": data["main"]["temp"],
            "condition": data["weather"][0]["description"],
            "wind": data["wind"]["speed"]
        }
    return None

async def fetch_all_data_for_today() -> Dict[str, Any]:
    """Orquestador principal."""
    logger.info("Iniciando fetch de datos MLB...")
    
    games = await get_mlb_schedule()
    if not games:
        return {"error": "No hay juegos programados hoy o error en API."}
    
    pitcher_ids = list(set([
        g["home_pitcher_id"] for g in games if g["home_pitcher_id"]
    ] + [
        g["away_pitcher_id"] for g in games if g["away_pitcher_id"]
    ]))
    
    pitcher_stats, odds = await asyncio.gather(
        get_pitcher_stats(pitcher_ids),
        get_mlb_odds(),
        return_exceptions=True
    )
    
    if isinstance(pitcher_stats, Exception):
        pitcher_stats = {}
    if isinstance(odds, Exception):
        odds = []
    
    result_games = []
    for g in games:
        home_stats = pitcher_stats.get(g["home_pitcher_id"]) if g.get("home_pitcher_id") else None
        away_stats = pitcher_stats.get(g["away_pitcher_id"]) if g.get("away_pitcher_id") else None
        weather = await get_weather(g["city"]) if g.get("city") else None
        
        game_odds = None
        if odds:
            for o in odds:
                if o["home_team"].lower() == g["home_team"].lower() and o["away_team"].lower() == g["away_team"].lower():
                    game_odds = o
                    break
        
        result_games.append({
            **g,
            "home_stats": home_stats,
            "away_stats": away_stats,
            "odds": game_odds,
            "weather": weather
        })
    
    logger.info(f"Fetch completado: {len(result_games)} juegos")
    return {"games": result_games}