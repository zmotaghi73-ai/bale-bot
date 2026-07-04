import os
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

TOKEN = "1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
ADMIN_ID = 722283092
USERS_FILE = "users.txt" # برای ذخیره آیدی کاربران جهت ارسال همگانی

def save_user(user_id):
    if not os.path.exists(USERS_FILE): open(USERS_FILE, 'w').close()
    with open(USERS_FILE, 'r+') as f:
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(str(user_id) + "\n")

def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup: payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

@app.route("/", methods=["POST"])
def receive_update():
    data = request.json
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        
        save_user(chat_id)

        if text == "/start":
            menu = {
                "inline_keyboard": [
                    [{"text": "📖 آیه روز", "callback_data": "get_ayah"}, {"text": "📿 ذکر روز", "callback_data": "get_dhikr"}],
                    [{"text": "📸 ساخت کارت قرآنی", "callback_data": "make_card"}],
                    [{"text": "👤 پنل مدیریت", "callback_data": "admin_panel"}]
                ]
            }
            send_message(chat_id, "سلام زندگی! به ربات قرآنی خوش آمدی. یکی از گزینه‌ها رو انتخاب کن:", menu)
        
        elif text.startswith("/sendall ") and chat_id == ADMIN_ID:
            msg_to_send = text.replace("/sendall ", "")
            with open(USERS_FILE, 'r') as f:
                for uid in f.read().splitlines():
                    send_message(uid, msg_to_send)
            send_message(chat_id, "✅ پیام به همه ارسال شد.")

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        query_data = cb["data"]

        if query_data == "get_ayah":
            send_message(chat_id, "آیه روز: «وَتَوَکَّلْ عَلَى الْحَیِّ الَّذِی لَا یَمُوتُ» - و بر آن زنده که نمی‌میرد توکل کن.")
        elif query_data == "get_dhikr":
            send_message(chat_id, "ذکر امروز: یا قاضی الحاجات")
        elif query_data == "admin_panel":
            if chat_id == ADMIN_ID:
                send_message(chat_id, "پنل مدیریت باز شد.\nبرای ارسال پیام همگانی از دستور زیر استفاده کن:\n\n`/sendall سلام به همه` ")
            else:
                send_message(chat_id, "شما دسترسی مدیریت ندارید! ❌")
                
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
