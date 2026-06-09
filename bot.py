import requests
import time
import schedule
from datetime import datetime
import pytz
from flask import Flask
from threading import Thread
import os

# --- 1. FLASK (za 24/7 održavanje) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot je aktivan i skenira!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

t = Thread(target=run_web)
t.start()

# --- 2. TVOJ BOT LOGIKA ---
CMC_API_KEY = "133ae9a26a224359b1a925c007de5bc9"
TELEGRAM_BOT_TOKEN = "8756652282:AAEiRCHQtidqlalDnbPwbVBpoBLkHUZ0CNo"  
TELEGRAM_CHAT_ID = "8190330606"    
hrvatska_zona = pytz.timezone('Europe/Zagreb')

zadnje_stanje_oi = {}
zadnje_stanje_spot_vol = {}

def posalji_telegram_poruku(poruka):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": poruka, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Greška: {e}")

def run_scanner():
    global zadnje_stanje_oi, zadnje_stanje_spot_vol
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
    params = {'limit': '1500'}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=60).json()
        data = res['data']
        top_kandidati = []
        
        for c in data:
            sym = c['symbol']
            spot_vol_24h = c['quote']['USD']['volume_24h']
            market_cap = c['quote']['USD']['market_cap']
            change_24h = c['quote']['USD']['percent_change_24h']
            
            oi_procjena = spot_vol_24h * 0.25 
            
            if sym in zadnje_stanje_oi and zadnje_stanje_oi[sym] > 0:
                delta_oi = ((oi_procjena - zadnje_stanje_oi[sym]) / zadnje_stanje_oi[sym]) * 100
                if abs(delta_oi) > 15:
                    top_kandidati.append(f"🚀 <b>{sym}</b> | ΔOI: {delta_oi:+.2f}% | 24h: {change_24h:+.2f}%\n")
            
            zadnje_stanje_oi[sym] = oi_procjena
        
        if top_kandidati:
            poruka = f"📊 <b>IZVJEŠTAJ ({datetime.now(hrvatska_zona).strftime('%H:%M')})</b>\n\n" + "".join(top_kandidati[:10])
            posalji_telegram_poruku(poruka)
    except Exception as e:
        print(f"Greška: {e}")

# --- 3. RASPPORED ---
schedule.every().day.at("4:32").do(run_scanner)
schedule.every().day.at("14:00").do(run_scanner)
schedule.every().day.at("22:00").do(run_scanner)

while True:
    schedule.run_pending()
    time.sleep(60)
