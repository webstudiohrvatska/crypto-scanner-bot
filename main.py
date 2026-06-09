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

# Flag da spriječimo višestruko pokretanje
scan_u_tijeku = False

app = Flask('')

@app.route('/')
def home():
    now = datetime.now(hrvatska_zona).strftime('%d.%m.%Y %H:%M')
    return f"Bot aktivan | {now} HR", 200

@app.route('/run')
def manual_run():
    global scan_u_tijeku
    if scan_u_tijeku:
        return "⏳ Scan već u tijeku, pričekaj...", 200
    threading.Thread(target=pokreni_scan).start()
    return "🔍 Scan pokrenut — rezultati stižu na Telegram!", 200

@app.route('/listing')
def manual_listing():
    check_listings(posalji_poruku)
    return "🔍 Listing check pokrenut!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def pokreni_scan():
    global scan_u_tijeku
    if scan_u_tijeku:
        logger.info("Scan već u tijeku, preskačem")
        return
    scan_u_tijeku = True
    try:
        asyncio.run(run_analysis())
    except Exception as e:
        logger.error(f"Greška u scanu: {e}")
        posalji_poruku(f"❌ Greška u scanu: {e}")
    finally:
        scan_u_tijeku = False

def listing_job():
    try:
        check_listings(posalji_poruku)
    except Exception as e:
        logger.error(f"Greška u listing jobu: {e}")

def run_scheduler():
    schedule.every().day.at("04:00").do(pokreni_scan)
    schedule.every().day.at("12:00").do(pokreni_scan)
    schedule.every().day.at("20:00").do(pokreni_scan)
    schedule.every(2).minutes.do(listing_job)

    logger.info("Scheduler pokrenut: Scan 06/14/22 HR, Listing svake 2min")

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    logger.info("Crypto bot startao!")

    try:
        check_listings(posalji_poruku)
    except Exception as e:
        logger.error(f"Inicijalni listing check greška: {e}")

    posalji_poruku(
        "🤖 <b>Crypto Bot pokrenut!</b>\n"
        "📊 Scan: 06:00, 14:00, 22:00 HR\n"
        "🆕 Listing monitor: svake 2 minute\n"
        "━━━━━━━━━━━━━━━\n"
        "Samo FULL alertovi (svi filteri zeleni)\n"
        "Futures obavezan ✅"
    )

    threading.Thread(target=run_scheduler, daemon=True).start()
    run_web()
