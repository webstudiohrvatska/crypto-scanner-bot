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
    3. Filtri → šalji na Telegram
    """
    logger.info("Pokretanje analize...")

    # 1. Spot scan
    spot_kandidati = scan_spot_candidates()
    logger.info(f"Spot kandidati: {len(spot_kandidati)}")

    if not spot_kandidati:
        logger.warning("Nema spot kandidata — provjeravamo API")
        from telegram_bot import posalji_poruku
        posalji_poruku("⚠️ Scan nije vratio rezultate — mogući API problem")
        return

    # 2. Za svaki spot kandidat povuci futures podatke
    finalni_kandidati = []

    for coin in spot_kandidati:
        symbol = coin["binance_symbol"]  # npr. "XYZUSDT"
        mc = coin["market_cap"]
        price_7d = coin["price_7d_pct"]
        price_24h = coin["price_24h_pct"]

        logger.debug(f"Futures check za {symbol}...")

        futures_data = get_all_futures_data(symbol, market_cap_usd=mc)

        if futures_data:
            # Ima futures — provjeri filtere
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
                # Sve zeleno — puni alert
                coin["alert_tip"] = "FULL"
                finalni_kandidati.append(coin)
                logger.info(f"✅ FULL ALERT: {symbol}")
            else:
                # Futures postoje ali ne prolaze sve filtere
                # Šaljemo samo ako je blizu (min 3/6 zelenih)
                if len(zeleni) >= 3:
                    coin["alert_tip"] = "PARTIAL"
                    finalni_kandidati.append(coin)
                    logger.info(f"⚠️ PARTIAL ALERT: {symbol} ({len(zeleni)}/6 zelenih)")
        else:
            # Nema futures para — šalji samo spot
            coin["futures"] = None
            coin["futures_prolazi"] = False
            coin["alert_tip"] = "SPOT_ONLY"
            finalni_kandidati.append(coin)
            logger.info(f"ℹ️ SPOT ONLY: {symbol}")

        # Pauza da ne prespamo Binance API
        time.sleep(0.3)

    # 3. Sortiraj — FULL prvo, onda PARTIAL, onda SPOT_ONLY
    priority = {"FULL": 0, "PARTIAL": 1, "SPOT_ONLY": 2}
    finalni_kandidati.sort(key=lambda x: priority.get(x.get("alert_tip"), 3))

    logger.info(f"Finalni kandidati: {len(finalni_kandidati)}")
    logger.info(f"  FULL: {sum(1 for c in finalni_kandidati if c.get('alert_tip') == 'FULL')}")
    logger.info(f"  PARTIAL: {sum(1 for c in finalni_kandidati if c.get('alert_tip') == 'PARTIAL')}")
    logger.info(f"  SPOT_ONLY: {sum(1 for c in finalni_kandidati if c.get('alert_tip') == 'SPOT_ONLY')}")

    # 4. Spremi za sljedeću usporedbu
    save_current_scan(finalni_kandidati)

    # 5. Pošalji na Telegram
    prethodni_scan_vrijeme = get_previous_scan_time()
    posalji_scan_rezultate(finalni_kandidati, prethodni_scan_vrijeme)

    logger.info("Analiza završena ✅")
