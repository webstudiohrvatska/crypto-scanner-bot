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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': text}
    requests.get(url, params=params)

def job():
    # OVDJE IDE TVOJ KOD ZA SKENIRANJE
    # Primjer:
    message = "Bot je upravo skenirao tržište! Sve radi."
    send_telegram_message(message)
    print("Poruka poslana!")

# 2. Raspored (Oduzeto 2h za Render server)
# 06:00 -> 04:00
# 14:00 -> 12:00
# 22:00 -> 20:00
schedule.every().day.at("04:48").do(job)
schedule.every().day.at("12:00").do(job)
schedule.every().day.at("20:00").do(job)

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    # Pokreni Flask u pozadini
    threading.Thread(target=run_flask).start()
    
    print("Bot pokrenut...")
    
    # Glavna petlja
    while True:
        schedule.run_pending()
        time.sleep(1)
