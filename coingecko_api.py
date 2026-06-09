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
    """
    Povlači coinove s tržišnim podacima.
    Vraća listu coinova s MC, price%, volume%.
    """
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

def get_coin_volume_7d(coin_id: str) -> float | None:
    """
    Povlači 7d volume podatke za jedan coin.
    Koristi market_chart endpoint.
    Pažljivo s pozivima — samo za filtrirane coinove!
    """
    try:
        url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": 7, "interval": "daily"}
        res = requests.get(url, headers=HEADERS, params=params, timeout=20)
        if res.status_code == 429:
            logger.warning("CoinGecko rate limit na market_chart")
            return None
        if res.status_code != 200:
            return None
        data = res.json()
        volumes = data.get("total_volumes", [])
        if len(volumes) < 2:
            return None
        # Volume promjena 7d%: (zadnji - prvi) / prvi * 100
        first_vol = volumes[0][1]
        last_vol = volumes[-1][1]
        if first_vol == 0:
            return None
        return ((last_vol - first_vol) / first_vol) * 100
    except Exception as e:
        logger.debug(f"CoinGecko volume 7d greška za {coin_id}: {e}")
        return None

def scan_spot_candidates() -> list:
    """
    Glavni spot scan — prolazi sve coinove i filtrira po kriterijima.
    
    SPOT filteri:
    - MC: $1.5M – $500M
    - Volume 24h%: +10% do +5000%
    - Price 7d%: -20% do +10%
    - Price 24h%: -10% do +10%
    - Volume 7d%: -100% do +20% (provjeravamo posebno)
    
    Vraća listu kandidata koji prolaze filtere.
    """
    kandidati = []
    
    # Povlačimo prve 3 stranice (750 coinova) — pokriva MC do ~$1.5M
    for page in range(1, 4):
        logger.info(f"CoinGecko scan stranica {page}/3...")
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

                # Preskačemo stablecoins i wrappede tokene
                stable_keywords = ["usd", "usdt", "usdc", "dai", "busd", "tusd", "usdp", 
                                   "wrapped", "wbtc", "weth", "staked"]
                if any(kw in name.lower() for kw in stable_keywords):
                    continue

                # MC filter: $1.5M – $500M
                if not (1_500_000 <= mc <= 500_000_000):
                    continue

                # Volume 24h% filter: +10% do +5000%
                # CoinGecko nema direktno volume_change_24h%, računamo proxy
                # (koristimo total_volume vs mc ratio kao signal aktivnosti)
                # Napomena: pravi volume_24h% dolazi iz volume_7d endpointa
                # Za sada koristimo price + volume kombinaciju kao filter
                
                # Price 7d%: -20% do +10%
                if not (-20 <= price_7d_pct <= 10):
                    continue

                # Price 24h%: -10% do +10%
                if not (-10 <= price_24h_pct <= 10):
                    continue

                # Volume/MC ratio > 0.05 (volumen mora biti značajan)
                vol_mc_ratio = vol_24h / mc if mc > 0 else 0
                if vol_mc_ratio < 0.05:
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
                    # Binance symbol format
                    "binance_symbol": f"{symbol}USDT"
                })

            except Exception as e:
                logger.debug(f"Greška pri obradi coina: {e}")
                continue

        # Pauza između stranica da ne udarimo rate limit
        time.sleep(2)

    logger.info(f"Spot scan završen — {len(kandidati)} kandidata pronađeno")
    return kandidati
