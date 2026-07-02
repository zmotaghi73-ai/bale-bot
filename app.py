import os
import random
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_URL = f"https://api.bale.ai/bot{BOT_TOKEN}"

# ----------------------------
# Keyboard / Menu
# ----------------------------
def get_main_keyboard():
    return {
        "keyboard": [
            [
                {"text": "📖 قرآن در لحظه"},
                {"text": "🕊️ حدیث تصادفی"}
            ],
            [
                {"text": "📖 جستجوی قرآن"},
                {"text": "🌐 جستجوی وب"}
            ],
            [
                {"text": "🤖 هوش مصنوعی"},
                {"text": "📚 مقالات علمی"}
            ],
            [
                {"text": "📢 رویدادها"},
                {"text": "📊 آمار من"}
            ],
            [
                {"text": "📞 ارتباط با ادمین"},
                {"text": "🔄 منوی اصلی"}
            ]
        ],
        "resize_keyboard": True
    }

# ----------------------------
# Bot API helper
# ----------------------------
def send_message(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if keyboard:
        payload["reply_markup"] = keyboard

    try:
        r = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=15)
        print("send_message status:", r.status_code, r.text)
    except Exception as e:
        print("send_message error:", e)

# ----------------------------
# Content
# ----------------------------
WELCOME_MSG = """
<b>سلام زندگی جان 🌷</b>

به ربات قرآنی دلبر و جمع‌وجور ما خوش آمدی!
از منوی زیر یکی را انتخاب کن تا با هم شروع کنیم ✨
"""

QURAN_INSTANT_MSG = """
<b>📖 قرآن در لحظه</b>

اللَّهُ نُورُ السَّمَاوَاتِ وَالْأَرْضِ
<br><i>خداوند نور آسمان‌ها و زمین است.</i>
"""

RANDOM_HADITHS = [
    """
    <b>🕊️ حدیث تصادفی</b>

    <b>متن عربی:</b>
    «إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ»

    <b>ترجمه:</b>
    ارزش عمل‌ها به نیت‌هاست.
    """,
    """
    <b>🕊️ حدیث تصادفی</b>

    <b>متن عربی:</b>
    «الدِّينُ النَّصِيحَةُ»

    <b>ترجمه:</b>
    دین، خیرخواهی و نصیحت است.
    """,
    """
    <b>🕊️ حدیث تصادفی</b>

    <b>متن عربی:</b>
    «سَهِّلُوا وَلا تُعَسِّرُوا»

    <b>ترجمه:</b>
    آسان بگیرید و سخت نگیرید.
    """
]

HELP_MSG = """
<b>📌 راهنما</b>

از دکمه‌های منو استفاده کن:
• قرآن در لحظه
• حدیث تصادفی
• جستجوی قرآن
• جستجوی وب
• هوش مصنوعی
• مقالات علمی
• رویدادها
• آمار من

اگر خواستی، بعداً برای هرکدام جستجوی واقعی هم وصل می‌کنیم.
"""

COMING_SOON = """
<b>✨ این بخش هنوز در حال تکمیل است</b>

فعلاً اسکلتش آماده‌ست و خیلی زود وصلش می‌کنیم.
"""

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    return "Robot is Alive and Healthy!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    print("UPDATE:", data)

    message = data.get("message", {})
    text = (message.get("text") or "").strip()
    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return "OK", 200

    if text in ["/start", "🔄 منوی اصلی"]:
        send_message(chat_id, WELCOME_MSG, get_main_keyboard())
        return "OK", 200

    if text == "📖 قرآن در لحظه":
        send_message(chat_id, QURAN_INSTANT_MSG, get_main_keyboard())
        return "OK", 200

    if text == "🕊️ حدیث تصادفی":
        send_message(chat_id, random.choice(RANDOM_HADITHS), get_main_keyboard())
        return "OK", 200

    if text == "📖 جستجوی قرآن":
        send_message(
            chat_id,
            "<b>📖 جستجوی قرآن</b>\n\nفعلاً نسخه‌ی هوشمند جستجو در حال آماده‌سازی است.",
            get_main_keyboard()
        )
        return "OK", 200

    if text == "🌐 جستجوی وب":
        send_message(chat_id, COMING_SOON, get_main_keyboard())
        return "OK", 200

    if text == "🤖 هوش مصنوعی":
        send_message(chat_id, COMING_SOON, get_main_keyboard())
        return "OK", 200

    if text == "📚 مقالات علمی":
        send_message(chat_id, COMING_SOON, get_main_keyboard())
        return "OK", 200

    if text == "📢 رویدادها":
        send_message(chat_id, COMING_SOON, get_main_keyboard())
        return "OK", 200

    if text == "📊 آمار من":
        send_message(
            chat_id,
            "<b>📊 آمار من</b>\n\n👤 این بخش به‌زودی به آمار شخصی کاربر وصل می‌شود.",
            get_main_keyboard()
        )
        return "OK", 200

    if text == "📞 ارتباط با ادمین":
        send_message(
            chat_id,
            "<b>📞 ارتباط با ادمین</b>\n\nبرای پشتیبانی، بعداً آیدی ادمین را اینجا قرار می‌دهیم.",
            get_main_keyboard()
        )
        return "OK", 200

    send_message(chat_id, HELP_MSG, get_main_keyboard())
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
