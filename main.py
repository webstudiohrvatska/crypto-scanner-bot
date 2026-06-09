import asyncio
import schedule
import time
import threading
import logging
import os
from datetime import datetime
import pytz
from flask import Flask
from analyzer import run_analysis
from listing_monitor import check_listings
from telegram_bot import posalji_poruku

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

hrvatska_zona = pytz.timezone('Europe/Zagreb')

# --- FLASK (keepalive za Render + UptimeRobot) ---
app = Flask('')

@app.route('/')
def home():
    now = datetime.now(hrvatska_zona).strftime('%d.%m.%Y %H:%M')
    return f"✅ Bot aktivan | {now} HR", 200

@app.route('/run')
def manual_run():
    """Manualno pokretanje scana za testiranje."""
    threading.Thread(target=lambda: asyncio.run(run_analysis())).start()
    return "🔍 Scan pokrenut — rezultati stižu na Telegram!", 200

@app.route('/listing')
def manual_listing():
    """Manualno pokretanje listing checkera."""
    check_listings(posalji_poruku)
    return "🔍 Listing check pokrenut!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- SCAN JOB (3x dnevno) ---
def scan_job():
    now = datetime.now(hrvatska_zona).strftime('%H:%M')
    logger.info(f"Pokretanje scana u {now} HR")
    try:
        asyncio.run(run_analysis())
    except Exception as e:
        logger.error(f"Greška u scan jobu: {e}")
        posalji_poruku(f"❌ Greška u scanu: {e}")

# --- LISTING JOB (svake 2 minute) ---
def listing_job():
    try:
        check_listings(posalji_poruku)
    except Exception as e:
        logger.error(f"Greška u listing jobu: {e}")

# --- SCHEDULER ---
def run_scheduler():
    # Scan: 04:00, 12:00, 20:00 UTC = 06:00, 14:00, 22:00 HR
    schedule.every().day.at("04:00").do(scan_job)
    schedule.every().day.at("12:00").do(scan_job)
    schedule.every().day.at("20:00").do(scan_job)

    # Listing monitor: svake 2 minute
    schedule.every(2).minutes.do(listing_job)

    logger.info("Scheduler pokrenut:")
    logger.info("  📊 Scan: 06:00, 14:00, 22:00 HR")
    logger.info("  🆕 Listing check: svake 2 minute")

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    logger.info("🚀 Crypto bot startao!")

    # Inicijalni listing check (sprema početno stanje bez alerta)
    try:
        check_listings(posalji_poruku)
        logger.info("Inicijalni listing check završen ✅")
    except Exception as e:
        logger.error(f"Inicijalni listing check greška: {e}")

    posalji_poruku(
        "🤖 <b>Crypto Bot pokrenut!</b>\n"
        "📊 Scan: 06:00, 14:00, 22:00 HR\n"
        "🆕 Listing monitor: svake 2 minute\n"
        "━━━━━━━━━━━━━━━\n"
        "Filters aktivni:\n"
        "• Spot: MC $1.5M–$500M, Vol/MC, Price%\n"
        "• Futures: OI/MC >0.15, Top Trader Pos >1.1\n"
        "• Retail Acc <1.2 (squeeze setup)\n"
        "• L/S divergencija praćena ✅"
    )

    # Pokreni scheduler u pozadini
    threading.Thread(target=run_scheduler, daemon=True).start()

    # Pokreni Flask
    run_web()
