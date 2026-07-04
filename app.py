import os
import time
import sqlite3
import requests
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

# ----------------- تنظیمات از متغیرهای محیطی (رندر) -----------------
# توکن رو در پنل رندر به عنوان ENV تعریف کن یا مستقیم اینجا بذار
BOT_TOKEN = os.environ.get("BOT_TOKEN", "1649912283:vCf8-a3K617B0DxQVpFfOhL0VJGPaPojpKo")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"
ADMIN_ID = int(os.environ.get("ADMIN_ID", 722283092))
REQUIRED_CHANNEL = "@quran_sums"
CHANNEL_LINK = "https://ble.ir/quran_sums"
DB_PATH = "database.db"

# ----------------- بخش دیتابیس -----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        join_date TEXT,
        is_active INTEGER DEFAULT 1
    )''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
                  (user_id, username, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def get_all_users():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_active = 1")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        return users
    except Exception as e:
        print(f"DB Error: {e}")
        return []

# ----------------- متدهای بله API -----------------
def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

def send_photo(chat_id, photo_path, caption=None):
    url = f"{BASE_URL}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            requests.post(url, data=data, files=files, timeout=20)
    except Exception as e:
        print(f"Error sending photo: {e}")

def check_channel_membership(user_id):
    url = f"{BASE_URL}/getChatMember"
    payload = {"chat_id": REQUIRED_CHANNEL, "user_id": user_id}
    try:
        response = requests.post(url, json=payload, timeout=5).json()
        if response.get("ok"):
            status = response["result"]["status"]
            return status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Error checking membership: {e}")
    return False

# ----------------- دکمه‌ها و کیبوردهای بله -----------------
def get_main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🌙 آیه روز", "callback_data": "generate_card"}],
            [{"text": "📜 حدیث تصادفی", "callback_data": "random_hadith"}],
            [{"text": "🔎 جستجوی قرآن", "callback_data": "search_quran"}],
            [{"text": "🤖 هوش مصنوعی", "callback_data": "ai_section"}],
            [{"text": "📊 وضعیت من", "callback_data": "my_status"}],
            [{"text": "👥 ارتباط با ادمین", "callback_data": "contact_admin"}]
        ]
    }

def get_join_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "عضویت در کانال کانون", "url": CHANNEL_LINK}],
            [{"text": "✅ عضو شدم! بررسی کن", "callback_data": "check_membership"}]
        ]
    }

# ----------------- هندلر وب‌هوک و دریافت پیام‌ها -----------------
@app.route("/", methods=["GET", "POST"])
def webhook():
    # اگر رندر پینگ کرد که بفهمه سرور زنده‌ست
    if request.method == "GET":
        return "Bot Server is Running!", 200

    # دریافت آپدیت‌ها از بله
    update = request.get_json()
    if not update:
        return "Empty update", 400

    # پردازش پیام‌های معمولی
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        username = msg["from"].get("username", "Unknown")
        text = msg.get("text", "")

        add_user(user_id, username)

        # بررسی عضویت اجباری
        if not check_channel_membership(user_id):
            send_message(chat_id, "سلام! برای استفاده از امکانات ربات کانون، لطفاً ابتدا در کانال ما عضو شوید و سپس دکمه بررسی را بزنید. 👇", get_join_keyboard())
            return "OK", 200

        if text == "/start":
            send_message(chat_id, "سلام زندگی! 🌸 به ربات کانون قرآن و عترت خوش آمدی. از منوی زیر انتخاب کن:", get_main_menu())
            
        elif text.startswith("/broadcast") and user_id == ADMIN_ID:
            broadcast_text = text.replace("/broadcast", "").strip()
            if broadcast_text:
                users = get_all_users()
                send_message(chat_id, f"⏳ در حال ارسال به {len(users)} کاربر...")
                for uid in users:
                    send_message(uid, broadcast_text)
                    time.sleep(0.05)
                send_message(chat_id, "✅ پیام همگانی ارسال شد.")
            else:
                send_message(chat_id, "⚠️ متن پیام را بعد از دستور بنویسید.")

    # پردازش دکمه‌های شیشه‌ای (Callback Query)
    elif "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        user_id = cb["from"]["id"]
        cb_data = cb["data"]

        if cb_data == "check_membership":
            if check_channel_membership(user_id):
                send_message(chat_id, "🎉 عضویت شما تایید شد! منوی کاربری فعال شد:", get_main_menu())
            else:
                send_message(chat_id, "❌ هنوز عضو کانال نشده‌اید. لطفاً عضو شوید و مجدد تست کنید.", get_join_keyboard())

        elif cb_data == "generate_card":
            send_message(chat_id, "⏳ در حال آماده‌سازی کارت قرآنی زیبا برای شما...")
            # در اینجا منطق تولید تصویر کارت با افکت‌های Pillow و راست‌نویسی اجرا می‌شود:
            frame_path = "Quran.png"
            output_path = f"card_{user_id}.png"
            
            if os.path.exists(frame_path):
                try:
                    img = Image.open(frame_path).convert("RGBA")
                    draw = ImageDraw.Draw(img)
                    width, height = img.size
                    
                    # نمونه متن فارسی و عربی
                    arabic_text = "إِنَّ مَعَ الْعُسْرِ يُسْرًا"
                    persian_text = "به یقین با هر سختی، آسانی است."
                    
                    # فونت‌های بارگذاری شده روی گیت‌هاب/رندر
                    font_path = "fonts/Vazirmatn-Bold.ttf"
                    if os.path.exists(font_path):
                        font_ar = ImageFont.truetype(font_path, 40)
                    else:
                        font_ar = ImageFont.load_default()
                    
                    # اصلاح راست‌نویسی متن عربی و فارسی
                    ar_reshaped = get_display(arabic_reshaper.reshape(arabic_text))
                    fa_reshaped = get_display(arabic_reshaper.reshape(persian_text))
                    
                    # کشیدن روی تصویر قاب
                    draw.text((width / 2, height / 2.5), ar_reshaped, font=font_ar, fill="black", anchor="mm")
                    draw.text((width / 2, height / 1.8), fa_reshaped, font=font_ar, fill="darkblue", anchor="mm")
                    
                    img.save(output_path, "PNG")
                    send_photo(chat_id, output_path, caption="✨ کارت قرآنی امروز شما")
                    os.remove(output_path)
                except Exception as e:
                    send_message(chat_id, f"❌ خطای تصویرسازی: {e}")
            else:
                send_message(chat_id, "❌ فریم اصلی تصویر روی سرور یافت نشد.")

        elif cb_data == "contact_admin":
            send_message(chat_id, "📬 انتقادات و پیشنهادات خود را ارسال کنید تا برای مدیریت ارسال شود.")

    return "OK", 200

# ----------------- اجرای سرور -----------------
if __name__ == "__main__":
    init_db()
    # پورت رو از رندر می‌گیریم، در غیر این‌صورت روی ۵۰۰۰ اجرا می‌شه
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
