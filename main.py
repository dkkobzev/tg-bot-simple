import os
from dotenv import load_dotenv
from telebot import *
from typing import List
import logging
import requests

load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("В .env нет TOKEN")

bot = telebot.TeleBot(TOKEN)

#Базовая настройка логирования
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s'
)


def fetch_weather_moscow_open_meteo() -> str:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 55.6551186,
        "longitude": 37.5009639,
        "current": "temperature_2m",
        "timezone": "Europe/Moscow"
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        t = r.json()["current"]["temperature_2m"]
        return f"В Москве сейчас {round(t)}°C"
    except Exception:
        return "Не удалось получить погоду."

def parse_ints_from_text(text: str) -> List[int]:
    """Выделяет из текста целые числа: нормализует запятые, игнорирует токены-команды."""
    text = text.replace(",", " ")
    tokens = [tok for tok in text.split() if not tok.startswith("/")]
    return [int(tok) for tok in tokens if is_int_token(tok)]

def is_int_token(t: str) -> bool:
    """Проверка токена на целое число (с поддержкой знака минус)."""
    if not t:
        return False
    t = t.strip()
    if t in {"-", ""}:
        return False
    return t.lstrip("-").isdigit()


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я твой первый бот! Напиши /help", reply_markup=make_main_kb())

def make_main_kb() -> types.ReplyKeyboardMarkup: #Создание клавиатуры
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("Максимум", "Сумма")
    kb.row("/help", "/about")
    kb.row("/hide", "/show")
    kb.row("Погода", '/confirm')

    return kb


@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "/start - начать\n/help - помощь\n/about - о боте\nСумма - суммирование чисел\n/hide - спрятать клавиатуру")


@bot.message_handler(func=lambda m: m.text == "Погода")
def weather(m):
    bot.reply_to(m, fetch_weather_moscow_open_meteo())


@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(message, "Автор: Кобзев Дмитрий Константинович\nВерсия: 1.0.0\nНазначение: Напоминание о делах")

    
@bot.message_handler(func=lambda m: m.text == "Сумма")
def kb_sum(m):
    bot.send_message(m.chat.id, "Введи числа через пробел или запятую:")
    bot.register_next_step_handler(m, on_sum_numbers)

def on_sum_numbers(m: types.Message) -> None:
    nums = parse_ints_from_text(m.text)
    logging.info("KB-sum next step from id=%s text=%r -> %r", m.from_user.id if m.from_user else "?", m.text, nums) #Логируем входящую команду
    logging.info(f'распознаны числа: {nums}') #Логируем результат парсинга
    if not nums:
        bot.reply_to(m, "Не вижу чисел. Пример: 2 3 10")
    else:
        bot.reply_to(m, f"Сумма: {sum(nums)}")


@bot.message_handler(func=lambda m: m.text == "Максимум")
def kb_max(m):
    bot.send_message(m.chat.id, "Введи числа через пробел или запятую:")
    bot.register_next_step_handler(m, max_numbers)

def max_numbers(m: types.Message) -> None:
    nums = parse_ints_from_text(m.text)
    logging.info("KB-max next step from id=%s text=%r -> %r", m.from_user.id if m.from_user else "?", m.text, nums)
    logging.info(f'распознаны числа: {nums}')
    if not nums:
        bot.reply_to(m, "Не вижу чисел. Пример: 2 3 10")
    else:
        bot.reply_to(m, f"Максимум: {max(nums)}")


@bot.message_handler(commands=['hide'])
def hide_kb(m):
    rm = types.ReplyKeyboardRemove()
    bot.send_message(m.chat.id, 'Спрятал клавиатуру', reply_markup=rm)

@bot.message_handler(commands=['show'])
def hide_kb(m):
    bot.send_message(m.chat.id, 'Открыл клавиатуру', reply_markup=make_main_kb())
        

@bot.message_handler(commands=['confirm'])
def confirm_cmd(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton('Да', callback_data='confirm:yes'),
        types.InlineKeyboardButton('Нет', callback_data='confirm:no'),
    )
    bot.send_message(m.chat.id, 'Подтвердить действие?', reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm:"))
def on_confirm(c):
    #Извлекаем выбор пользователя
    choice = c.data.split(':', 1)[1] #yes или no

    #Показываем "тик" на нажатой кнопке
    bot.answer_callback_query(c.id, 'Принято')

    #Убираем inline-кнопки
    bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)

    #Отправляем результат
    bot.send_message(c.message.chat.id, 'Готово!' if choice == 'yes' else 'Отменено')

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)