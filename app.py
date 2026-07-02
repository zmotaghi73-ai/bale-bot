import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- تنظیمات اصلی ---
TOKEN = "1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

# --- پیام‌های متنی ---
WELCOME_MSG = """
سلام و درود به ربات قرآنی «لبیک» خوش آمدید ✨📖

همکار گرامی و کاربر عزیز، این بازو جهت انس بیشتر با کلام وحی و دسترسی سریع به آیات طراحی شده است.

لطفاً برای شروع از دکمه‌های زیر استفاده کنید: 👇
"""

# --- توابع کمکی ---
def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_main_keyboard():
    """ایجاد منوی اصلی دکمه‌ای"""
    return {
        "keyboard": [
            [{"text": "📖 جستجوی آیه"}, {"text": "🌙 آیه روز"}],
            [{"text": "✨ آیات آرامش‌بخش"}, {"text": "🔍 جستجوی موضوعی"}],
            [{"text": "🕌 راهنمای ربات"}]
        ],
        "resize_keyboard": True
    }

# --- مسیرهای Flask ---
@app.route("/")
def home():
    return "Labbayk Quran Bot is ONLINE 🩺📖"

@app.route("/webhook", methods=['POST'])
def webhook():
    update = request.get_json()
    
    if not update or "message" not in update:
        return "OK", 200

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # منطق پاسخ‌دهی (Router)
    if text == "/start":
        send_message(chat_id, WELCOME_MSG, get_main_keyboard())
    
    elif text == "📖 جستجوی آیه":
        send_message(chat_id, "لطفاً نام سوره یا شماره آیه را ارسال کنید. (در نسخه بعد فعال می‌شود)")
    
    elif text == "🌙 آیه روز":
        # اینجا بعداً کد انتخاب آیه تصادفی رو می‌زنیم
        send_message(chat_id, "آیه روز: «أَلَا بِذِکْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ» 🌸\nآگاه باشید که با یاد خدا دل‌ها آرام می‌گیرد.")
    
    elif text == "✨ آیات آرامش‌بخش":
        send_message(chat_id, "تقدیم به شما که پیام‌آور سلامت هستید: ❤️\n«وَ نُنَزِّلُ مِنَ الْقُرْآنِ ما هُوَ شِفاءٌ وَ رَحْمَةٌ لِلْمُؤْمِنِینَ»")
    
    elif text == "🕌 راهنمای ربات":
        send_message(chat_id, "این ربات توسط خادمان قرآن طراحی شده و به مرور قابلیت‌های جدیدی به آن اضافه خواهد شد.")
    
    else:
        # پاسخ به پیام‌های متفرقه
        send_message(chat_id, f"پیام شما دریافت شد: {text}\nلطفاً از دکمه‌های منو استفاده کنید.")

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
