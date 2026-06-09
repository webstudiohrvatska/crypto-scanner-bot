import logging
import time
from coingecko_api import scan_spot_candidates
from binance_api import get_all_futures_data, check_futures_filters
from storage import save_current_scan, get_previous_scan_time
from telegram_bot import posalji_scan_rezultate

logger = logging.getLogger(__name__)

async def run_analysis():
    """
    Glavni scan:
    1. CoinGecko → spot kandidati
    2. Binance → futures podaci za svaki kandidat
    3. Samo FULL (svi futures filteri zeleni) → Telegram
    """
    logger.info("Pokretanje analize...")

    # 1. Spot scan
    spot_kandidati = scan_spot_candidates()
    logger.info(f"Spot kandidati: {len(spot_kandidati)}")

    if not spot_kandidati:
        from telegram_bot import posalji_poruku
        posalji_poruku("⚠️ Scan nije vratio rezultate — mogući API problem")
        return

    # 2. Za svaki spot kandidat povuci futures podatke
    finalni_kandidati = []

    for coin in spot_kandidati:
        symbol = coin["binance_symbol"]
        mc = coin["market_cap"]
        price_7d = coin["price_7d_pct"]
        price_24h = coin["price_24h_pct"]

        futures_data = get_all_futures_data(symbol, market_cap_usd=mc)

        if futures_data:
            prolazi, zeleni, crveni = check_futures_filters(
                futures_data,
                price_7d_pct=price_7d,
                price_24h_pct=price_24h
            )
            coin["futures"] = futures_data
            coin["futures_prolazi"] = prolazi
            coin["futures_zeleni"] = zeleni
            coin["futures_crveni"] = crveni

            if prolazi:
                coin["alert_tip"] = "FULL"
                finalni_kandidati.append(coin)
                logger.info(f"✅ FULL: {symbol}")
            else:
                logger.info(f"❌ {symbol} — {len(zeleni)}/6 zelenih")
        else:
            logger.info(f"⏭️ Nema futures: {symbol}")

        time.sleep(0.3)

    logger.info(f"Finalni kandidati: {len(finalni_kandidati)}")

    # 3. Spremi za sljedeću usporedbu
    save_current_scan(finalni_kandidati)

    # 4. Pošalji na Telegram
    prethodni_scan_vrijeme = get_previous_scan_time()
    posalji_scan_rezultate(finalni_kandidati, prethodni_scan_vrijeme)

    logger.info("Analiza završena ✅")
