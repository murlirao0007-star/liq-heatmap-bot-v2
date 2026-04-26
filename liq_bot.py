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
    return "Bot is running 24/7!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

TOKEN = os.getenv("TOKEN")
COINGLASS_KEY = os.getenv("COINGLASS_KEY")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

def get_heatmap_coins():
    try:
        url = "https://open-api-v4.coinglass.com/api/futures/liquidation/coin-list"
        headers = {"cg-api-key": COINGLASS_KEY} if COINGLASS_KEY else {}
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json().get('data', [])

        if not data:
            return "❌ No data from Coinglass right now."

        for coin in data:
            coin['total_liq_1h'] = (coin.get('long_liquidation_usd_1h') or 0) + (coin.get('short_liquidation_usd_1h') or 0)

        data = sorted(data, key=lambda x: x.get('total_liq_1h', 0), reverse=True)[:12]

        price_url = "https://api.coingecko.com/api/v3/coins/markets"
        price_params = {"vs_currency": "usd", "order": "volume_desc", "per_page": 100, "page": 1}
        price_data = requests.get(price_url, params=price_params, timeout=12).json()
        price_map = {coin['symbol'].upper(): coin['current_price'] for coin in price_data}

        now = datetime.now().strftime("%d %B %Y, %H:%M IST")
        msg = f"🔥 **15-Min Coinglass Heatmap Alert** - {now}\n\n"

        for i, coin in enumerate(data, 1):
            symbol = coin.get('symbol', 'N/A')
            price = price_map.get(symbol, 0)
            long_liq = coin.get('long_liquidation_usd_1h') or coin.get('long_liquidation_usd_24h', 0)
            short_liq = coin.get('short_liquidation_usd_1h') or coin.get('short_liquidation_usd_24h', 0)
            total_liq = long_liq + short_liq

            if short_liq > long_liq * 1.8:
                sl_pct = 1.5
                tp_pct = 12
                bias = "🔥 **MAX PROFIT LONG** (Very Strong)"
            elif long_liq > short_liq * 1.8:
                sl_pct = 1.5
                tp_pct = 12
                bias = "🔻 **MAX PROFIT SHORT** (Very Strong)"
            else:
                sl_pct = 1.5
                tp_pct = 12
                bias = "⚖️ MAX PROFIT"

            entry = price
            sl = round(price * (1 - sl_pct/100), 4) if price else 0
            tp = round(price * (1 + tp_pct/100), 4) if price else 0

            msg += f"{i}. **{symbol}** (~${price:,.4f}) | {bias}\n"
            msg += f"   1h Liq: ${total_liq:,.0f}\n"
            msg += f"   Entry: ~${entry:,.4f} | SL: ~${sl:,.4f} ({sl_pct}% risk)\n"
            msg += f"   TP: ~${tp:,.4f} → **MAX PROFIT: +{tp_pct}%**\n\n"

        msg += "Live: https://www.coinglass.com/pro/futures/LiquidationHeatMap"
        return msg

    except Exception as e:
        return f"❌ Error: {e}"

def send_alert():
    text = get_heatmap_coins()
    bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
    print("✅ Alert sent!")

schedule.every(15).minutes.do(send_alert)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

Thread(target=run_schedule, daemon=True).start()
keep_alive()

print("✅ FINAL Bot running 24/7 with exact format!")
bot.infinity_polling()
