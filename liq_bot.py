import telebot
import os
import requests
from datetime import datetime
from threading import Thread
from flask import Flask
import schedule
import time

app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7 with real-time public data!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

def get_public_liquidation_data():
    try:
        # Get real-time prices from CoinGecko
        price_url = "https://api.coingecko.com/api/v3/coins/markets"
        price_params = {"vs_currency": "usd", "order": "volume_desc", "per_page": 50, "page": 1}
        price_data = requests.get(price_url, params=price_params, timeout=12).json()
        price_map = {coin['symbol'].upper(): coin['current_price'] for coin in price_data}

        # Get real-time futures data from Binance (public)
        binance_url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        binance_data = requests.get(binance_url, timeout=10).json()

        # Filter top coins by volume (proxy for high liquidity/liquidation potential)
        top_coins = sorted(binance_data, key=lambda x: float(x['quoteVolume']), reverse=True)[:15]

        now = datetime.now().strftime("%d %B %Y, %H:%M IST")
        msg = f"🔥 **15-Min Real-Time Liquidation Alert** - {now}\n\n"

        for i, coin in enumerate(top_coins, 1):
            symbol = coin['symbol'].replace('USDT', '')
            price = price_map.get(symbol, 0)
            volume = float(coin['quoteVolume'])
            price_change = float(coin['priceChangePercent'])

            # Estimate liquidation potential based on volume + price movement
            if abs(price_change) > 5:
                bias = "🔥 **HIGH LIQUIDATION RISK**"
                tp_pct = 10
            elif abs(price_change) > 2:
                bias = "⚡ **MEDIUM LIQUIDATION RISK**"
                tp_pct = 8
            else:
                bias = "📊 **NORMAL**"
                tp_pct = 6

            entry = price
            sl = round(price * 0.985, 4) if price else 0
            tp = round(price * (1 + tp_pct/100), 4) if price else 0

            msg += f"{i}. **{symbol}** (~${price:,.4f})\n"
            msg += f"   24h Volume: ${volume:,.0f} | {bias}\n"
            msg += f"   Entry: ~${entry:,.4f} | SL: ~${sl:,.4f} | TP: ~${tp:,.4f} (+{tp_pct}%)\n\n"

        msg += "Data: CoinGecko + Binance Public API"
        return msg

    except Exception as e:
        return f"❌ Error: {e}"

def send_alert():
    text = get_public_liquidation_data()
    bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
    print("✅ Real-time alert sent!")

schedule.every(15).minutes.do(send_alert)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

Thread(target=run_schedule, daemon=True).start()
keep_alive()

print("✅ BEST PUBLIC VERSION running 24/7!")
bot.infinity_polling()
