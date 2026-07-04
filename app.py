import os
import sqlite3
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = "1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY"
ADMIN_ID = 722283092

BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = "data.db"


def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    con.commit()
    con.close()


def save_user(chat_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO users(chat_id) VALUES (?)", (chat_id,))
    con.commit()
    con.close()


def get_all_users():
    con = db_conn()
    cur = con.cursor()
    cur.execute("SELECT chat_id FROM users")
    rows = cur.fetchall()
    con.close()
    return [r[0] for r in rows]


def bale_post(method: str, payload: dict):
    url = f"{BASE_URL}/{method}"
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Bale API {method} status:", response.status_code, response.text)
        return response
    except Exception as e:
        print(f"Bale API Error in {method}:", e)
        return None


def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    return bale_post("sendMessage", payload)


def answer_callback(callback_query_id: str):
    payload = {
        "callback_query_id": callback_query_id
    }
    return bale_post("answerCallbackQuery", payload)


def main_menu(is_admin: bool):
    keyboard = [
        [
            {"text": "📖 آیه روز", "callback_data": "get_ayah"},
            {"text": "📿 ذکر روز", "callback_data": "get_dhikr"}
        ],
        [
            {"text": "ℹ️ درباره ربات", "callback_data": "about"}
        ]
    ]

    if is_admin:
        keyboard.append([
            {"text": "🛠 پنل مدیریت", "callback_data": "admin_panel"}
        ])

    return {"inline_keyboard": keyboard}


@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    print("Received update:", data)

    if "message" in data:
        msg = data["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "")

        if chat_id is None:
            return "OK", 200

        chat_id = int(chat_id)

        try:
            save_user(chat_id)
        except Exception as e:
            print("DB Save Error:", e)

        if text == "/start":
            send_message(
                chat_id,
                "سلام زندگی! به ربات قرآنی خوش آمدی. 🌸\nبرای استفاده از بخش‌های مختلف، روی دکمه‌های زیر کلیک کن:",
                reply_markup=main_menu(chat_id == ADMIN_ID)
            )

        elif text == "/admin":
            if chat_id == ADMIN_ID:
                send_message(
                    chat_id,
                    "🛠 پنل مدیریت باز شد.\n\n"
                    "برای ارسال پیام همگانی به اعضا، پیام خود را به شکل زیر ارسال کنید:\n"
                    "/sendall سلام به همگی"
                )
            else:
                send_message(chat_id, "⛔ شما دسترسی مدیریت ندارید.")

        elif text.startswith("/sendall"):
            if chat_id != ADMIN_ID:
                send_message(chat_id, "⛔ این دستور فقط مخصوص مدیر ربات است.")
            else:
                msg_to_send = text.replace("/sendall", "", 1).strip()

                if not msg_to_send:
                    send_message(chat_id, "متن پیام را هم بنویس زندگی.\nمثال:\n/sendall سلام به همگی")
                    return "OK", 200

                users = get_all_users()
                success_count = 0
                fail_count = 0

                for u_id in users:
                    result = send_message(u_id, msg_to_send)
                    if result is not None and result.status_code == 200:
                        success_count += 1
                    else:
                        fail_count += 1

                send_message(
                    chat_id,
                    f"✅ ارسال همگانی انجام شد.\nموفق: {success_count}\nناموفق: {fail_count}"
                )

        else:
            send_message(chat_id, "برای شروع مجدد، دستور /start را بفرستید.")

        return "OK", 200

    elif "callback_query" in data:
        cb = data["callback_query"]
        cb_id = cb.get("id")
        cb_data = cb.get("data", "")

        msg = cb.get("message", {})
        chat = msg.get("chat", {})
        chat_id = chat.get("id")

        if cb_id:
            answer_callback(cb_id)

        if chat_id is None:
            return "OK", 200

        chat_id = int(chat_id)

        if cb_data == "get_ayah":
            send_message(
                chat_id,
                "📖 آیه روز:\n"
                "«وَتَوَکَّلْ عَلَى الْحَیِّ الَّذِی لَا یَمُوتُ»\n"
                "و توکل کن بر آن زنده نامیرایی که هرگز نمی‌میرد.\n"
                "سوره فرقان، آیه ۵۸"
            )

        elif cb_data == "get_dhikr":
            send_message(
                chat_id,
                "📿 ذکر روز:\n"
                "یا قاضِیَ الحاجات\n"
                "ای برآورنده حاجت‌ها"
            )

        elif cb_data == "about":
            send_message(
                chat_id,
                "ℹ️ این ربات جهت انتشار آیات قرآنی و ذکرهای مفید برای پیام‌رسان بله طراحی شده است."
            )

        elif cb_data == "admin_panel":
            if chat_id == ADMIN_ID:
                send_message(
                    chat_id,
                    "🛠 به پنل مدیریت خوش آمدید.\n\n"
                    "ارسال پیام همگانی:\n"
                    "/sendall متن مورد نظر"
                )
            else:
                send_message(chat_id, "⛔ شما ادمین نیستید.")

        else:
            send_message(chat_id, "دکمه نامشخص بود. لطفاً دوباره /start را بزنید.")

        return "OK", 200

    return "OK", 200


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "bot": "Bale Quran Bot"
    }), 200


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
