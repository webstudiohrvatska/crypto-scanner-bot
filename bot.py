import requests
import time
import schedule
from datetime import datetime
import pytz
from flask import Flask
from threading import Thread
import os

# --- 1. FLASK (Web server za Render) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot je aktivan i skenira!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. KONFIGURACIJA ---
CMC_API_KEY = "133ae9a26a224359b1a925c007de5bc9"
TELEGRAM_BOT_TOKEN = "8756652282:AAEiRCHQtidqlalDnbPwbVBpoBLkHUZ0CNo"  
TELEGRAM_CHAT_ID = "8190330606"    
hrvatska_zona = pytz.timezone('Europe/Zagreb')

def posalji_telegram_poruku(poruka):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": poruka, "parse_mode": "HTML"}, timeout=20)
    except Exception as e:
        print(f"Greška pri slanju: {e}")

def run_scanner():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
    # Povlačimo 500 tokena da imamo dovoljno uzoraka za filtere
    params = {'limit': '500', 'sort': 'volume_24h', 'sort_dir': 'desc'}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=60).json()
        data = res['data']
        poruka = f"📊 <b>SKENER (Strogi kriteriji) - {datetime.now(hrvatska_zona).strftime('%H:%M')}</b>\n\n"
        nasao_kandidate = False
        
        for c in data:
            sym = c['symbol']
            mc = c['quote']['USD']['market_cap']
            vol_chg = c['quote']['USD']['volume_change_24h']
            p_24h = c['quote']['USD']['percent_change_24h']
            p_7d = c['quote']['USD']['percent_change_7d']
            
            # --- STROGI FILTERI ---
            # MC: 1.5M - 500M
            # Vol 24h: > 50%
            # Price 24h: -10% do +5%
            # Price 7d: -20% do +10%
            
            if (1_500_000 <= mc <= 500_000_000) and \
               (vol_chg >= 50) and \
               (-10 <= p_24h <= 5) and \
               (-20 <= p_7d <= 10):
                
                nasao_kandidate = True
                poruka += (f"🚀 <b>{sym}</b>\n"
                           f"• MC: ${mc/1_000_000:.1f}M\n"
                           f"• Vol 24h Δ: {vol_chg:+.2f}%\n"
                           f"• Price 24h: {p_24h:+.2f}% | 7d: {p_7d:+.2f}%\n"
                           f"--------------------------\n")
        
        if nasao_kandidate:
            posalji_telegram_poruku(poruka)
        else:
            print("Nema tokena koji zadovoljavaju stroge kriterije.")
            
    except Exception as e:
        print(f"Greška u skeneru: {e}")

# --- 3. RASPPORED ---
# 04:00, 12:00, 20:00 (UTC) odgovara 06:00, 14:00, 22:00 (Hrvatska)
schedule.every().day.at("04:00").do(run_scanner)
schedule.every().day.at("12:00").do(run_scanner)
schedule.every().day.at("20:00").do(run_scanner)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=run_web).start()
    Thread(target=run_schedule).start()
