import os
import time
import threading
import schedule
import requests
from flask import Flask

# 1. Postavke
app = Flask(__name__)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

@app.route('/')
def home():
    return "Bot is running!"

def send_telegram_message(text):
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {'chat_id': CHAT_ID, 'text': text}
        try:
            requests.get(url, params=params)
        except Exception as e:
            print(f"Greška: {e}")

def job():
    print("Skeniranje u tijeku...")
    message = "Izvještaj: Sustav radi i skenira tržište."
    send_telegram_message(message)

# 2. Raspored (Oduzeto 2h za razliku servera)
# 06:00 (lokalno) -> 04:00 (server)
# 14:00 (lokalno) -> 12:00 (server)
# 22:00 (lokalno) -> 20:00 (server)
schedule.every().day.at("04:00").do(job)
schedule.every().day.at("12:00").do(job)
schedule.every().day.at("20:00").do(job)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Pokreni scheduler u pozadini
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Pokreni Flask (Render očekuje port 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
