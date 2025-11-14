import os
from dotenv import load_dotenv
import telebot
from db import init_db, add_note, list_notes, update_note, delete_note#, find_notes

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("В .env файле нет TOKEN")

bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных при запуске
init_db()

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот для заметок. Используй /help для списка команд.")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = """
Доступные команды:
/note_add <текст> - Добавить заметку
/note_list - Показать все заметки
/note_find <запрос> - Найти заметку
/note_edit <id> <новый текст> - Изменить заметку
/note_del <id> - Удалить заметку
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['note_add'])
def note_add(message):
    text = message.text.replace('/note_add', '').strip()
    if not text:
        bot.reply_to(message, "Ошибка: Укажите текст заметки.")
        return
    
    user_id = message.from_user.id
    note_id = add_note(user_id, text)
    bot.reply_to(message, f"Заметка #{note_id} добавлена: {text}")

@bot.message_handler(commands=['note_list'])
def note_list(message):
    user_id = message.from_user.id
    user_notes = list_notes(user_id)
    
    if not user_notes:
        bot.reply_to(message, "Заметок пока нет.")
        return
    
    response = "Ваши заметки:\n" + "\n".join([f"{note['id']}: {note['text']}" for note in user_notes])
    bot.reply_to(message, response)

@bot.message_handler(commands=['note_find'])
def note_find(message):
    query = message.text.replace('/note_find', '').strip()
    if not query:
        bot.reply_to(message, "Ошибка: Укажите поисковый запрос.")
        return
    
    user_id = message.from_user.id
    found_notes = find_notes(user_id, query)
    
    if not found_notes:
        bot.reply_to(message, "Заметки не найдены.")
        return
    
    response = "Найденные заметки:\n" + "\n".join([f"{note['id']}: {note['text']}" for note in found_notes])
    bot.reply_to(message, response)

@bot.message_handler(commands=['note_edit'])
def note_edit(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "Ошибка: Используйте /note_edit <id> <новый текст>")
        return
    
    try:
        note_id = int(parts[1])
        new_text = parts[2]
    except ValueError:
        bot.reply_to(message, "Ошибка: ID должен быть числом.")
        return
    
    user_id = message.from_user.id
    success = update_note(user_id, note_id, new_text)
    
    if not success:
        bot.reply_to(message, f"Ошибка: Заметка #{note_id} не найдена или у вас нет прав для её изменения.")
        return
    
    bot.reply_to(message, f"Заметка #{note_id} изменена на: {new_text}")

@bot.message_handler(commands=['note_del'])
def note_del(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Ошибка: Укажите ID заметки для удаления.")
        return
    
    try:
        note_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Ошибка: ID должен быть числом.")
        return
    
    user_id = message.from_user.id
    success = delete_note(user_id, note_id)
    
    if not success:
        bot.reply_to(message, f"Ошибка: Заметка #{note_id} не найдена или у вас нет прав для её удаления.")
        return
    
    bot.reply_to(message, f"Заметка #{note_id} удалена.")

if __name__ == "__main__":
    print("Бот запускается...")
    bot.infinity_polling()