import telebot
import os
import requests
from datetime import datetime

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ TOKEN not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "👋 Send /liq for Coinglass Heatmap Alert")

@bot.message_handler(commands=['liq', 'heatmap'])
def send_liq(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, "✅ Bot is working! This is a test message.")

print("✅ Bot running")
bot.infinity_polling()
