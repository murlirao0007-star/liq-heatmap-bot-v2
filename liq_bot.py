import telebot
import os
import time
import threading
from datetime import datetime
import schedule
import requests

TOKEN = os.getenv("TOKEN")
COINGLASS_KEY = os.getenv("8b5e8e90d5824aada5164b1364c77c1f")

if not TOKEN:
    print("❌ TOKEN not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

YOUR_CHAT_ID = 17219470795   # ← CHANGE THIS

headers = {"cg-api-key": COINGLASS_KEY} if COINGLASS_KEY else {}

def get_full_coinglass_data():
    try:
        # Coinglass Liquidation Coin List (the coins in heatmap)
        liq_url = "https://open-api-v4.coinglass.com/api/futures/liquidation/coin-list"
        liq_response = requests.get(liq_url, headers=headers, timeout=15)
        liq_data = liq_response.json().get('data', [])[:12]

        # CoinGecko for accurate price
        price_url = "https://api.coingecko.com/api/v3/coins/markets"
        price_params = {"vs_currency": "usd", "order": "volume_desc", "per_page": 50, "page": 1}
        price_data = requests.get(price_url, params=price_params, timeout=12).json()
        price_map = {coin['symbol'].upper(): coin['current_price'] for coin in price_data}

        now = datetime.now().strftime("%d %B %Y, %H:%M IST")
        msg = f"🔥 **15-Min Full Coinglass Alert** - {now}\n\n"

        for i, coin in enumerate(liq_data[:10], 1):
            symbol = coin.get('symbol', 'N/A')
            price = price_map.get(symbol, 0)
            long_liq = coin.get('long_liquidation_usd_24h', 0)
            short_liq = coin.get('short_liquidation_usd_24h', 0)
            total_liq = long_liq + short_liq

            entry = price
            sl = round(price * 0.92, 4) if price else 0
            tp = round(price * 1.18, 4) if price else 0

            msg += f"{i}. **{symbol}** (~${price:,.4f})\n"
            msg += f"   24h Liq: ${total_liq:,.0f} (Long: ${long_liq:,.0f} | Short: ${short_liq:,.0f})\n"
            msg += f"   Entry: ~${entry:,.4f} | SL: ~${sl:,.4f} | TP: ~${tp:,.4f}\n\n"

        msg += "⚠️ Data: Coinglass Liquidation + CoinGecko Price\n"
        msg += "Live Heatmap: https://www.coinglass.com/pro/futures/LiquidationHeatMap"
        return msg

    except Exception as e:
        return f"❌ Error: {e}"

def send_alert():
    text = get_full_coinglass_data()
    bot.send_message(YOUR_CHAT_ID, text, parse_mode='Markdown')

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "👋 /liq = Full Coinglass data (Price + Liq)\nAlerts every 15 min + 8 PM IST daily.")

@bot.message_handler(commands=['liq', 'heatmap'])
def send_liq(message):
    bot.send_chat_action(message.chat.id, 'typing')
    text = get_full_coinglass_data()
    bot.reply_to(message, text, parse_mode='Markdown')

# Scheduler
schedule.every(15).minutes.do(send_alert)
schedule.every().day.at("20:00").do(send_alert)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=run_scheduler, daemon=True).start()

print("✅ Bot running - Full Coinglass data (Price + Liquidation)")
bot.infinity_polling()
