import os
import time
import threading
import schedule
import requests
from flask import Flask

app = Flask(__name__)

# Učitavanje varijabli
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
            print("Telegram poruka poslana!")
        except Exception as e:
            print(f"Greška pri slanju: {e}")

def job():
    send_telegram_message("Sustav je aktivan i skenira tržište.")

# Raspored
schedule.every().day.at("04:00").do(job)
schedule.every().day.at("12:00").do(job)
schedule.every().day.at("20:00").do(job)

def run_scheduler():
    # TEST: Pošalji poruku odmah pri pokretanju da vidimo radi li bot
    send_telegram_message("Bot se uspješno pokrenuo na serveru!")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Pokreni scheduler u pozadini
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Pokreni Flask
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
