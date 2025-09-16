import os
from dotenv import load_dotenv
import telebot


load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("В .env нет TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я твой первый бот! Напиши /help")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "/start - начать\n/help - помощь\n/about - о боте")

@bot.message_handler(commands=['about'])
def start(message):
    bot.reply_to(message, "Автор: Кобзев Дмитрий Константинович\nВерсия: 1.0.0\nНазначение: Напоминание о делах")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)