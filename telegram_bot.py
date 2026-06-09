import requests
import logging
import time

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "8756652282:AAEiRCHQtidqlalDnbPwbVBpoBLkHUZ0CNo"
TELEGRAM_CHAT_ID = "8190330606"

def posalji_poruku(tekst: str) -> bool:
    """Šalje poruku na Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": tekst,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=20)
        if res.status_code == 200:
            return True
        logger.error(f"Telegram greška: {res.status_code} — {res.text}")
        return False
    except Exception as e:
        logger.error(f"Telegram greška: {e}")
        return False

def posalji_dugu_poruku(tekst: str):
    """Dijeli dugu poruku na dijelove od max 4096 znakova."""
    MAX = 4000
    if len(tekst) <= MAX:
        posalji_poruku(tekst)
        return
    
    dijelovi = []
    while tekst:
        if len(tekst) <= MAX:
            dijelovi.append(tekst)
            break
        # Reži na zadnjem newline unutar limita
        rez = tekst[:MAX].rfind('\n')
        if rez == -1:
            rez = MAX
        dijelovi.append(tekst[:rez])
        tekst = tekst[rez:]
    
    for i, dio in enumerate(dijelovi):
        posalji_poruku(dio)
        if i < len(dijelovi) - 1:
            time.sleep(1)

def formatiraj_coin_alert(coin: dict, usporedba: str = "") -> str:
    """
    Formatira alert za jedan coin.
    coin dict sadrži spot + futures podatke.
    """
    symbol = coin.get("symbol", "???")
    name = coin.get("name", "")
    mc = coin.get("market_cap", 0)
    price = coin.get("current_price", 0)
    price_24h = coin.get("price_24h_pct", 0)
    price_7d = coin.get("price_7d_pct", 0)
    vol_24h = coin.get("volume_24h", 0)
    vol_mc = coin.get("vol_mc_ratio", 0)

    futures = coin.get("futures")
    ima_futures = futures is not None and futures.get("has_futures", False)

    # MC format
    if mc >= 1_000_000:
        mc_str = f"${mc/1_000_000:.1f}M"
    else:
        mc_str = f"${mc/1_000:.0f}K"

    # Volume format
    if vol_24h >= 1_000_000:
        vol_str = f"${vol_24h/1_000_000:.1f}M"
    else:
        vol_str = f"${vol_24h/1_000:.0f}K"

    # Emoji za price
    emoji_24h = "🟢" if price_24h >= 0 else "🔴"
    emoji_7d = "🟢" if price_7d >= 0 else "🔴"

    linija = "━━━━━━━━━━━━━━━"

    tekst = f"{linija}\n"
    tekst += f"🪙 <b>{symbol}</b> — {name}\n"
    tekst += f"{linija}\n"

    # SPOT podaci
    tekst += f"📍 <b>SPOT</b>\n"
    tekst += f"  MC: {mc_str}\n"
    tekst += f"  Cijena: ${price:.6f}\n"
    tekst += f"  {emoji_24h} Price 24h: {price_24h:+.2f}%\n"
    tekst += f"  {emoji_7d} Price 7d: {price_7d:+.2f}%\n"
    tekst += f"  Vol 24h: {vol_str} (Vol/MC: {vol_mc:.2f}x)\n"

    # FUTURES podaci
    if ima_futures:
        f_data = futures
        tekst += f"\n📊 <b>FUTURES</b>\n"

        # Funding rate
        funding = f_data.get("funding_rate")
        if funding is not None:
            funding_pct = funding * 100
            funding_emoji = "🟢" if funding < 0 else "🔴"
            tekst += f"  {funding_emoji} Funding: {funding_pct:.4f}%\n"

        # OI/MC
        oi_mc = f_data.get("oi_mc_ratio")
        if oi_mc is not None:
            oi_emoji = "✅" if oi_mc > 0.15 else "❌"
            tekst += f"  {oi_emoji} OI/MC: {oi_mc:.4f}\n"

        # OI u USD
        oi_usd = f_data.get("open_interest_usd")
        if oi_usd is not None:
            if oi_usd >= 1_000_000:
                oi_str = f"${oi_usd/1_000_000:.1f}M"
            else:
                oi_str = f"${oi_usd/1_000:.0f}K"
            tekst += f"  OI: {oi_str}\n"

        # Volume 4h%
        vol_4h = f_data.get("volume_4h_pct")
        if vol_4h is not None:
            vol4h_emoji = "✅" if vol_4h > 30 else "⚠️"
            tekst += f"  {vol4h_emoji} Vol 4h: {vol_4h:+.1f}%\n"

        tekst += f"\n  📈 <b>L/S DIVERGENCIJA</b>\n"

        # Top Trader Positions
        tt_pos = f_data.get("top_trader_position_ratio")
        tt_pos_long = f_data.get("top_trader_position_long_pct")
        tt_pos_short = f_data.get("top_trader_position_short_pct")
        if tt_pos is not None:
            tt_emoji = "✅" if tt_pos > 1.1 else "❌"
            long_pct = f"{tt_pos_long*100:.1f}%" if tt_pos_long else "?"
            short_pct = f"{tt_pos_short*100:.1f}%" if tt_pos_short else "?"
            tekst += f"  {tt_emoji} Top Trader Pos: {tt_pos:.3f}\n"
            tekst += f"     Long {long_pct} / Short {short_pct}\n"

        # Top Trader Accounts (bez filtera)
        tt_acc = f_data.get("top_trader_account_ratio")
        tt_acc_long = f_data.get("top_trader_account_long_pct")
        tt_acc_short = f_data.get("top_trader_account_short_pct")
        if tt_acc is not None:
            long_pct = f"{tt_acc_long*100:.1f}%" if tt_acc_long else "?"
            short_pct = f"{tt_acc_short*100:.1f}%" if tt_acc_short else "?"
            tekst += f"  ℹ️ Top Trader Acc: {tt_acc:.3f}\n"
            tekst += f"     Long {long_pct} / Short {short_pct}\n"

        # Retail Accounts
        retail = f_data.get("retail_account_ratio")
        retail_long = f_data.get("retail_long_pct")
        retail_short = f_data.get("retail_short_pct")
        if retail is not None:
            retail_emoji = "✅" if retail < 1.2 else "❌"
            long_pct = f"{retail_long*100:.1f}%" if retail_long else "?"
            short_pct = f"{retail_short*100:.1f}%" if retail_short else "?"
            tekst += f"  {retail_emoji} Retail Acc: {retail:.3f}\n"
            tekst += f"     Long {long_pct} / Short {short_pct}\n"

    else:
        tekst += f"\n⚠️ <b>Nema futures podataka na Binance</b>\n"

    # Usporedba s prethodnim scanom
    if usporedba:
        tekst += f"\n{usporedba}\n"

    return tekst

def posalji_scan_rezultate(kandidati: list, prethodni_scan_vrijeme: str = None):
    """
    Šalje kompletne rezultate scana na Telegram.
    Dijeli po 5 coinova po poruci.
    """
    from datetime import datetime
    import pytz
    hrvatska_zona = pytz.timezone('Europe/Zagreb')
    now_str = datetime.now(hrvatska_zona).strftime('%d.%m.%Y %H:%M')

    if not kandidati:
        poruka = (
            f"📊 <b>CRYPTO SCAN — {now_str} HR</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"😴 Nema kandidata koji zadovoljavaju filtere.\n"
        )
        if prethodni_scan_vrijeme:
            poruka += f"<i>Prethodni scan: {prethodni_scan_vrijeme}</i>"
        posalji_poruku(poruka)
        return

    # Header poruka
    header = (
        f"📊 <b>CRYPTO SCAN — {now_str} HR</b>\n"
        f"Pronađeno: <b>{len(kandidati)} kandidata</b>\n"
    )
    if prethodni_scan_vrijeme:
        header += f"<i>Prethodni scan: {prethodni_scan_vrijeme}</i>\n"
    posalji_poruku(header)
    time.sleep(1)

    # Šalji po 5 coinova
    batch = []
    for i, coin in enumerate(kandidati):
        from storage import build_comparison
        usporedba = build_comparison(coin["symbol"], coin)
        alert_tekst = formatiraj_coin_alert(coin, usporedba)
        batch.append(alert_tekst)

        if len(batch) == 5 or i == len(kandidati) - 1:
            poruka = "\n".join(batch)
            posalji_dugu_poruku(poruka)
            batch = []
            time.sleep(1.5)
