import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PREVIOUS_SCAN_FILE = "previous_scan.json"

def save_current_scan(candidates: list):
    """Sprema trenutni scan za usporedbu u sljedećem alerta."""
    try:
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "candidates": candidates
        }
        with open(PREVIOUS_SCAN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Scan spremljen: {len(candidates)} kandidata")
    except Exception as e:
        logger.error(f"Greška pri spremanju scana: {e}")

def load_previous_scan() -> dict:
    """Učitava prethodni scan."""
    if not os.path.exists(PREVIOUS_SCAN_FILE):
        return {}
    try:
        with open(PREVIOUS_SCAN_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Greška pri učitavanju prethodnog scana: {e}")
        return {}

def get_previous_coin_data(symbol: str) -> dict | None:
    """Vraća prethodne podatke za specifičan coin."""
    previous = load_previous_scan()
    if not previous:
        return None
    candidates = previous.get("candidates", [])
    for coin in candidates:
        if coin.get("symbol") == symbol:
            return coin
    return None

def get_previous_scan_time() -> str | None:
    """Vraća vrijeme prethodnog scana."""
    previous = load_previous_scan()
    if not previous:
        return None
    ts = previous.get("timestamp")
    if ts:
        try:
            dt = datetime.fromisoformat(ts)
            return dt.strftime('%d.%m. %H:%M UTC')
        except:
            return ts
    return None

def build_comparison(symbol: str, current_data: dict) -> str:
    """
    Gradi usporedbu s prethodnim alertom za coin.
    Vraća string s razlikom ili prazan string ako nema prethodnih podataka.
    """
    previous = get_previous_coin_data(symbol)
    if not previous:
        return "🆕 <i>Novi kandidat (nije bio u prethodnom scanu)</i>"
    
    lines = ["📊 <i>Promjena od zadnjeg scana:</i>"]
    
    # Price usporedba
    prev_price_24h = previous.get("price_24h_pct")
    curr_price_24h = current_data.get("price_24h_pct")
    if prev_price_24h is not None and curr_price_24h is not None:
        delta = curr_price_24h - prev_price_24h
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        lines.append(f"  Price 24h: {prev_price_24h:+.2f}% → {curr_price_24h:+.2f}% {arrow}")
    
    # Funding rate usporedba (ako ima futures)
    prev_funding = previous.get("futures", {}).get("funding_rate") if previous.get("futures") else None
    curr_funding = current_data.get("futures", {}).get("funding_rate") if current_data.get("futures") else None
    if prev_funding is not None and curr_funding is not None:
        delta = curr_funding - prev_funding
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        lines.append(f"  Funding: {prev_funding*100:.4f}% → {curr_funding*100:.4f}% {arrow}")
    
    # Top Trader Positions usporedba
    prev_tt = previous.get("futures", {}).get("top_trader_position_ratio") if previous.get("futures") else None
    curr_tt = current_data.get("futures", {}).get("top_trader_position_ratio") if current_data.get("futures") else None
    if prev_tt is not None and curr_tt is not None:
        delta = curr_tt - prev_tt
        arrow = "↑" if delta > 0.01 else "↓" if delta < -0.01 else "→"
        lines.append(f"  Top Trader Pos: {prev_tt:.3f} → {curr_tt:.3f} {arrow}")
    
    # Retail Accounts usporedba
    prev_retail = previous.get("futures", {}).get("retail_account_ratio") if previous.get("futures") else None
    curr_retail = current_data.get("futures", {}).get("retail_account_ratio") if current_data.get("futures") else None
    if prev_retail is not None and curr_retail is not None:
        delta = curr_retail - prev_retail
        arrow = "↑" if delta > 0.01 else "↓" if delta < -0.01 else "→"
        lines.append(f"  Retail Acc: {prev_retail:.3f} → {curr_retail:.3f} {arrow}")
    
    if len(lines) == 1:
        return "🆕 <i>Novi kandidat</i>"
    
    return "\n".join(lines)
