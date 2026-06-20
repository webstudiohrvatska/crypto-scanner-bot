import logging
import time
from coingecko_api import scan_spot_candidates
from binance_api import get_all_futures_data, get_funding_rate
from storage import save_current_scan, get_previous_scan_time
from telegram_bot import posalji_scan_rezultate

logger = logging.getLogger(__name__)

async def run_analysis():
    logger.info("Pokretanje analize...")

    spot_kandidati = scan_spot_candidates()
    logger.info(f"Spot kandidati: {len(spot_kandidati)}")

    if not spot_kandidati:
        from telegram_bot import posalji_poruku
        posalji_poruku("⚠️ Scan nije vratio rezultate — mogući API problem")
        return

    finalni_kandidati = []

    for coin in spot_kandidati:
        symbol = coin["binance_symbol"]
        mc = coin["market_cap"]

        # Samo provjeri postoji li futures par — bez filtriranja po vrijednostima
        futures_data = get_all_futures_data(symbol, market_cap_usd=mc)

        if futures_data:
            coin["futures"] = futures_data
            coin["ima_futures"] = True
            finalni_kandidati.append(coin)
            logger.info(f"✅ {symbol} — ima futures par")
        else:
            logger.info(f"⏭️ {symbol} — nema futures para, preskačem")

        time.sleep(0.3)

    logger.info(f"Finalni kandidati s futures parom: {len(finalni_kandidati)}")

    save_current_scan(finalni_kandidati)

    prethodni_scan_vrijeme = get_previous_scan_time()
    posalji_scan_rezultate(finalni_kandidati, prethodni_scan_vrijeme)

    logger.info("Analiza završena ✅")
