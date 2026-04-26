import os
import time
import requests
import telebot
import schedule
import threading
from datetime import datetime

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CG_API_KEY = os.getenv("COINGLASS_API_KEY")

if not TOKEN:
    print("❌ TOKEN not set!")
    exit(1)
if not CHAT_ID:
    print("❌ CHAT_ID not set!")
    exit(1)
if not CG_API_KEY:
    print("❌ COINGLASS_API_KEY not set!")
    exit(1)

print("✅ All env vars set! Starting bot...")

bot = telebot.TeleBot(TOKEN)
CG_BASE = "https://open-api-v4.coinglass.com"
CG_HEADERS = {"CG-API-KEY": CG_API_KEY, "accept": "application/json"}

# Top 15 coins to track
COINS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX", 
         "LINK", "DOT", "MATIC", "LTC", "TRX", "SHIB", "UNI"]

# ===== COINGLASS API HELPERS =====
def cg_get(path, params=None):
    """Generic Coinglass API call with error handling"""
    try:
        url = f"{CG_BASE}{path}"
        r = requests.get(url, headers=CG_HEADERS, params=params or {}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == "0" or data.get("success") == True:
                return data.get("data", [])
        print(f"⚠️ API {path}: status={r.status_code}, body={r.text[:200]}")
        return None
    except Exception as e:
        print(f"❌ Error calling {path}: {e}")
        return None

def get_price_and_oi(symbol):
    """Get current price and 24h OI change"""
    data = cg_get("/api/futures/openInterest/exchange-list", {"symbol": symbol})
    if not data:
        return None
    # Aggregate data across exchanges
    try:
        total = next((x for x in data if x.get("exchange", "").lower() == "all"), None)
        if total:
            return {
                "price": float(total.get("price", 0)),
                "oi_usd": float(total.get("openInterestUsd", 0)),
                "oi_change_24h": float(total.get("openInterestAmountChangePercent24h", 0) or 0),
            }
    except Exception as e:
        print(f"⚠️ Parse error {symbol}: {e}")
    return None

def get_long_short_ratio(symbol):
    """Get long/short ratio"""
    data = cg_get("/api/futures/globalLongShortAccountRatio/history", 
                  {"symbol": symbol, "interval": "15m", "limit": 1})
    if data and len(data) > 0:
        try:
            latest = data[-1] if isinstance(data, list) else data
            return float(latest.get("longShortRatio", 1))
        except:
            pass
    return None

def get_funding_rate(symbol):
    """Get current funding rate"""
    data = cg_get("/api/futures/fundingRate/exchange-list", {"symbol": symbol})
    if data:
        try:
            rates = [float(x.get("fundingRate", 0)) for x in data if x.get("fundingRate")]
            if rates:
                return sum(rates) / len(rates) * 100  # avg, in %
        except:
            pass
    return None

def get_liquidation_24h(symbol):
    """Get 24h liquidation total"""
    data = cg_get("/api/futures/liquidation/coin-list")
    if data and isinstance(data, list):
        for item in data:
            if item.get("symbol", "").upper() == symbol.upper():
                try:
                    return float(item.get("liquidationUsd24h", 0))
                except:
                    pass
    return None

# ===== SIGNAL LOGIC =====
def analyze_coin(symbol):
    """Returns dict with all data and a LONG/SHORT signal"""
    info = get_price_and_oi(symbol)
    if not info or info["price"] == 0:
        return None
    
    time.sleep(0.3)  # avoid rate limit
    ls_ratio = get_long_short_ratio(symbol)
    time.sleep(0.3)
    funding = get_funding_rate(symbol)
    time.sleep(0.3)
    liq_24h = get_liquidation_24h(symbol)
    
    # Decide direction based on multiple signals
    score = 0
    if info["oi_change_24h"] > 2: score += 1
    if info["oi_change_24h"] < -2: score -= 1
    if ls_ratio and ls_ratio > 1.1: score -= 1   # too many longs = SHORT signal (contrarian)
    if ls_ratio and ls_ratio < 0.9: score += 1   # too many shorts = LONG signal
    if funding and funding > 0.03: score -= 1     # high funding = overheated longs
    if funding and funding < -0.01: score += 1    # negative funding = shorts paying
    
    direction = "LONG" if score >= 0 else "SHORT"
    
    # Strength
    abs_score = abs(score)
    if abs_score >= 3: strength = "Very Strong"
    elif abs_score == 2: strength = "Strong"
    else: strength = "Moderate"
    
    # Calculate Entry, SL, TP
    price = info["price"]
    if direction == "LONG":
        entry = price
        sl = round(price * 0.985, 6)   # -1.5%
        tp = round(price * 1.12, 6)    # +12%
        emoji = "🟢"
    else:
        entry = price
        sl = round(price * 1.015, 6)   # +1.5%
        tp = round(price * 0.88, 6)    # -12%
        emoji = "🔴"
    
    return {
        "symbol": symbol, "price": price, "direction": direction,
        "emoji": emoji, "strength": strength,
        "entry": entry, "sl": sl, "tp": tp,
        "liq_24h": liq_24h or 0,
        "oi_usd": info["oi_usd"], "oi_change": info["oi_change_24h"],
        "ls_ratio": ls_ratio, "funding": funding,
    }

# ===== BUILD ALERT =====
def fmt(n, decimals=4):
    if n is None: return "N/A"
    if n >= 1: return f"{n:,.{decimals}f}"
    return f"{n:.6f}"

def build_alert():
    now = datetime.now().strftime("%d %b %Y, %H:%M IST")
    msg = f"<b>🔥 15-Min Coinglass Heatmap Alert - {now}</b>\n\n"
    
    success = 0
    for i, sym in enumerate(COINS, 1):
        print(f"  Processing {sym}...")
        d = analyze_coin(sym)
        if not d:
            continue
        success += 1
        
        msg += f"<b>{i}. {d['emoji']} {sym}</b> (~${fmt(d['price'])})\n"
        msg += f"  24h Liq: ${d['liq_24h']:,.0f} | <b>MAX PROFIT {d['direction']}</b> ({d['strength']})\n"
        msg += f"  OI: ${d['oi_usd']/1e6:,.1f}M | OI 24h Δ: {d['oi_change']:+.2f}%\n"
        if d['ls_ratio']:
            msg += f"  L/S Ratio: {d['ls_ratio']:.2f}"
        if d['funding'] is not None:
            msg += f" | Funding: {d['funding']:+.4f}%"
        msg += "\n"
        msg += f"  Entry: ${fmt(d['entry'])} | SL: ${fmt(d['sl'])} (1.5%)\n"
        msg += f"  TP: ${fmt(d['tp'])} → <b>MAX PROFIT: +12%</b>\n\n"
        
        time.sleep(0.5)  # rate limit safety between coins
    
    msg += f"<i>✅ Processed {success}/{len(COINS)} coins</i>\n"
    msg += "<i>⚠️ Educational only. DYOR. Not financial advice.</i>"
    return msg

# ===== SEND ALERT =====
def send_alert():
    print(f"\n📤 Building alert at {datetime.now().strftime('%H:%M:%S')}")
    try:
        message = build_alert()
        # Telegram 4096 char limit - split if needed
        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                bot.send_message(CHAT_ID, part, parse_mode="HTML")
                time.sleep(1)
        else:
            bot.send_message(CHAT_ID, message, parse_mode="HTML")
        print("✅ Alert sent!")
    except Exception as e:
        print(f"❌ Send error: {e}")

# ===== TELEGRAM COMMANDS =====
@bot.message_handler(commands=['start', 'test'])
def start_cmd(m):
    bot.reply_to(m, "✅ Bot running! Real Coinglass alerts every 15 min.\n\nCommands:\n/now - Send alert now\n/chatid - Show chat ID")

@bot.message_handler(commands=['now'])
def now_cmd(m):
    bot.reply_to(m, "📤 Building alert... wait ~1 min")
    send_alert()

@bot.message_handler(commands=['chatid'])
def chatid_cmd(m):
    bot.reply_to(m, f"Chat ID: <code>{m.chat.id}</code>", parse_mode="HTML")

# ===== SCHEDULER =====
def run_scheduler():
    schedule.every(15).minutes.do(send_alert)
    print("⏰ Scheduler: alerts every 15 min")
    while True:
        schedule.run_pending()
        time.sleep(30)

# ===== START =====
print("🔧 Removing old webhook...")
bot.remove_webhook()
time.sleep(2)

print("📤 Sending startup alert...")
send_alert()

print("🚀 Starting scheduler...")
threading.Thread(target=run_scheduler, daemon=True).start()

print("👂 Polling Telegram...")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
