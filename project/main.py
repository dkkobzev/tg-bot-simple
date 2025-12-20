import os
import json
import telebot
import uuid
from telebot import types
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

DATA_DIR = 'pay_data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

user_steps = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Добавить трату", "Регистрация")
    markup.row("Статус", "Расчет")
    markup.row("Удалить трату", "Пнуть должников")
    markup.row("Кто в списке", "Сброс")
    return markup

def get_data(chat_id):
    # Загрузка данных чата из JSON
    path = f"{DATA_DIR}/{chat_id}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"members": {}, "expenses": []}

def save_data(chat_id, data):
    # Сохранение данных чата в JSON
    with open(f"{DATA_DIR}/{chat_id}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_m_name(data, uid):
    # Получение имени участника по ID
    member = data["members"].get(uid, "Удален")
    if isinstance(member, dict):
        return member.get("name", "Без имени")
    return str(member)

def get_m_user(data, uid):
    # Получение username участника по ID
    member = data["members"].get(uid, {})
    if isinstance(member, dict):
        return member.get("username", "")
    return ""

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(message.chat.id, "Бот запущен!", reply_markup=main_menu())

@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Обработка нажатий на кнопки меню
    chat_id = message.chat.id
    data = get_data(chat_id)
    
    if message.text == "Добавить трату":
        if not data["members"]:
            return bot.send_message(chat_id, "❌ Сначала добавьте участников через 'Регистрация'.")
        msg = bot.send_message(chat_id, "Введите данные в формате: <b>сумма имя описание</b>\n(Например: <code>500 Дима Такси</code>)", parse_mode='HTML')
        bot.register_next_step_handler(msg, start_add_expense)
    
    elif message.text == "Удалить трату":
        delete_last_expense(message)
    
    elif message.text == "Регистрация":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Зарегистрировать себя", callback_data="reg_self"),
                   types.InlineKeyboardButton("Добавить другого", callback_data="reg_other"))
        bot.send_message(chat_id, "Кого регистрируем в системе?", reply_markup=markup)
    
    elif message.text == "Статус":
        show_status(message)
    
    elif message.text == "Расчет":
        show_settle(message)
    
    elif message.text == "Пнуть должников":
        remind_debtors(message)
        
    elif message.text == "Кто в списке":
        show_members_list(message)
        
    elif message.text == "Сброс":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Удалить только долги", callback_data="clear_debts"),
                   types.InlineKeyboardButton("Удалить всё полностью", callback_data="clear_all"))
        bot.send_message(chat_id, "⚠️ Выберите режим очистки данных:", reply_markup=markup)

def show_members_list(message):
    # Вывод списка всех зарегистрированных пользователей
    data = get_data(message.chat.id)
    if not data["members"]:
        return bot.send_message(message.chat.id, "👥 В этом чате пока никто не зарегистрирован.")
    
    res = "👥 <b>Зарегистрированные участники:</b>\n\n"
    for uid, info in data["members"].items():
        name = get_m_name(data, uid)
        uname = get_m_user(data, uid)
        res += f"• <b>{name}</b> — {uname if uname else '<i>юзернейм не привязан</i>'}\n"
    
    bot.send_message(message.chat.id, res, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # Обработка нажатий на инлайн-кнопки
    chat_id = call.message.chat.id
    data = get_data(chat_id)

    # Регистрация пользователя через ID Telegram
    if call.data == "reg_self":
        uid = str(call.from_user.id)
        uname = f"@{call.from_user.username}" if call.from_user.username else ""
        data["members"][uid] = {"name": call.from_user.first_name, "username": uname}
        save_data(chat_id, data)
        bot.send_message(chat_id, f"✅ <b>{call.from_user.first_name}</b>, вы успешно добавлены в список!", parse_mode='HTML')
        bot.answer_callback_query(call.id)
        
    elif call.data == "reg_other":
        msg = bot.send_message(chat_id, "Введите данные: <b>Имя @username</b>\n(Ник необязателен)", parse_mode='HTML')
        bot.register_next_step_handler(msg, save_other)
        bot.answer_callback_query(call.id)

    # Обработка выбора участников для деления счета
    elif call.data.startswith(("split_", "toggle_")):
        if chat_id not in user_steps: 
            return bot.answer_callback_query(call.id, "Ошибка сессии. Введите команду заново.", show_alert=True)
            
        if call.data == "split_all":
            user_steps[chat_id]["selected_members"] = list(data["members"].keys())
            data["expenses"].append(user_steps[chat_id])
            save_data(chat_id, data)
            bot.edit_message_text(f"✅ Записано на всех! ({user_steps[chat_id]['amount']}р — {user_steps[chat_id]['desc']})", chat_id, call.message.message_id)
            user_steps.pop(chat_id)
        elif call.data == "split_custom":
            show_member_selection(call.message)
        elif call.data.startswith("toggle_"):
            uid = call.data.replace("toggle_", "")
            if uid in user_steps[chat_id]["selected_members"]:
                user_steps[chat_id]["selected_members"].remove(uid)
            else:
                user_steps[chat_id]["selected_members"].append(uid)
            show_member_selection(call.message, updated=True)
        elif call.data == "split_confirm":
            if not user_steps[chat_id]["selected_members"]:
                return bot.answer_callback_query(call.id, "Выберите хотя бы одного участника!", show_alert=True)
            data["expenses"].append(user_steps[chat_id])
            save_data(chat_id, data)
            bot.edit_message_text(f"✅ Сохранено! Сумма {user_steps[chat_id]['amount']}р распределена вручную.", chat_id, call.message.message_id)
            user_steps.pop(chat_id)
            
    elif call.data == "clear_debts":
        data["expenses"] = []
        save_data(chat_id, data)
        bot.edit_message_text("🗑️ История трат очищена. Долги обнулены.", chat_id, call.message.message_id)
    elif call.data == "clear_all":
        if os.path.exists(f"{DATA_DIR}/{chat_id}.json"): os.remove(f"{DATA_DIR}/{chat_id}.json")
        bot.edit_message_text("💥 Все данные чата (участники и траты) полностью удалены.", chat_id, call.message.message_id)
    bot.answer_callback_query(call.id)

def start_add_expense(message):
    # Парсинг сообщения: сумма, имя плательщика и описание
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[0].isdigit():
        return bot.send_message(message.chat.id, "❌ Неверный формат! Нужно: <b>сумма имя описание</b>\nПример: 500 Дима Такси", parse_mode='HTML')
    
    data = get_data(message.chat.id)
    amount, p_name_input, desc = int(parts[0]), parts[1].lower(), parts[2]
    
    payer_id = next((uid for uid in data["members"] if get_m_name(data, uid).lower() == p_name_input), None)

    if not payer_id:
        return bot.send_message(message.chat.id, f"❌ Участник '{parts[1]}' не найден в списке чата.")

    # Временное сохранение параметров транзакции
    user_steps[message.chat.id] = {
        "payer": payer_id, "amount": amount, "desc": desc, "selected_members": []
    }
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("На всех", callback_data="split_all"),
               types.InlineKeyboardButton("Выбрать вручную", callback_data="split_custom"))
    bot.send_message(message.chat.id, f"💰 Трата: <b>{amount}р</b> ({desc})\nОплатил: <b>{get_m_name(data, payer_id)}</b>\nКак делим?", reply_markup=markup, parse_mode='HTML')

def save_other(m):
    # Сохранение участника, добавленного вручную
    parts = m.text.split()
    if not parts: return
    name = parts[0]
    uname = parts[1] if len(parts) > 1 else ""
    data = get_data(m.chat.id)
    data["members"][str(uuid.uuid4())[:8]] = {"name": name, "username": uname}
    save_data(m.chat.id, data)
    bot.send_message(m.chat.id, f"👤 Участник <b>{name}</b> ({uname}) добавлен в систему.", parse_mode='HTML')

def show_member_selection(message, updated=False):
    # Интерфейс выбора участников для деления траты
    chat_id = message.chat.id
    data = get_data(chat_id)
    expense = user_steps[chat_id]
    markup = types.InlineKeyboardMarkup()
    for uid in data["members"]:
        is_sel = uid in expense["selected_members"]
        markup.add(types.InlineKeyboardButton(f"{'✅' if is_sel else '❌'} {get_m_name(data, uid)}", callback_data=f"toggle_{uid}"))
    markup.add(types.InlineKeyboardButton("💎 ПОДТВЕРДИТЬ", callback_data="split_confirm"))
    
    text = f"Выберите участников для распределения <b>{expense['amount']}р</b>:"
    if updated: bot.edit_message_text(text, chat_id, message.message_id, reply_markup=markup, parse_mode='HTML')
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

def show_status(message):
    # Расчет текущих балансов всех участников
    data = get_data(message.chat.id)
    if not data["expenses"]: return bot.send_message(message.chat.id, "Трат пока нет. Список пуст.")
    
    balances = {uid: 0 for uid in data["members"]}
    spent_info = {uid: {"total": 0, "cats": []} for uid in data["members"]}
    
    for e in data["expenses"]:
        p_id = e["payer"]
        if p_id in spent_info:
            spent_info[p_id]["total"] += e["amount"]
            spent_info[p_id]["cats"].append(f"{e['desc']} ({e['amount']}р)")
            
        share = e["amount"] / len(e["selected_members"])
        balances[p_id] += e["amount"]
        for u in e["selected_members"]:
            if u in balances:
                balances[u] -= share
                
    res = "📊 <b>Детальный статус:</b>\n\n"
    for uid, bal in balances.items():
        name = get_m_name(data, uid)
        info = spent_info[uid]
        icon = '📈' if bal >= 0 else '📉'
        res += f"👤 <b>{name}</b>\n"
        res += f"💳 Вложил всего: <b>{info['total']}р</b>\n"
        if info['cats']:
            res += f"📋 Траты: <i>{', '.join(info['cats'])}</i>\n"
        res += f"{icon} Текущий баланс: <b>{round(bal, 2)}р</b>\n"
        res += "────────────────────\n"
        
    bot.send_message(message.chat.id, res, parse_mode='HTML')

def show_settle(message):
    # Расчет финальных перевода между участниками
    data = get_data(message.chat.id)
    if not data["expenses"]: return bot.send_message(message.chat.id, "Трат нет — расчет не требуется.")
    
    balances = {uid: 0 for uid in data["members"]}
    for e in data["expenses"]:
        share = e["amount"] / len(e["selected_members"])
        balances[e["payer"]] += e["amount"]
        for u in e["selected_members"]:
            balances[u] -= share
            
    # Алгоритм сведения долгов между людьми
    debtors = sorted([[u, b] for u, b in balances.items() if b < -0.1], key=lambda x: x[1])
    creditors = sorted([[u, b] for u, b in balances.items() if b > 0.1], key=lambda x: x[1], reverse=True)
    
    res = "🤝 <b>Рекомендованные переводы:</b>\n\n"
    found = False
    for d_uid, d_bal in debtors:
        while d_bal < -0.1 and creditors:
            c_uid, c_bal = creditors[0]
            pay = min(-d_bal, c_bal)
            res += f"🔸 {get_m_name(data, d_uid)} ➡️ {get_m_name(data, c_uid)}: <b>{round(pay)}р.</b>\n"
            d_bal += pay
            creditors[0][1] -= pay
            if creditors[0][1] < 0.1: creditors.pop(0)
            found = True
            
    bot.send_message(message.chat.id, res if found else "✅ Все долги закрыты, никто никому не должен!", parse_mode='HTML')

def remind_debtors(message):
    # Пинг должников в общем чате
    data = get_data(message.chat.id)
    if not data["expenses"]: return bot.send_message(message.chat.id, "Долгов нет, так как нет трат.")
    
    balances = {uid: 0 for uid in data["members"]}
    for e in data["expenses"]:
        share = e["amount"] / len(e["selected_members"])
        balances[e["payer"]] += e["amount"]
        for u in e["selected_members"]:
            balances[u] -= share
            
    debtors = sorted([[u, b] for u, b in balances.items() if b < -0.1], key=lambda x: x[1])
    creditors = sorted([[u, b] for u, b in balances.items() if b > 0.1], key=lambda x: x[1], reverse=True)
    
    pings = []
    # Формирование списка долгов для упоминания в чате
    for d_uid, d_bal in debtors:
        temp_d_bal, temp_creditors = d_bal, [c[:] for c in creditors]
        ind_debts = []
        while temp_d_bal < -0.1 and temp_creditors:
            c_uid, c_bal = temp_creditors[0]
            pay = min(-temp_d_bal, c_bal)
            ind_debts.append(f"{get_m_name(data, c_uid)} ({round(pay)}р)")
            temp_d_bal += pay
            temp_creditors[0][1] -= pay
            if temp_creditors[0][1] < 0.1: temp_creditors.pop(0)
        
        uname = get_m_user(data, d_uid)
        mention = uname if uname else get_m_name(data, d_uid)
        pings.append(f"👉 {mention} должен: {', '.join(ind_debts)}")
        
    if not pings:
        bot.send_message(message.chat.id, "🎉 Все должники расплатились!")
    else:
        text = "🔔 <b>СПИСОК ДОЛЖНИКОВ:</b>\n\n" + "\n".join(pings)
        bot.send_message(message.chat.id, text, parse_mode='HTML')

def delete_last_expense(message):
    # Удаление последней траты из списка
    data = get_data(message.chat.id)
    if not data["expenses"]:
        return bot.send_message(message.chat.id, "❌ Список пуст, удалять нечего.")
    
    last = data["expenses"].pop()
    save_data(message.chat.id, data)
    p_name = get_m_name(data, last['payer'])
    bot.send_message(message.chat.id, f"🗑 <b>Удалена последняя трата:</b>\n{last['amount']}р от {p_name} ({last['desc']})", parse_mode='HTML')

if __name__ == "__main__":
    bot.infinity_polling()