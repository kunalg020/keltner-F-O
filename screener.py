
# screener.py
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import pytz
import os

DHAN_API_KEY = os.getenv("DHAN_API_KEY")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def is_trading_hours():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start <= now <= end

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

def fetch_ohlcv_dhan(symbol, interval="1d", limit=100):
    try:
        url = f"https://api.dhan.co/market/v1/chart/intraday/{symbol}/NSE/{interval}?limit={limit}"
        headers = {
            "accept": "application/json",
            "access-token": DHAN_API_KEY,
            "client-id": DHAN_CLIENT_ID
        }
        response = requests.get(url, headers=headers)
        candles = response.json().get("data", [])
        df = pd.DataFrame(candles, columns=["datetime", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}:", e)
        return pd.DataFrame()

def get_nifty_50_and_fno_symbols():
    try:
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.nseindia.com/"}
        session.get("https://www.nseindia.com", headers=headers)

        nifty_data = session.get("https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050", headers=headers).json()["data"]
        fno_data = session.get("https://www.nseindia.com/api/liveEquity-derivatives", headers=headers).json()["data"]

        nifty_symbols = [item["symbol"] for item in nifty_data]
        fno_symbols = list(set(item["underlying"] for item in fno_data))
        return sorted(set(nifty_symbols + fno_symbols))
    except Exception as e:
        print("Error fetching symbols:", e)
        return []

def meets_criteria(symbol):
    try:
        df_daily = fetch_ohlcv_dhan(symbol, "1d")
        df_1h = fetch_ohlcv_dhan(symbol, "1h")

        if df_daily.empty or df_1h.empty:
            return False

        df_daily.ta.ema(length=88, append=True)
        df_daily.ta.rsi(length=14, append=True)
        df_daily.ta.kc(length=21, scalar=1.0, append=True)

        last = df_daily.iloc[-1]
        if (last["close"] < last["KC_Upper_21_1.0"] or last["close"] < last["EMA_88"] or last["RSI_14"] < 60):
            return False

        df_1h.ta.rsi(length=14, append=True)
        df_1h.ta.kc(length=21, scalar=1.0, append=True)

        prices = df_1h["close"]
        kc_upper = df_1h["KC_Upper_21_1.0"]
        kc_middle = df_1h["KC_Mid_21_1.0"]
        rsi = df_1h["RSI_14"]

        for i in range(len(df_1h) - 3):
            p1, p2, p3 = prices[i], prices[i+1], prices[i+2]
            u1, u2, u3 = kc_upper[i], kc_upper[i+1], kc_upper[i+2]
            m2 = kc_middle[i+1]
            r1, r2, r3 = rsi[i], rsi[i+1], rsi[i+2]
            if (p1 > u1 and p2 < m2 and p3 > u3 and r1 > 60 and 50 <= r2 < 60 and r3 > 60):
                return True
    except Exception as e:
        print(f"Error in {symbol}: {e}")
    return False

def run_screener():
    print("🔍 Running Screener...")
    matched = []
    symbols = get_nifty_50_and_fno_symbols()
    for symbol in symbols:
        if meets_criteria(symbol):
            matched.append(symbol)
    if matched:
        msg = "🔔 *Screener Alerts (Nifty 50 + F&O):*
" + "\n".join(matched)
        send_telegram_alert(msg)
    else:
        print("No matches today.")

if __name__ == "__main__":
    if is_trading_hours():
        run_screener()
    else:
        print("⏰ Outside trading hours. Skipping.")
