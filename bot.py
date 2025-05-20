import random
import string
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

KEYS_FILE = "keys.json"
DATE_FORMAT = "%Y-%m-%d"

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f)

def generate_unique_key(existing_keys, length=12):
    while True:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        new_key = f"nearmod-{suffix}"
        if new_key not in existing_keys:
            return new_key

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    keys = load_keys()

    existing_keys = {data.get("key") for data in keys.values() if data.get("key")}

    if user_id in keys:
        data = keys[user_id]
        key = data.get("key")
        exp_date = data.get("expiration_date")
        reissue_status = data.get("reissue_status", "разрешена")

        if not key or not exp_date:
            key = generate_unique_key(existing_keys)
            exp_date = (datetime.now() + timedelta(days=365)).strftime(DATE_FORMAT)
            reissue_status = "разрешена"
            keys[user_id] = {
                "key": key,
                "expiration_date": exp_date,
                "reissue_status": reissue_status
            }
            save_keys(keys)
    else:
        key = generate_unique_key(existing_keys)
        exp_date = (datetime.now() + timedelta(days=365)).strftime(DATE_FORMAT)
        reissue_status = "разрешена"
        keys[user_id] = {
            "key": key,
            "expiration_date": exp_date,
            "reissue_status": reissue_status
        }
        save_keys(keys)

    keyboard = [
        [InlineKeyboardButton("Перевыпустить ключ 🔄", callback_data="reissue_key")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Твой ключ: {key}\n"
        f"Действует до: {exp_date}\n"
        f"Перевыдача — {reissue_status}",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    keys = load_keys()

    if query.data == "disabled":
        await query.answer("Перевыдача запрещена", show_alert=True)
        return

    if user_id not in keys:
        await query.edit_message_text("У тебя нет выданного ключа. Напиши /start чтобы получить.")
        return

    data = keys[user_id]
    key = data.get("key")
    exp_date = data.get("expiration_date")
    reissue_status = data.get("reissue_status", "разрешена")

    if not key or not exp_date:
        await query.edit_message_text("Данные ключа повреждены. Напиши /start чтобы получить новый.")
        return

    exp_date_dt = datetime.strptime(exp_date, DATE_FORMAT)
    if datetime.now() > exp_date_dt:
        await query.edit_message_text("Срок действия ключа истёк. Обновите ключ.")
        return

    if reissue_status == "запрещена":
        await query.edit_message_text("Перевыдача ключа уже запрещена.")
        return

    # Генерируем новый уникальный ключ и обновляем данные
    existing_keys = {d.get("key") for d in keys.values() if d.get("key")}
    new_key = generate_unique_key(existing_keys)
    new_exp_date = (datetime.now() + timedelta(days=365)).strftime(DATE_FORMAT)

    data["key"] = new_key
    data["expiration_date"] = new_exp_date
    data["reissue_status"] = "запрещена"
    keys[user_id] = data
    save_keys(keys)

    keyboard = [[InlineKeyboardButton("Перевыдача запрещена ❌", callback_data="disabled")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Твой новый ключ: {new_key}\n"
        f"Действует до: {new_exp_date}\n"
        f"Перевыдача — запрещена",
        reply_markup=reply_markup
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token("7623160235:AAEoQPPYO8DHV67PeePlVrZGbIUy4RVeEsA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен...")
    app.run_polling()
