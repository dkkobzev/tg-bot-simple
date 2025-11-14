import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import List, Optional

DB_PATH = os.getenv("DB_PATH", "bot.db")

@contextmanager
def _connect():
    """Контекстный менеджер для работы с базой данных"""
    conn = sqlite3.connect('notes.db')
    conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Инициализация базы данных - создание таблицы, если она не существует"""
    with _connect() as conn:
        cursor = conn.cursor()

        # Создаем таблицу с правильной структурой
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY,
                key TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0,1))
            )
        ''')

        # Добавляем уникальный индекс для ограничения только одной активной модели
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS ux_models_single_active 
            ON models(active) WHERE active=1;
        ''')

        # Создаем таблицу notes (если её еще нет)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # СОЗДАНИЕ ТАБЛИЦЫ ДЛЯ ХРАНЕНИЯ ПЕРСОНАЖЕЙ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                prompt TEXT NOT NULL
            )
        ''')

        # СОЗДАНИЕ ТАБЛИЦЫ СВЯЗЕЙ ПОЛЬЗОВАТЕЛЕЙ И ПЕРСОНАЖЕЙ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_character (
                telegram_user_id INTEGER PRIMARY KEY,
                character_id INTEGER NOT NULL,
                FOREIGN KEY(character_id) REFERENCES characters(id)
            )
        ''')

        # Добавляем начальные данные моделей
        cursor.execute('''
            INSERT OR IGNORE INTO models(id, key, label, active) VALUES
            (1, 'deepseek/deepseek-chat-v3.1:free', 'DeepSeek V3.1 (free)', 1),
            (2, 'deepseek/deepseek-r1:free', 'DeepSeek R1 (free)', 0),
            (3, 'mistralai/mistral-small-24b-instruct-2501:free', 'Mistral Small 24b (free)', 0),
            (4, 'meta-llama/llama-3.1-8b-instruct:free', 'Llama 3.1 8B (free)', 0)
        ''')

        # ДОБАВЛЯЕМ ПЕРСОНАЖЕЙ И ИХ ПРОМПТЫ
        cursor.execute('''
            INSERT OR IGNORE INTO characters(id, name, prompt) VALUES
            (1, 'Иода', 'Ты отвечаешь строго в образе персонажа «Иода» из вселенной «Звёздные войны». Стиль речи: мудро, загадочно, короткими фразами, с инверсией порядка слов.'),
            (2, 'Дарт Вейдер', 'Ты отвечаешь строго в образе персонажа «Дарт Вейдер» из «Звёздных войн». Стиль: властно, угрожающе, с имперским величием.'),
            (3, 'Мистер Спок', 'Ты отвечаешь строго в образе персонажа «Спок» из «Звёздного пути». Стиль: логично, рационально, без эмоций, с вулканской мудростью.'),
            (4, 'Тони Старк', 'Ты отвечаешь строго в образе персонажа «Тони Старк» из киновселенной Marvel. Стиль: саркастично, остроумно, с техническими метафорами.'),
            (5, 'Шерлок Холмс', 'Ты отвечаешь строго в образе «Шерлока Холмса». Стиль: дедукция шаг за шагом, аналитично, проницательно, с британским акцентом.'),
            (6, 'Капитан Джек Воробей', 'Ты отвечаешь строго в образе «Капитана Джека Воробья». Стиль: иронично, эксцентрично, с пиратским юмором и намёками.'),
            (7, 'Гэндальф', 'Ты отвечаешь строго в образе «Гэндальфа» из «Властелина колец». Стиль: мудро, наставительно, с оттенком таинственности и власти.'),
            (8, 'Винни-Пух', 'Ты отвечаешь строго в образе «Винни-Пуха». Стиль: просто, доброжелательно, наивно, с мыслями о мёде и друзьях.'),
            (9, 'Голум', 'Ты отвечаешь строго в образе «Голума» из «Властелина колец». Стиль: шипяще, двусмысленно, с внутренним конфликтом между Смеаголом и Голумом.'),
            (10, 'Рик', 'Ты отвечаешь строго в образе «Рика» из «Рика и Морти». Стиль: цинично, с научным сарказмом, пренебрежением к условностям.'),
            (11, 'Бендер', 'Ты отвечаешь строго в образе «Бендера» из «Футурамы». Стиль: дерзко, саркастично, с роботизированным цинизмом и жаждой наживы.')
        ''')

        conn.commit()


def list_models() -> list[dict]:
    """Получение списка всех моделей"""
    with _connect() as conn:
        rows = conn.execute('SELECT id, key, label, active FROM models ORDER BY id').fetchall()
        return [{'id': r['id'], 'key': r['key'], 'label': r['label'], 'active': bool(r['active'])} for r in rows]


def get_active_model() -> dict:
    """Получение активной модели"""
    with _connect() as conn:
        row = conn.execute('SELECT id, key, label FROM models WHERE active=1').fetchone()
        if row:
            return {'id': row['id'], 'key': row['key'], 'label': row['label'], 'active': True}

        row = conn.execute('SELECT id, key, label FROM models ORDER BY id LIMIT 1').fetchone()
        if not row:
            raise RuntimeError('В реестре моделей нет записей')

        conn.execute('UPDATE models SET active=CASE WHEN id=? THEN 1 ELSE 0 END', (row['id'],))
        conn.commit()
        return {'id': row['id'], 'key': row['key'], 'label': row['label'], 'active': True}


def set_active_model(model_id: int) -> dict:
    """Установка признака активности модели"""
    with _connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        exists = conn.execute('SELECT 1 FROM models WHERE id=?', (model_id,)).fetchone()
        if not exists:
            conn.rollback()
            raise ValueError('Несуществующий ID модели')

        conn.execute('UPDATE models SET active=CASE WHEN id=? THEN 1 ELSE 0 END', (model_id,))
        conn.commit()
        return get_active_model()


def add_note(user_id, text):
    """Добавление новой заметки"""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (user_id, text) VALUES (?, ?)', (user_id, text))
        note_id = cursor.lastrowid
        conn.commit()
        return note_id


def list_notes(user_id):
    """Получение всех заметок пользователя"""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, text FROM notes WHERE user_id = ? ORDER BY id', (user_id,))
        notes = [{'id': row[0], 'text': row[1]} for row in cursor.fetchall()]
        return notes


def update_note(user_id, note_id, new_text):
    """Обновление заметки"""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE notes SET text = ? WHERE id = ? AND user_id = ?', (new_text, note_id, user_id))
        rows_affected = cursor.rowcount
        conn.commit()
        return rows_affected > 0


def delete_note(user_id, note_id):
    """Удаление заметки"""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id))
        rows_affected = cursor.rowcount
        conn.commit()
        return rows_affected > 0


def find_notes(user_id, query):
    """Поиск заметок по тексту"""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, text FROM notes WHERE user_id = ? AND text LIKE ? ORDER BY id',
                       (user_id, f'%{query}%'))
        notes = [{'id': row[0], 'text': row[1]} for row in cursor.fetchall()]
        return notes


def count_notes(user_id):
    """Подсчет количества заметок пользователя"""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM notes WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        return count


def list_characters() -> List[dict]:
    """Получение списка персонажей"""
    with _connect() as conn:
        rows = conn.execute("SELECT id, name FROM characters ORDER BY id").fetchall()
        return [{"id": r["id"], "name": r["name"]} for r in rows]


def get_character_by_id(character_id: int) -> Optional[dict]:
    """Получение персонажа по ID"""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, prompt FROM characters WHERE id=?",
            (character_id,)
        ).fetchone()
        return {'id': row["id"], 'name': row["name"], 'prompt': row["prompt"]} if row else None


def set_user_character(user_id: int, character_id: int) -> dict:
    """Установка персонажа для пользователя"""
    character = get_character_by_id(character_id)
    if not character:
        raise ValueError("Неизвестный ID персонажа")

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_character(telegram_user_id, character_id)
            VALUES(?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET character_id=excluded.character_id
            """,
            (user_id, character_id)
        )
        conn.commit()
        return character


def get_user_character(user_id: int) -> dict:
    """Получение персонажа пользователя"""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT p.id, p.name, p.prompt
            FROM user_character up
            JOIN characters p ON p.id = up.character_id
            WHERE up.telegram_user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if row:
            return {'id': row['id'], 'name': row['name'], 'prompt': row['prompt']}

        # Если у пользователя нет персонажа - берем Иоду (id=1), иначе первую запись
        row = conn.execute('SELECT id, name, prompt FROM characters WHERE id=1').fetchone()
        if row:
            return {'id': row['id'], 'name': row['name'], 'prompt': row['prompt']}

        row = conn.execute('SELECT id, name, prompt FROM characters ORDER BY id LIMIT 1').fetchone()
        if not row:
            raise RuntimeError("Таблица characters пуста")

        return {'id': row['id'], 'name': row['name'], 'prompt': row['prompt']}


def get_character_prompt_for_user(user_id: int) -> str:
    """Получение промита персонажа для пользователя"""
    return get_user_character(user_id)["prompt"]


def add_model(key, label, active=False):
    """Добавление новой модели с использованием UPSERT"""
    with _connect() as conn:
        cursor = conn.cursor()

        # Если модель должна быть активной, сначала сбрасываем все активные
        if active:
            cursor.execute('UPDATE models SET active = 0 WHERE active = 1')

        # Используем UPSERT для вставки или обновления модели
        cursor.execute('''
            INSERT INTO models (key, label, active) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                label = excluded.label,
                active = excluded.active
        ''', (key, label, 1 if active else 0))

        model_id = cursor.lastrowid

        conn.commit()
        return model_id