import requests
import logging
import time

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CG_API_KEY = "CG-vq1LMsWnjaMgNb92WTXpi3XL"

HEADERS = {
    "accept": "application/json",
    "x-cg-demo-api-key": CG_API_KEY
}

def get_all_coins_markets(page: int = 1, per_page: int = 250) -> list:
    try:
        url = f"{COINGECKO_BASE}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": False,
            "price_change_percentage": "24h,7d"
        }
        res = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if res.status_code == 429:
            logger.warning("CoinGecko rate limit — čekam 60s")
            time.sleep(60)
            return []
        if res.status_code != 200:
            logger.error(f"CoinGecko greška: {res.status_code}")
            return []
        return res.json()
    except Exception as e:
        logger.error(f"CoinGecko markets greška: {e}")
        return []

def scan_spot_candidates() -> list:
    """
    Faza mira / kapitulacija setup:
    - MC: $3M - $150M
    - Price 7d%: -20% do -45% (brutalni dump, slabe ruke isprane)
    - Price 24h%: -2% do +2% (faza mira, cijena stagnira)
    - Price 4h% proxy: gledamo da nije eksplozivan
    - Volume/MC ratio: nizak (mrtav volumen = faza mira)
    - Net Inflow proxy: volume raste ali cijena ne prati = whale apsorbira
    """
    kandidati = []

    for page in range(1, 5):
        logger.info(f"CoinGecko scan stranica {page}/4...")
        coins = get_all_coins_markets(page=page, per_page=250)
        if not coins:
            break

        for coin in coins:
            try:
                mc = coin.get("market_cap") or 0
                vol_24h = coin.get("total_volume") or 0
                price_24h_pct = coin.get("price_change_percentage_24h") or 0
                price_7d_pct = coin.get("price_change_percentage_7d_in_currency") or 0
                symbol = coin.get("symbol", "").upper()
                name = coin.get("name", "")
                coin_id = coin.get("id", "")
                current_price = coin.get("current_price") or 0

                # Preskoči stablecoins i wrappede
                stable_keywords = ["usd", "usdt", "usdc", "dai", "busd", "tusd",
                                   "wrapped", "wbtc", "weth", "staked"]
                if any(kw in name.lower() for kw in stable_keywords):
                    continue

                # MC: $3M - $150M
                if not (3_000_000 <= mc <= 150_000_000):
                    continue

                # Price 7d%: -20% do -45% (kapitulacija)
                if not (-45 <= price_7d_pct <= -20):
                    continue

                # Price 24h%: -2% do +2% (faza mira)
                if not (-2 <= price_24h_pct <= 2):
                    continue

                # Volume/MC ratio: mora biti nizak (mrtav volumen)
                # Faza mira = vol/mc ispod 0.15
                vol_mc_ratio = vol_24h / mc if mc > 0 else 0
                if vol_mc_ratio > 0.15:
                    continue

                # Mora imati minimalni volumen (nije mrtav coin)
                if vol_24h < 10_000:
                    continue

                kandidati.append({
                    "symbol": symbol,
                    "name": name,
                    "coin_id": coin_id,
                    "market_cap": mc,
                    "current_price": current_price,
                    "volume_24h": vol_24h,
                    "vol_mc_ratio": vol_mc_ratio,
                    "price_24h_pct": price_24h_pct,
                    "price_7d_pct": price_7d_pct,
                    "binance_symbol": f"{symbol}USDT"
                })

            except Exception as e:
                logger.debug(f"Greška pri obradi coina: {e}")
                continue

        time.sleep(2)

    logger.info(f"Spot scan završen — {len(kandidati)} kandidata")
    return kandidati
