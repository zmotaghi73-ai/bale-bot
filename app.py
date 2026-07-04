import os
import sqlite3
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- اطلاعات اصلی و اصلاح توکن واقعی زندگی ---
TOKEN = "1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY"
DEEPSEEK_KEY = "sk-40e2e32cdcdc44ad91e6f428bd187a22"
ADMIN_ID = 722283092
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = "bot_data.db"

# --- متون و منوهای ۴ زبانه ربات کانون ---
LANGS = {
    'fa': {
        'welcome': "سلام {name} جان! {greet} 🌸\nبه ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.\nلطفاً یک گزینه را انتخاب کن:",
        'select_lang': "لطفاً زبان خود را انتخاب کنید / Please choose your language:",
        'ai_prompt': "🤖 سوال خود را بپرسید؛ هوش مصنوعی DeepSeek آماده پاسخگویی است:",
        'ai_wait': "در حال پردازش پاسخ توسط هوش مصنوعی... لطفاً صبور باشید.",
        'ticket_prompt': "📞 لطفاً پیام یا سوال خود را برای مدیریت کانون ارسال کنید:",
        'ticket_sent': "✅ پیام شما با موفقیت ارسال شد و کد پیگیری شما {code} است.",
        'menu': [
            "📖 جستجوی قرآن", "🤖 هوش مصنوعی", "🌐 جستجوی وب",
            "📚 مقالات علمی", "🕊️ حدیث تصادفی", "📖 قرآن در لحظه",
            "📢 رویدادها", "📞 ارتباط با ادمین", "📊 آمار من",
            "🏆 لیگ قرآنی", "📋 کارنامه شخصی", "🌐 تغییر زبان"
        ]
    },
    'en': {
        'welcome': "Hello {name}! {greet} 🌸\nWelcome to the Quran & Etrat Bot of Shiraz University of Medical Sciences.\nPlease choose an option:",
        'select_lang': "Please choose your language:",
        'ai_prompt': "🤖 Ask your question; DeepSeek AI is ready to answer:",
        'ai_wait': "AI is processing your answer... Please wait.",
        'ticket_prompt': "📞 Please send your message or question to the admin:",
        'ticket_sent': "✅ Your message has been sent successfully. Tracking code: {code}",
        'menu': [
            "📖 Quran Search", "🤖 AI DeepSeek", "🌐 Web Search",
            "📚 Scientific Articles", "🕊️ Random Hadith", "📖 Instant Quran",
            "📢 Events", "📞 Contact Admin", "📊 My Stats",
            "🏆 Quranic League", "📋 Personal Scorecard", "🌐 Change Language"
        ]
    },
    'ar': {
        'welcome': "أهلاً بك يا {name}! {greet} 🌸\nمرحباً بك في بوت القرآن والعترة بجامعة شيراز للعلوم الطبية.\nيرجى اختيار خيار:",
        'select_lang': "اختر لغتك من فضلك:",
        'ai_prompt': "🤖 اسأل سؤالك؛ الذكاء الاصطناعي DeepSeek جاهز للإجابة:",
        'ai_wait': "الذكاء الاصطناعي قيد المعالجة... يرجى الانتظار.",
        'ticket_prompt': "📞 يرجى إرسال رسالتك أو سؤالك إلى الإدارة:",
        'ticket_sent': "✅ تم إرسال رسالتك بنجاح. رمز المتابعة الخاص بك هو {code}",
        'menu': [
            "📖 بحث القرآن", "🤖 الذكاء الاصطناعي", "🌐 بحث الويب",
            "📚 المقالات العلمية", "🕊️ الحديث العشوائي", "📖 القرآن في لحظة",
            "📢 الأحداث", "📞 الاتصال بالمسؤول", "📊 إحصائياتي",
            "🏆 الدوري القرآني", "📋 بطاقة الأداء", "🌐 تغيير اللغة"
        ]
    },
    'tr': {
        'welcome': "Merhaba {name}! {greet} 🌸\nŞiraz Tıp Bilimleri Üniversitesi Kuran ve Etrat Botuna hoş geldiniz.\nLütfen bir seçenek seçin:",
        'select_lang': "Lütfen dilinizi seçin:",
        'ai_prompt': "🤖 Sorunuzu sorun; DeepSeek Yapay Zeka cevaplamaya hazır:",
        'ai_wait': "Yapay zeka yanıtı işliyor... Lütfen bekleyin.",
        'ticket_prompt': "📞 Lütfen mesajınızı veya sorunuzu yöneticiye gönderin:",
        'ticket_sent': "✅ Mesajınız başarıyla gönderildi. Takip kodunuz: {code}",
        'menu': [
            "📖 Kuran Arama", "🤖 Yapay Zeka", "🌐 Web Arama",
            "📚 Bilimsel Makaleler", "🕊️ Rastgele Hadis", "📖 Anlık Kuran",
            "📢 Etkinlikler", "📞 Yöneticiye Ulaşın", "📊 İstatistiklerim",
            "🏆 Kuran Ligi", "📋 Kişisel Karne", "🌐 Dil Değiştir"
        ]
    }
}

# --- مدیریت دیتابیس ---
def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'fa',
            score INTEGER DEFAULT 0,
            state TEXT DEFAULT 'none',
            name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quran_offline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surah TEXT,
            verse INTEGER,
            arabic TEXT,
            trans_fa TEXT,
            trans_en TEXT,
            trans_ar TEXT,
            trans_tr TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT lang, score, state FROM users WHERE chat_id=?", (chat_id,))
    res = cur.fetchone()
    conn.close()
    return res if res else ('fa', 0, 'none')

def update_user(chat_id, lang=None, score_add=0, state=None, name=""):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (chat_id, lang, score, state, name) VALUES (?, ?, ?, ?, ?)", (chat_id, 'fa', 0, 'none', name))
    if lang:
        cur.execute("UPDATE users SET lang=? WHERE chat_id=?", (lang, chat_id))
    if score_add:
        cur.execute("UPDATE users SET score=score+? WHERE chat_id=?", (score_add, chat_id))
    if state is not None:
        cur.execute("UPDATE users SET state=? WHERE chat_id=?", (state, chat_id))
    conn.commit()
    conn.close()

# --- ارتباطات بله ---
def send_bale(method, data):
    url = f"{BASE_URL}/{method}"
    try:
        response = requests.post(url, json=data, timeout=15)
        return response
    except Exception as e:
        print(f"Bale API error: {e}")
        return None

def answer_callback(callback_query_id):
    send_bale("answerCallbackQuery", {"callback_query_id": callback_query_id})

# --- طراحی کیبوردهای تعاملی ---
def lang_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🇮🇷 فارسی", "callback_data": "setlang_fa"},
                {"text": "🇬🇧 English", "callback_data": "setlang_en"}
            ],
            [
                {"text": "🇸🇦 العربية", "callback_data": "setlang_ar"},
                {"text": "🇹🇷 Türkçe", "callback_data": "setlang_tr"}
            ]
        ]
    }

def main_menu(chat_id, lang_code):
    l = LANGS.get(lang_code, LANGS['fa'])
    buttons = []
    row = []
    for i, btn_text in enumerate(l['menu']):
        row.append({"text": btn_text, "callback_data": f"menu_{i}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    if chat_id == ADMIN_ID:
        buttons.append([{"text": "🛠️ پنل ادمین کانون", "callback_data": "admin_panel"}])

    return {"inline_keyboard": buttons}

# --- هوش مصنوعی DeepSeek ---
def ask_deepseek(question, lang):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": f"You are a helpful Quranic assistant. Please respond to the user in {lang} language."},
            {"role": "user", "content": question}
        ]
    }
    try:
        res = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=25)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek connection error: {e}")
        return "خطا در اتصال به موتور هوش مصنوعی. لطفاً دوباره تلاش کنید."

# --- کنترلر اصلی وب‌هوک ---
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg = data["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "")
        first_name = msg.get("from", {}).get("first_name", "زندگی")

        if chat_id is None:
            return "OK", 200

        chat_id = int(chat_id)
        lang, score, state = get_user(chat_id)

        # اولین بار ثبت نام کاربر و گرفتن زبان
        if text == "/start":
            update_user(chat_id, name=first_name, state='none')
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": LANGS[lang]['select_lang'],
                "reply_markup": lang_keyboard()
            })
            return "OK", 200

        # اگر کاربر در وضعیت انتظار سوال برای هوش مصنوعی بود
        if state == "waiting_ai":
            send_bale("sendMessage", {"chat_id": chat_id, "text": LANGS[lang]['ai_wait']})
            ai_res = ask_deepseek(text, lang)
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": f"🤖 **DeepSeek Bot:**\n\n{ai_res}",
                "reply_markup": main_menu(chat_id, lang)
            })
            update_user(chat_id, state='none')
            return "OK", 200

    elif "callback_query" in data:
        cb = data["callback_query"]
        cb_id = cb.get("id")
        cb_data = cb.get("data", "")
        msg = cb.get("message", {})
        chat_id = int(msg.get("chat", {}).get("id"))

        if cb_id:
            answer_callback(cb_id)

        lang, score, state = get_user(chat_id)

        # تغییر زبان
        if cb_data.startswith("setlang_"):
            new_lang = cb_data.split("_")[1]
            update_user(chat_id, lang=new_lang, state='none')
            # پیام خوش‌آمدگویی پویا
            greet_msg = "روز خوش" if new_lang == 'fa' else "Good day"
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": LANGS[new_lang]['welcome'].format(name=msg.get("chat", {}).get("first_name", "زندگی"), greet=greet_msg),
                "reply_markup": main_menu(chat_id, new_lang)
            })

        # هندل کردن منوی ۱۲ تایی
        elif cb_data.startswith("menu_"):
            btn_index = int(cb_data.split("_")[1])
            
            # دکمه هوش مصنوعی (DeepSeek)
            if btn_index == 1:
                update_user(chat_id, state='waiting_ai')
                send_bale("sendMessage", {"chat_id": chat_id, "text": LANGS[lang]['ai_prompt']})
            
            # دکمه تغییر زبان دستی
            elif btn_index == 11:
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": LANGS[lang]['select_lang'],
                    "reply_markup": lang_keyboard()
                })
            
            # بقیه دکمه‌ها در فاز بعدی کاملاً فعال می‌شوند
            else:
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"این بخش به زودی فعال می‌شود. زبان فعلی شما: {lang.upper()}",
                    "reply_markup": main_menu(chat_id, lang)
                })

    return "OK", 200

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "active", "bot": "Shiraz Quran Bot"}), 200

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
