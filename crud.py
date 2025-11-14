import os
from dotenv import load_dotenv
import telebot
import time
from datetime import datetime, timedelta
from db import init_db, add_note, list_notes, update_note, delete_note, find_notes, count_notes

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("В .env файле нет TOKEN")

bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных при запуске
init_db()

# Максимальное количество заметок на пользователя
MAX_NOTES_PER_USER = 50


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
/note_count - Показать количество заметок
/note_export - Экспортировать заметки в файл
/note_stats - Статистика активности за неделю
"""
    bot.reply_to(message, help_text)


@bot.message_handler(commands=['note_add'])
def note_add(message):
    user_id = message.from_user.id

    # Проверка лимита заметок
    if count_notes(user_id) >= MAX_NOTES_PER_USER:
        bot.reply_to(message,
                     f"Ошибка: Превышен лимит в {MAX_NOTES_PER_USER} заметок. Удалите некоторые заметки перед добавлением новых.")
        return

    text = message.text.replace('/note_add', '').strip()
    if not text:
        bot.reply_to(message, "Ошибка: Укажите текст заметки.")
        return

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


@bot.message_handler(commands=['note_count'])
def note_count(message):
    user_id = message.from_user.id
    notes_count = count_notes(user_id)
    remaining = MAX_NOTES_PER_USER - notes_count
    bot.reply_to(message, f"У вас {notes_count} заметок. Осталось места для {remaining} заметок.")


@bot.message_handler(commands=['note_export'])
def note_export(message):
    user_id = message.from_user.id
    user_notes = list_notes(user_id)

    if not user_notes:
        bot.reply_to(message, "Нет заметок для экспорта.")
        return

    # Создаем имя файла с timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notes_{user_id}_{timestamp}.txt"

    # Записываем заметки в файл
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Экспорт заметок пользователя {user_id}\n")
        f.write(f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Всего заметок: {len(user_notes)}\n")
        f.write("=" * 50 + "\n\n")

        for note in user_notes:
            f.write(f"Заметка #{note['id']}:\n")
            f.write(f"{note['text']}\n")
            f.write("-" * 30 + "\n")

    # Отправляем файл пользователю
    with open(filename, 'rb') as f:
        bot.send_document(message.chat.id, f, caption="Ваши экспортированные заметки")

    # Удаляем временный файл
    os.remove(filename)


@bot.message_handler(commands=['note_stats'])
def note_stats(message):
    user_id = message.from_user.id

    # Получаем статистику за последние 7 дней
    stats = get_weekly_stats(user_id)

    if not stats:
        bot.reply_to(message, "Недостаточно данных для построения статистики.")
        return

    # Создаем ASCII гистограмму
    chart = create_ascii_chart(stats)

    response = f"Статистика активности за неделю:\n\n{chart}"
    bot.reply_to(message, response)


def get_weekly_stats(user_id):
    """Получает статистику заметок за последние 7 дней"""
    conn = sqlite3.connect('notes.db')
    cursor = conn.cursor()

    # Получаем дату 7 дней назад
    week_ago = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')

    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count 
        FROM notes 
        WHERE user_id = ? AND created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (user_id, week_ago))

    result = cursor.fetchall()
    conn.close()

    # Создаем словарь для всех дней недели
    stats = {}
    for i in range(7):
        date = (datetime.now() - timedelta(days=6 - i)).strftime('%Y-%m-%d')
        stats[date] = 0

    # Заполняем реальными данными
    for date, count in result:
        stats[date] = count

    return stats


def create_ascii_chart(stats):
    """Создает ASCII гистограмму из статистики"""
    max_count = max(stats.values()) if stats else 1

    chart_lines = []
    for date, count in stats.items():
        # Форматируем дату
        day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%a')
        short_date = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m')

        # Создаем строку гистограммы
        bar_length = int((count / max_count) * 20) if max_count > 0 else 0
        bar = '█' * bar_length

        chart_lines.append(f"{day_name} ({short_date}): {bar} {count}")

    return "\n".join(chart_lines)


if __name__ == "__main__":
    print("Бот запускается...")
    bot.infinity_polling()