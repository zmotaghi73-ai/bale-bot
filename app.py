# -*- coding: utf-8 -*-
import os
import sqlite3
import random
import requests
import json
import threading
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# =========================================================
# ۱. تنظیمات و متغیرهای محیطی اصلی (Environment Variables)
# =========================================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BALE_BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "YOUR_DEEPSEEK_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "722283092"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@quran_sums")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = "bot_data.db"

QURAN_FILE = "quran.json"
NAHJ_FILE = "nahj.json"
SAHIFEH_FILE = "sahifeh.json"

# متغیرهای سراسری برای نگه داشتن داده‌های بارگذاری شده در حافظه
QURAN_DATA = []
NAHJ_DATA = []
SAHIFEH_DATA = []

# =========================================================
# ۲. داده‌های اولیه و نمونه (Seed Data) در صورت نبود فایل‌ها
# =========================================================
DEFAULT_QURAN_SEED = [
    {"index": 1, "surah": "حمد", "verse": 1, "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "trans": "به نام خداوند بخشنده مهربان"},
    {"index": 2, "surah": "حمد", "verse": 2, "text": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "trans": "ستایش مخصوص خداوندی است که پروردگار جهانیان است"},
    {"index": 3, "surah": "حمد", "verse": 5, "text": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "trans": "تنها تو را می‌پرستیم و تنها از تو یاری می‌جوییم"},
    {"index": 4, "surah": "بقره", "verse": 153, "text": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "trans": "ای کسانی که ایمان آورده‌اید، از صبر و نماز یاری جویید"},
    {"index": 5, "surah": "بقره", "verse": 255, "text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ", "trans": "خداوند است که هیچ معبودی جز او نیست؛ زنده و پایدار است"}
]

DEFAULT_NAHJ_SEED = [
    {"index": 1, "type": "خطبه", "number": 1, "text": "الْحَمْدُ لِلَّهِ الَّذِی لَا یَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ", "trans": "ستایش خدایی را که سخنوران در ستودن او فرومانند"},
    {"index": 2, "type": "حکمت", "number": 1, "text": "كُنْ فِي الْفِتْنَةِ كَابْنِ اللَّبُونِ لاَ ظَهْرٌ فَيُرْكَبَ، وَلاَ ضَرْعٌ فَيُحْلَبَ", "trans": "در فتنه‌ها چونان شتر دو ساله باش، نه پشتی دارد که سوار شوند و نه پستانی که بدوشند"},
    {"index": 3, "type": "نامه", "number": 31, "text": "يَا بُنَيَّ اجْعَلْ نَفْسَكَ مِيزَاناً فِيما بَيْنَكَ وَبَيْنَ غَيْرِكَ", "trans": "پسرم، خویشتن را میان خود و دیگران ترازویی قرار ده"}
]

DEFAULT_SAHIFEH_SEED = [
    {"index": 1, "dua": 1, "title": "در ستایش پروردگار", "text": "الْحَمْدُ لِلَّهِ الْأَوَّلِ بلا أَوَّلٍ كَانَ قَبْلَهُ", "trans": "ستایش خدای را که نخستین است و پیش از او نخستینی نبوده"},
    {"index": 2, "dua": 20, "title": "دعای مکارم الاخلاق", "text": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَ آلِهِ ، وَ بَلِّغْ بِإِیمَانِی أَکْمَلَ الْإِیمَانِ", "trans": "بار خدایا بر محمد و آلش درود فرست، و ایمان مرا به کامل‌ترین مرتبه ایمان برسان"}
]

# =========================================================
# ۳. توابع راه‌اندازی و مدیریت فایل‌های JSON کتابخانه
# =========================================================
def ensure_library_files():
    """اگر فایل‌های دیتای متون وجود نداشتند، آن‌ها را با مقادیر اولیه می‌سازد."""
    if not os.path.exists(QURAN_FILE):
        with open(QURAN_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_QURAN_SEED, f, ensure_ascii=False, indent=4)
    
    if not os.path.exists(NAHJ_FILE):
        with open(NAHJ_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_NAHJ_SEED, f, ensure_ascii=False, indent=4)
            
    if not os.path.exists(SAHIFEH_FILE):
        with open(SAHIFEH_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SAHIFEH_SEED, f, ensure_ascii=False, indent=4)

def load_library():
    """بارگذاری اطلاعات کتابخانه از فایل‌ها به حافظه موقت رم"""
    global QURAN_DATA, NAHJ_DATA, SAHIFEH_DATA
    try:
        ensure_library_files()
        with open(QURAN_FILE, "r", encoding="utf-8") as f:
            QURAN_DATA = json.load(f)
        with open(NAHJ_FILE, "r", encoding="utf-8") as f:
            NAHJ_DATA = json.load(f)
        with open(SAHIFEH_FILE, "r", encoding="utf-8") as f:
            SAHIFEH_DATA = json.load(f)
        print("🟢 کتابخانه با موفقیت بارگذاری شد.")
    except Exception as e:
        print(f"🔴 خطا در بارگذاری فایل‌های کتابخانه: {e}")

# =========================================================
# ۴. مدیریت دیتابیس محلی ربات (SQLite)
# =========================================================
def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """ایجاد جداول دیتابیس در صورت عدم وجود"""
    conn = db_conn()
    cur = conn.cursor()
    
    # جدول کاربران
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT '',
            lang TEXT DEFAULT 'fa',
            score INTEGER DEFAULT 0,
            state TEXT DEFAULT 'none'
        )
    """)
    
    # جدول وضعیت ارسال‌های روزانه کتابخانه به کانال
    cur.execute("""
        CREATE TABLE IF NOT EXISTS publish_state (
            book_name TEXT PRIMARY KEY,
            last_index INTEGER DEFAULT 0
        )
    """)
    
    # ثبت رکوردهای پیش‌فرض وضعیت ارسال روزانه برای سه منبع
    for book in ["quran", "nahj", "sahifeh"]:
        cur.execute("INSERT OR IGNORE INTO publish_state (book_name, last_index) VALUES (?, 0)", (book,))
        
    conn.commit()
    conn.close()
    print("🟢 دیتابیس با موفقیت راه‌اندازی شد.")

def get_user(chat_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, lang, score, state FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "name": row[0] or "",
            "lang": row[1] if row[1] in ["fa", "en", "ar", "tr"] else "fa",
            "score": row[2] or 0,
            "state": row[3] or "none"
        }
    return {"name": "", "lang": "fa", "score": 0, "state": "none"}

def ensure_user(chat_id, name=""):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (chat_id, name, lang, score, state)
        VALUES (?, ?, 'fa', 0, 'none')
    """, (chat_id, name))
    conn.commit()
    conn.close()

def update_user(chat_id, name=None, lang=None, score=None, state=None, score_add=None):
    conn = db_conn()
    cur = conn.cursor()
    if name is not None:
        cur.execute("UPDATE users SET name=? WHERE chat_id=?", (name, chat_id))
    if lang is not None:
        cur.execute("UPDATE users SET lang=? WHERE chat_id=?", (lang, chat_id))
    if score is not None:
        cur.execute("UPDATE users SET score=? WHERE chat_id=?", (score, chat_id))
    if score_add is not None:
        cur.execute("UPDATE users SET score=score+? WHERE chat_id=?", (score_add, chat_id))
    if state is not None:
        cur.execute("UPDATE users SET state=? WHERE chat_id=?", (state, chat_id))
    conn.commit()
    conn.close()

def get_publish_index(book_name):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT last_index FROM publish_state WHERE book_name = ?", (book_name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def set_publish_index(book_name, index_value):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("UPDATE publish_state SET last_index = ? WHERE book_name = ?", (index_value, book_name))
    conn.commit()
    conn.close()
# =========================================================
# ۵. ابزارهای ارسال پیام به بله
# =========================================================

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        res = requests.post(f"{BASE_URL}/sendMessage", json=data)
        return res.json()
    except Exception as e:
        print("خطا در ارسال پیام:", e)
        return None

def answer_callback(callback_id, text=""):
    try:
        requests.post(f"{BASE_URL}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": text
        })
    except:
        pass

def send_bale(chat_id, text):
    return send_message(chat_id, text)

# =========================================================
# ۶. سیستم چندزبانه (FA / EN / AR / TR)
# =========================================================

LANGS = {
    "fa": {
        "welcome": "سلام! به ربات کانون قرآن و عترت خوش آمدید 🌿",
        "ask_name": "اسم قشنگتو بگو؟",
        "main_menu": "منوی اصلی را انتخاب کن:",
        "ai_prompt": "متن مورد نظرت رو برای هوش مصنوعی بفرست 🌙🧠",
        "join_first": "اول عضو کانال شوید سپس دکمه بررسی عضویت را بزنید:",
        "joined": "عضویت شما تایید شد ✔️",
        "not_joined": "عضویت تایید نشد ❌ لطفاً وارد کانال شوید."
    },
    "en": {
        "welcome": "Welcome to Quran & Etrat Bot 🌿",
        "ask_name": "What is your name?",
        "main_menu": "Choose from main menu:",
        "ai_prompt": "Send your message for AI 🌙",
        "join_first": "Please join the channel first:",
        "joined": "Membership confirmed ✔️",
        "not_joined": "Membership not confirmed ❌"
    },
    "ar": {
        "welcome": "مرحباً بكم في روبوت القرآن والعترة 🌿",
        "ask_name": "ما اسمك؟",
        "main_menu": "اختر من القائمة الرئيسية:",
        "ai_prompt": "أرسل رسالتك للذكاء الاصطناعي 🌙",
        "join_first": "يرجى الانضمام إلى القناة أولاً:",
        "joined": "تم تأكيد العضوية ✔️",
        "not_joined": "لم يتم تأكيد العضوية ❌"
    },
    "tr": {
        "welcome": "Kur'an ve Ehlibeyt Botuna hoş geldiniz 🌿",
        "ask_name": "Adınız nedir?",
        "main_menu": "Ana menüden seçin:",
        "ai_prompt": "Yapay zekaya mesaj gönder 🌙",
        "join_first": "Lütfen önce kanala katılın:",
        "joined": "Üyelik onaylandı ✔️",
        "not_joined": "Üyelik onaylanmadı ❌"
    }
}

def safe(lang, key):
    return LANGS.get(lang, LANGS["fa"]).get(key, "خطا")

# =========================================================
# ۷. کیبوردهای اصلی
# =========================================================

def main_keyboard(lang="fa"):
    # منوی ۱۲‌تایی گنده به سبک MegaBot
    buttons = [
        [{"text": "📖 قرآن"}, {"text": "🤖 هوش مصنوعی"}],
        [{"text": "🔍 جستجو"}, {"text": "📚 کتابخانه"}],
        [{"text": "📡 قرآن لحظه‌ای"}, {"text": "📜 حدیث روز"}],
        [{"text": "📨 پیام به ادمین"}, {"text": "📊 امتیاز"}],
        [{"text": "🕌 رویدادها"}, {"text": "🎉 مسابقات"}],
        [{"text": "🌐 تغییر زبان"}]
    ]
    return json.dumps({"keyboard": buttons, "resize_keyboard": True})

def lang_keyboard():
    return json.dumps({
        "inline_keyboard": [
            [{"text": "فارسی", "callback_data": "setlang_fa"}],
            [{"text": "English", "callback_data": "setlang_en"}],
            [{"text": "العربية", "callback_data": "setlang_ar"}],
            [{"text": "Türkçe", "callback_data": "setlang_tr"}],
        ]
    })

def join_keyboard():
    return json.dumps({
        "inline_keyboard": [
            [{"text": "ورود به کانال", "url": f"https://ble.ir/{CHANNEL_ID.replace('@', '')}"}],
            [{"text": "بررسی عضویت", "callback_data": "check_join"}]
        ]
    })

# =========================================================
# ۸. عضویت اجباری کانال
# =========================================================

def check_membership(chat_id):
    try:
        r = requests.post(
            f"{BASE_URL}/getChatMember",
            json={"chat_id": CHANNEL_ID, "user_id": chat_id}
        ).json()

        if "result" in r and r["result"].get("status") in ["member", "creator", "administrator"]:
            return True
        return False
    except Exception as e:
        print("Membership check error:", e)
        return False

# =========================================================
# ۹. اتصال هوش مصنوعی DeepSeek
# =========================================================

def ask_deepseek(prompt):
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}]
            }
        ).json()
        return r["choices"][0]["message"]["content"]
    except Exception as e:
        return f"خطا در پردازش هوش مصنوعی: {e}"

# =========================================================
# ۱۰. جستجوی کتابخانه سه‌گانه (قرآن/نهج/صحیفه)
# =========================================================

def search_library(q):
    q = q.strip()
    results = []

    for item in QURAN_DATA:
        if q in item["text"] or q in item["trans"]:
            results.append(f"📘 قرآن ({item['surah']} - آیه {item['verse']}):\n{item['text']}\n{item['trans']}")

    for item in NAHJ_DATA:
        if q in item["text"] or q in item["trans"]:
            results.append(f"📙 نهج‌البلاغه ({item['type']} {item['number']}):\n{item['text']}\n{item['trans']}")

    for item in SAHIFEH_DATA:
        if q in item["text"] or q in item["trans"]:
            results.append(f"📗 صحیفه سجادیه ({item['title']}):\n{item['text']}\n{item['trans']}")

    return results

# =========================================================
# ۱۱. پردازش State کاربران
# =========================================================

def handle_state(chat_id, msg, user):
    st = user["state"]
    lang = user["lang"]

    # هوش مصنوعی
    if st == "waiting_ai":
        answer = ask_deepseek(msg)
        send_message(chat_id, f"🤖 پاسخ هوش مصنوعی:\n\n{answer}")
        update_user(chat_id, state="none")
        return

    # جستجو
    if st == "waiting_search":
        res = search_library(msg)
        if not res:
            send_message(chat_id, "چیزی پیدا نشد 😔")
        else:
            for r in res:
                send_message(chat_id, r)
        update_user(chat_id, state="none")
        return

    # پیام به ادمین
    if st == "waiting_admin":
        send_message(ADMIN_ID, f"📨 پیام جدید از کاربر {chat_id}:\n{msg}")
        send_message(chat_id, "ارسال شد ✔️")
        update_user(chat_id, state="none")
        return

    # اگر هیچ state خاصی نبود
    send_message(chat_id, safe(lang, "main_menu"), main_keyboard(lang))
# =========================================================
# ۱۲. ابزار ارسال روزانه از کتابخانه‌ها
# =========================================================

def next_item(book_name, data_list):
    if not data_list:
        return None, 0

    idx = get_publish_index(book_name)
    if idx >= len(data_list):
        idx = 0

    item = data_list[idx]
    new_idx = idx + 1
    if new_idx >= len(data_list):
        new_idx = 0

    set_publish_index(book_name, new_idx)
    return item, new_idx

def format_daily_message(book_name, item):
    if not item:
        return None

    if book_name == "quran":
        return (
            f"🌙 آیه روز\n\n"
            f"📘 سوره {item['surah']} - آیه {item['verse']}\n\n"
            f"{item['text']}\n\n"
            f"🔹 ترجمه:\n{item['trans']}"
        )

    if book_name == "nahj":
        return (
            f"📜 فراز روز از نهج‌البلاغه\n\n"
            f"{item['type']} {item['number']}\n\n"
            f"{item['text']}\n\n"
            f"🔹 ترجمه:\n{item['trans']}"
        )

    if book_name == "sahifeh":
        return (
            f"🤲 فراز روز از صحیفه سجادیه\n\n"
            f"{item['title']} (دعای {item['dua']})\n\n"
            f"{item['text']}\n\n"
            f"🔹 ترجمه:\n{item['trans']}"
        )

    return None

def send_daily_posts():
    try:
        # قرآن
        q_item, _ = next_item("quran", QURAN_DATA)
        q_msg = format_daily_message("quran", q_item)
        if q_msg:
            send_message(CHANNEL_ID, q_msg)

        time.sleep(2)

        # نهج
        n_item, _ = next_item("nahj", NAHJ_DATA)
        n_msg = format_daily_message("nahj", n_item)
        if n_msg:
            send_message(CHANNEL_ID, n_msg)

        time.sleep(2)

        # صحیفه
        s_item, _ = next_item("sahifeh", SAHIFEH_DATA)
        s_msg = format_daily_message("sahifeh", s_item)
        if s_msg:
            send_message(CHANNEL_ID, s_msg)

        print("✅ ارسال روزانه با موفقیت انجام شد.")
    except Exception as e:
        print("❌ خطا در ارسال روزانه:", e)

def daily_scheduler():
    while True:
        try:
            send_daily_posts()
        except Exception as e:
            print("Scheduler error:", e)

        # هر 24 ساعت
        time.sleep(24 * 60 * 60)

# =========================================================
# ۱۳. پردازش وبهوک بله
# =========================================================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}

    # -----------------------------
    # callback query
    # -----------------------------
    if "callback_query" in data:
        cq = data["callback_query"]
        callback_id = cq.get("id")
        callback_data = cq.get("data", "")
        from_user = cq.get("from", {})
        chat_id = from_user.get("id")

        if not chat_id:
            return jsonify({"ok": True})

        ensure_user(chat_id, from_user.get("first_name", ""))
        user = get_user(chat_id)

        if callback_data.startswith("setlang_"):
            lang = callback_data.split("_", 1)[1]
            if lang not in ["fa", "en", "ar", "tr"]:
                lang = "fa"
            update_user(chat_id, lang=lang)
            answer_callback(callback_id, "زبان ذخیره شد")
            send_message(chat_id, safe(lang, "main_menu"), main_keyboard(lang))
            return jsonify({"ok": True})

        if callback_data == "check_join":
            joined = check_membership(chat_id)
            if joined:
                answer_callback(callback_id, safe(user["lang"], "joined"))
                send_message(chat_id, safe(user["lang"], "main_menu"), main_keyboard(user["lang"]))
            else:
                answer_callback(callback_id, safe(user["lang"], "not_joined"))
                send_message(chat_id, safe(user["lang"], "join_first"), join_keyboard())
            return jsonify({"ok": True})

        answer_callback(callback_id, "انجام شد")
        return jsonify({"ok": True})

    # -----------------------------
    # message
    # -----------------------------
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()
    from_user = message.get("from", {})

    if not chat_id:
        return jsonify({"ok": True})

    ensure_user(chat_id, from_user.get("first_name", ""))
    user = get_user(chat_id)

    # عضویت اجباری، به جز برای ادمین
    if chat_id != ADMIN_ID:
        if not check_membership(chat_id):
            send_message(chat_id, safe(user["lang"], "join_first"), join_keyboard())
            return jsonify({"ok": True})

    # دستورات
    if text in ["/start", "شروع", "start"]:
        welcome = safe(user["lang"], "welcome")
        send_message(chat_id, welcome)
        send_message(chat_id, safe(user["lang"], "main_menu"), main_keyboard(user["lang"]))
        return jsonify({"ok": True})

    if text in ["/lang", "زبان", "تغییر زبان", "🌐 تغییر زبان"]:
        send_message(chat_id, "زبان مورد نظر را انتخاب کنید:", lang_keyboard())
        return jsonify({"ok": True})

    # منوها
    if text == "🤖 هوش مصنوعی":
        update_user(chat_id, state="waiting_ai")
        send_message(chat_id, safe(user["lang"], "ai_prompt"))
        return jsonify({"ok": True})

    if text == "🔍 جستجو":
        update_user(chat_id, state="waiting_search")
        send_message(chat_id, "عبارت مورد نظر برای جستجو در قرآن، نهج‌البلاغه و صحیفه را بفرست:")
        return jsonify({"ok": True})

    if text == "📚 کتابخانه":
        msg = (
            "📚 کتابخانه متنی ربات\n\n"
            "منابع فعال:\n"
            "1) قرآن کریم\n"
            "2) نهج‌البلاغه\n"
            "3) صحیفه سجادیه\n\n"
            "برای جستجو از گزینه «🔍 جستجو» استفاده کن."
        )
        send_message(chat_id, msg)
        return jsonify({"ok": True})

    if text == "📨 پیام به ادمین":
        update_user(chat_id, state="waiting_admin")
        send_message(chat_id, "پیامت را بفرست تا برای ادمین ارسال شود.")
        return jsonify({"ok": True})

    if text == "📖 قرآن":
        if QURAN_DATA:
            item = random.choice(QURAN_DATA)
            msg = (
                f"📖 آیه منتخب\n\n"
                f"سوره {item['surah']} - آیه {item['verse']}\n\n"
                f"{item['text']}\n\n"
                f"🔹 ترجمه:\n{item['trans']}"
            )
            send_message(chat_id, msg)
        else:
            send_message(chat_id, "فعلاً دیتای قرآن بارگذاری نشده است.")
        return jsonify({"ok": True})

    if text == "📡 قرآن لحظه‌ای":
        if QURAN_DATA:
            item = random.choice(QURAN_DATA)
            send_message(chat_id, f"📡 قرآن لحظه‌ای\n\n{item['text']}\n\n{item['trans']}")
        else:
            send_message(chat_id, "داده‌ای موجود نیست.")
        return jsonify({"ok": True})

    if text == "📜 حدیث روز":
        hadiths = [
            "قالَ رَسولُ اللهِ ﷺ: خَیرُکُم مَن تَعَلَّمَ القُرآنَ وَ عَلَّمَهُ",
            "امام علی علیه‌السلام: اَلعِلمُ سُلطانٌ",
            "امام صادق علیه‌السلام: مَن قَرَأَ القُرآنَ وَ هُوَ شابٌّ مُؤمِنٌ اختَلَطَ القُرآنُ بِلَحمِهِ وَ دَمِهِ"
        ]
        send_message(chat_id, "📜 حدیث روز\n\n" + random.choice(hadiths))
        return jsonify({"ok": True})

    if text == "📊 امتیاز":
        send_message(chat_id, f"🏅 امتیاز فعلی شما: {user['score']}")
        return jsonify({"ok": True})

    if text == "🕌 رویدادها":
        send_message(chat_id, "🕌 در حال حاضر رویداد ویژه‌ای ثبت نشده است. بعداً این بخش به پنل ادمین وصل می‌شود.")
        return jsonify({"ok": True})

    if text == "🎉 مسابقات":
        send_message(chat_id, "🎉 مسابقات به‌زودی فعال می‌شوند. فعلاً این بخش آماده توسعه است.")
        return jsonify({"ok": True})

    # اگر کاربر در state خاصی باشد
    if user["state"] != "none":
        handle_state(chat_id, text, user)
        return jsonify({"ok": True})

    # پاسخ پیش‌فرض
    send_message(chat_id, safe(user["lang"], "main_menu"), main_keyboard(user["lang"]))
    return jsonify({"ok": True})

# =========================================================
# ۱۴. مسیر سلامت برای Render
# =========================================================

@app.route("/", methods=["GET"])
def health():
    return "MegaBot is running! ✅"

# =========================================================
# ۱۵. راه‌اندازی نهایی برنامه
# =========================================================

def startup():
    init_db()
    load_library()

    # اجرای scheduler در نخ جداگانه
    t = threading.Thread(target=daily_scheduler, daemon=True)
    t.start()
    print("🟢 Daily scheduler started.")

startup()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
