import telebot
import os
import time
import threading
from datetime import datetime
import schedule

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ TOKEN environment variable is not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# Your chat ID - Replace this with your actual Telegram chat ID
# How to get it: Send /start to the bot, then check logs or use @userinfobot
YOUR_CHAT_ID = 123456789   # ← CHANGE THIS TO YOUR CHAT ID

def get_liq_message():
    now = datetime.now().strftime("%d %B %Y, %H:%M IST")
    msg = f"🔥 **Daily Liquidation Heatmap Alert** - {now}\n\n"
    msg += "1. **HYPER** (~$0.17)\n   SL: 8-12% below | TP1: 15-25% | TP2: 35-50%+\n\n"
    msg += "2. **APE** (~$0.19)\n   SL: 8-10% below | TP1: 18-25% | TP2: 35-45%\n\n"
    msg += "3. **BNB**\n   SL: Below recent low | TP1: Next resistance\n\n"
    msg += "4. **AXS**\n   SL: 5-8% tight | TP1: 12-18%\n\n"
    msg += "5. **ORCA**\n   SL: 7-10% below | TP1: 15-22%\n\n"
    msg += "6. **BSB** (~$0.66)\n   SL: 8-12% below | TP1: 15-25% | TP2: 35-50%\n   🔥 High activity now!\n\n"
    msg += "7. **TRUMP**\n   SL: 12-15% below | TP1: 25-40%\n\n"
    msg += "8. **KAT**\n   SL: 5-8% tight | TP: 15-30%\n\n"
    msg += "9. **BTC** (~$77,650)\n   SL: $76,800 | TP1: $79,500 | TP2: $81,300\n\n"
    msg += "10. **ETH** (~$2,317)\n   SL: $2,250 | TP1: $2,400 | TP2: $2,550\n\n"
    msg += "⚠️ Heatmap changes fast. Always verify on Coinglass.\n"
    msg += "https://www.coinglass.com/pro/futures/LiquidationHeatMap"
    return msg

# Function to send daily alert
def send_daily_alert():
    try:
        text = get_liq_message()
        bot.send_message(YOUR_CHAT_ID, text, parse_mode='Markdown')
        print(f"✅ Daily alert sent at {datetime.now().strftime('%H:%M IST')}")
    except Exception as e:
        print(f"❌ Failed to send daily alert: {e}")

# Manual commands
@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "👋 Send /liq for instant Top 10.\nDaily alert will be sent every day at 8:00 PM IST.")

@bot.message_handler(commands=['liq', 'heatmap'])
def send_liq(message):
    bot.send_chat_action(message.chat.id, 'typing')
    text = get_liq_message()
    bot.reply_to(message, text, parse_mode='Markdown')

# Schedule the daily alert at 8:00 PM IST
schedule.every().day.at("20:00").do(send_daily_alert)

# Run scheduler in background thread
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)   # Check every minute

# Start scheduler in a separate thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

print("✅ Bot is running... Daily alert scheduled at 8:00 PM IST")
bot.infinity_polling()
