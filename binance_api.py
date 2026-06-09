import requests
import logging

logger = logging.getLogger(__name__)

BINANCE_FAPI = "https://fapi.binance.com"

def get_funding_rate(symbol: str) -> dict | None:
    """Trenutni funding rate za symbol"""
    try:
        url = f"{BINANCE_FAPI}/fapi/v1/premiumIndex"
        res = requests.get(url, params={"symbol": symbol}, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        return {
            "funding_rate": float(data["lastFundingRate"]),
            "mark_price": float(data["markPrice"]),
        }
    except Exception as e:
        logger.debug(f"Funding rate greška za {symbol}: {e}")
        return None

def get_open_interest(symbol: str) -> dict | None:
    """Open Interest za symbol"""
    try:
        url = f"{BINANCE_FAPI}/fapi/v1/openInterest"
        res = requests.get(url, params={"symbol": symbol}, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        return {"open_interest": float(data["openInterest"])}
    except Exception as e:
        logger.debug(f"OI greška za {symbol}: {e}")
        return None

def get_top_trader_position_ratio(symbol: str, period: str = "4h") -> dict | None:
    """
    Top Trader L/S POSITIONS ratio
    Filter: > 1.1 = smart money više long pozicija
    """
    try:
        url = f"{BINANCE_FAPI}/futures/data/topLongShortPositionRatio"
        res = requests.get(url, params={"symbol": symbol, "period": period, "limit": 1}, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        if not data:
            return None
        latest = data[-1]
        return {
            "ratio": float(latest["longShortRatio"]),
            "long_pct": float(latest["longAccount"]),
            "short_pct": float(latest["shortAccount"])
        }
    except Exception as e:
        logger.debug(f"Top trader positions greška za {symbol}: {e}")
        return None

def get_top_trader_account_ratio(symbol: str, period: str = "4h") -> dict | None:
    """
    Top Trader L/S ACCOUNTS ratio
    Prikazujemo bez filtera — za divergenciju
    """
    try:
        url = f"{BINANCE_FAPI}/futures/data/topLongShortAccountRatio"
        res = requests.get(url, params={"symbol": symbol, "period": period, "limit": 1}, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        if not data:
            return None
        latest = data[-1]
        return {
            "ratio": float(latest["longShortRatio"]),
            "long_pct": float(latest["longAccount"]),
            "short_pct": float(latest["shortAccount"])
        }
    except Exception as e:
        logger.debug(f"Top trader accounts greška za {symbol}: {e}")
        return None

def get_retail_account_ratio(symbol: str, period: str = "4h") -> dict | None:
    """
    Global/Retail L/S ACCOUNTS ratio
    Filter: < 1.2 = retail kratak (squeeze setup)
    """
    try:
        url = f"{BINANCE_FAPI}/futures/data/globalLongShortAccountRatio"
        res = requests.get(url, params={"symbol": symbol, "period": period, "limit": 1}, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        if not data:
            return None
        latest = data[-1]
        return {
            "ratio": float(latest["longShortRatio"]),
            "long_pct": float(latest["longAccount"]),
            "short_pct": float(latest["shortAccount"])
        }
    except Exception as e:
        logger.debug(f"Retail accounts greška za {symbol}: {e}")
        return None

def get_futures_klines_volume(symbol: str) -> dict | None:
    """
    Volumen iz klines za 4h% izračun.
    Uspoređuje zadnju 4h svjećicu s prethodnom.
    """
    try:
        url = f"{BINANCE_FAPI}/fapi/v1/klines"
        res = requests.get(url, params={"symbol": symbol, "interval": "4h", "limit": 3}, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        if len(data) < 2:
            return None
        # Kline format: [open_time, open, high, low, close, volume, ...]
        prev_vol = float(data[-2][5])
        curr_vol = float(data[-1][5])
        if prev_vol == 0:
            return None
        vol_4h_pct = ((curr_vol - prev_vol) / prev_vol) * 100
        return {
            "volume_4h_pct": vol_4h_pct,
            "current_volume": curr_vol,
            "prev_volume": prev_vol
        }
    except Exception as e:
        logger.debug(f"Klines volume greška za {symbol}: {e}")
        return None

def get_all_futures_data(symbol: str, market_cap_usd: float = None) -> dict | None:
    """
    Povlači sve futures podatke za jedan symbol.
    Vraća None ako symbol nema futures par na Binance.
    """
    # Provjeri postoji li futures par
    funding = get_funding_rate(symbol)
    if funding is None:
        return None  # Nema futures para

    oi = get_open_interest(symbol)
    top_positions = get_top_trader_position_ratio(symbol)
    top_accounts = get_top_trader_account_ratio(symbol)
    retail_accounts = get_retail_account_ratio(symbol)
    vol_4h = get_futures_klines_volume(symbol)

    # OI/MC ratio
    oi_mc_ratio = None
    if oi and market_cap_usd and market_cap_usd > 0:
        oi_value_usd = oi["open_interest"] * funding["mark_price"]
        oi_mc_ratio = oi_value_usd / market_cap_usd

    return {
        "has_futures": True,
        "funding_rate": funding["funding_rate"],
        "mark_price": funding["mark_price"],
        "oi_mc_ratio": oi_mc_ratio,
        "open_interest_usd": (oi["open_interest"] * funding["mark_price"]) if oi else None,
        # Top Trader Positions (filter: > 1.1)
        "top_trader_position_ratio": top_positions["ratio"] if top_positions else None,
        "top_trader_position_long_pct": top_positions["long_pct"] if top_positions else None,
        "top_trader_position_short_pct": top_positions["short_pct"] if top_positions else None,
        # Top Trader Accounts (bez filtera — divergencija)
        "top_trader_account_ratio": top_accounts["ratio"] if top_accounts else None,
        "top_trader_account_long_pct": top_accounts["long_pct"] if top_accounts else None,
        "top_trader_account_short_pct": top_accounts["short_pct"] if top_accounts else None,
        # Retail Accounts (filter: < 1.2)
        "retail_account_ratio": retail_accounts["ratio"] if retail_accounts else None,
        "retail_long_pct": retail_accounts["long_pct"] if retail_accounts else None,
        "retail_short_pct": retail_accounts["short_pct"] if retail_accounts else None,
        # Volume 4h%
        "volume_4h_pct": vol_4h["volume_4h_pct"] if vol_4h else None,
    }

def check_futures_filters(futures_data: dict, price_7d_pct: float, price_24h_pct: float) -> tuple:
    """
    Provjerava futures filtere.
    Vraća: (prolazi_sve, zeleni_list, crveni_list)
    """
    if not futures_data or not futures_data.get("has_futures"):
        return False, [], ["Nema futures para na Binance"]

    zeleni = []
    crveni = []

    # 1. OI/MC > 0.15
    oi_mc = futures_data.get("oi_mc_ratio")
    if oi_mc is not None:
        if oi_mc > 0.15:
            zeleni.append(f"✅ OI/MC: {oi_mc:.4f}")
        else:
            crveni.append(f"❌ OI/MC: {oi_mc:.4f} (treba >0.15)")
    else:
        crveni.append("❌ OI/MC: N/A")

    # 2. Volume 4h% > 30%
    vol_4h = futures_data.get("volume_4h_pct")
    if vol_4h is not None:
        if vol_4h > 30:
            zeleni.append(f"✅ Vol 4h: {vol_4h:+.1f}%")
        else:
            crveni.append(f"❌ Vol 4h: {vol_4h:+.1f}% (treba >30%)")
    else:
        crveni.append("❌ Vol 4h: N/A")

    # 3. Price 7d% od -50% do +10%
    if price_7d_pct is not None:
        if -50 <= price_7d_pct <= 10:
            zeleni.append(f"✅ Price 7d: {price_7d_pct:+.2f}%")
        else:
            crveni.append(f"❌ Price 7d: {price_7d_pct:+.2f}% (van -50/+10)")

    # 4. Price 24h% od -5% do +10%
    if price_24h_pct is not None:
        if -5 <= price_24h_pct <= 10:
            zeleni.append(f"✅ Price 24h: {price_24h_pct:+.2f}%")
        else:
            crveni.append(f"❌ Price 24h: {price_24h_pct:+.2f}% (van -5/+10)")

    # 5. Top Trader Positions > 1.1
    tt_pos = futures_data.get("top_trader_position_ratio")
    if tt_pos is not None:
        if tt_pos > 1.1:
            zeleni.append(f"✅ Top Trader Pos: {tt_pos:.3f}")
        else:
            crveni.append(f"❌ Top Trader Pos: {tt_pos:.3f} (treba >1.1)")
    else:
        crveni.append("❌ Top Trader Pos: N/A")

    # 6. Retail L/S Accounts < 1.2
    retail = futures_data.get("retail_account_ratio")
    if retail is not None:
        if retail < 1.2:
            zeleni.append(f"✅ Retail Accounts: {retail:.3f}")
        else:
            crveni.append(f"❌ Retail Accounts: {retail:.3f} (treba <1.2)")
    else:
        crveni.append("❌ Retail Accounts: N/A")

    prolazi = len(crveni) == 0
    return prolazi, zeleni, crveni
