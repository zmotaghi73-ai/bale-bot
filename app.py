import os
import sqlite3
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)

# --- تنظیمات اصلی ---
BOT_TOKEN = os.environ.get("1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY")
CHANNEL_ID = "@quran_sums"
ADMIN_ID = 722283092
API_URL = f"https://tapi.bale.ai/bot{1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY}"

# --- ایجاد و مدیریت دیتابیس ---
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, joined_at TEXT)''')
    # جدول پیام‌های زمان‌بندی شده
    c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts 
                 (id INTEGER PRIMARY KEY, content TEXT, post_time TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- توابع کمکی ---
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return requests.post(f"{API_URL}/sendMessage", json=payload)

def check_membership(user_id):
    # چک کردن عضویت در کانال بله
    res = requests.get(f"{API_URL}/getChatMember", params={"chat_id": CHANNEL_ID, "user_id": user_id})
    if res.status_code == 200:
        status = res.json().get("result", {}).get("status")
        return status in ["creator", "administrator", "member"]
    return False

# --- هندلر اصلی پیام‌ها ---
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.json
    if "message" not in update:
        return "ok"
    
    msg = update["message"]
    user_id = msg["chat"]["id"]
    text = msg.get("text", "")

    # ۱. ثبت کاربر در دیتابیس
    conn = sqlite3.connect('bot_data.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, ?)", 
                 (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    # ۲. چک کردن عضویت اجباری
    if not check_membership(user_id) and user_id != ADMIN_ID:
        markup = {
            "inline_keyboard": [[{"text": "عضویت در کانال 🌱", "url": f"https://bale.ai/{CHANNEL_ID[1:]}"}]]
        }
        send_message(user_id, "سلام! برای استفاده از امکانات ربات، لطفاً ابتدا عضو کانال ما بشید 👇", markup)
        return "ok"

    # ۳. منوی اصلی
    if text == "/start":
        main_menu = {
            "keyboard": [
                [{"text": "🤖 هوش مصنوعی"}, {"text": "📖 جستجوی قرآن"}],
                [{"text": "🕊️ حدیث تصادفی"}, {"text": "🤲 دعا و مناجات"}],
                [{"text": "📊 آمار من"}, {"text": "📞 ارتباط با ادمین"}]
            ],
            "resize_keyboard": True
        }
        # پیام خوشامدگویی اختصاصی (فقط برای بار اول یا هر بار استارت)
        send_message(user_id, "سلام زندگی جان! به سوپر ربات هوشمند خودت خوش اومدی ✨", main_menu)

    # ۴. بخش مدیریت (فقط برای تو)
    if text == "/admin" and user_id == ADMIN_ID:
        admin_menu = {
            "keyboard": [
                [{"text": "📢 ارسال همگانی"}, {"text": "⏰ زمان‌بندی پست"}],
                [{"text": "📚 مدیریت منابع"}, {"text": "👥 آمار کل کاربران"}],
                [{"text": "🔙 بازگشت"}]
            ]
        }
        send_message(user_id, "وارد پنل مدیریت شدی ادمین عزیز. چه دستوری داری؟", admin_menu)

    return "ok"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
