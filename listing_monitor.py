import requests
import json
import logging
import os
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

BINANCE_BASE = "https://api.binance.com"
STORAGE_FILE = "known_symbols.json"
hrvatska_zona = pytz.timezone('Europe/Zagreb')

def get_all_binance_spot_symbols() -> set:
    """
    Povlači sve aktivne USDT spot parove s Binance.
    Besplatno, bez API key-a, bez limita.
    """
    try:
        url = f"{BINANCE_BASE}/api/v3/exchangeInfo"
        res = requests.get(url, timeout=30)
        if res.status_code != 200:
            logger.error(f"Binance exchangeInfo greška: {res.status_code}")
            return set()
        
        data = res.json()
        symbols = set()
        
        for s in data.get("symbols", []):
            # Samo aktivni USDT spot parovi
            if (s.get("status") == "TRADING" and 
                s.get("quoteAsset") == "USDT" and
                s.get("isSpotTradingAllowed") == True):
                symbols.add(s["symbol"])
        
        logger.info(f"Binance: {len(symbols)} aktivnih USDT spot parova")
        return symbols
        
    except Exception as e:
        logger.error(f"Binance exchangeInfo greška: {e}")
        return set()

def get_all_binance_futures_symbols() -> set:
    """
    Povlači sve aktivne USDT futures parove s Binance.
    """
    try:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        res = requests.get(url, timeout=30)
        if res.status_code != 200:
            return set()
        
        data = res.json()
        symbols = set()
        
        for s in data.get("symbols", []):
            if (s.get("status") == "TRADING" and 
                s.get("quoteAsset") == "USDT"):
                symbols.add(s["symbol"])
        
        return symbols
        
    except Exception as e:
        logger.error(f"Binance futures exchangeInfo greška: {e}")
        return set()

def load_known_symbols() -> dict:
    """Učitava poznate symbolove iz lokalnog fajla."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"spot": [], "futures": []}

def save_known_symbols(data: dict):
    """Sprema poznate symbolove u lokalni fajl."""
    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Greška pri spremanju symbolova: {e}")

def get_coin_price(symbol: str) -> float | None:
    """Brzo povlači trenutnu cijenu s Binance."""
    try:
        url = f"{BINANCE_BASE}/api/v3/ticker/price"
        res = requests.get(url, params={"symbol": symbol}, timeout=5)
        if res.status_code == 200:
            return float(res.json()["price"])
        return None
    except:
        return None

def check_listings(send_telegram_func) -> None:
    """
    Provjerava nova listanja i delistanja.
    Poziva se svake 2 minute.
    """
    current_spot = get_all_binance_spot_symbols()
    current_futures = get_all_binance_futures_symbols()
    
    if not current_spot:
        logger.warning("Nije moguće povući Binance symbolove")
        return
    
    known = load_known_symbols()
    known_spot = set(known.get("spot", []))
    known_futures = set(known.get("futures", []))
    
    now_str = datetime.now(hrvatska_zona).strftime('%H:%M')
    
    # Inicijalizacija — prvi put samo spremi, ne šalji alert
    if not known_spot:
        logger.info("Inicijalizacija listing monitora — sprema početno stanje")
        save_known_symbols({
            "spot": list(current_spot),
            "futures": list(current_futures)
        })
        return
    
    # SPOT LISTANJA
    nova_spot = current_spot - known_spot
    delistana_spot = known_spot - current_spot
    
    # FUTURES LISTANJA
    nova_futures = current_futures - known_futures
    delistana_futures = known_futures - current_futures
    
    # Šalji alertove za nova listanja
    for symbol in nova_spot:
        # Filtriramo samo USDT parove koji su stvarno novi coinovi
        base = symbol.replace("USDT", "")
        price = get_coin_price(symbol)
        price_str = f"${price:.6f}" if price else "N/A"
        
        # Provjeri ima li futures par
        has_futures = symbol in current_futures or f"{base}USDT" in current_futures
        futures_tag = "🔵 Futures: DA" if has_futures else "⚪ Futures: NE"
        
        poruka = (
            f"🆕 <b>NOVO LISTANJE — SPOT</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🪙 <b>{symbol}</b>\n"
            f"💰 Cijena: {price_str}\n"
            f"{futures_tag}\n"
            f"⏰ {now_str} HR\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚡ Provjeri Binance odmah!"
        )
        logger.info(f"Novo spot listanje: {symbol}")
        send_telegram_func(poruka)
    
    # Šalji alertove za nova futures listanja (ako već postoji spot)
    for symbol in nova_futures:
        if symbol in nova_spot:
            continue  # Već smo poslali gore
        
        price = get_coin_price(symbol)
        price_str = f"${price:.6f}" if price else "N/A"
        
        poruka = (
            f"📈 <b>NOVO FUTURES LISTANJE</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🪙 <b>{symbol}</b>\n"
            f"💰 Mark Price: {price_str}\n"
            f"✅ Spot: već aktivan\n"
            f"⏰ {now_str} HR\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚡ Novi perp par — provjeri funding!"
        )
        logger.info(f"Novo futures listanje: {symbol}")
        send_telegram_func(poruka)
    
    # Delistanja (manje hitno)
    for symbol in delistana_spot:
        poruka = (
            f"🗑️ <b>DELISTING — SPOT</b>\n"
            f"🪙 {symbol} — uklonjen\n"
            f"⏰ {now_str} HR"
        )
        logger.info(f"Spot delisting: {symbol}")
        send_telegram_func(poruka)
    
    # Spremi novo stanje
    if nova_spot or delistana_spot or nova_futures or delistana_futures:
        save_known_symbols({
            "spot": list(current_spot),
            "futures": list(current_futures)
        })
