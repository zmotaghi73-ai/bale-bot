import os
import json
import time
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# =========================
# Config
# =========================
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BALE_API_BASE = f"https://tapi.bale.ai/bot{TOKEN}" if TOKEN else ""
PORT = int(os.environ.get("PORT", 10000))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/chat/completions"
).strip()

ADMIN_IDS = set()
for raw_id in os.environ.get("ADMIN_IDS", "").split(","):
    raw_id = raw_id.strip()
    if raw_id.isdigit():
        ADMIN_IDS.add(int(raw_id))

CHANNEL_ID = os.environ.get("CHANNEL_ID", "").strip()
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "").strip()
DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot.db")
LIBRARY_PATH = os.environ.get("LIBRARY_PATH", "library.json")
SETTINGS_PATH = os.environ.get("SETTINGS_PATH", "settings.json")

# مهم: پیش‌فرض خاموش است تا Gunicorn timeout ندهد
ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "false").lower() == "true"

# =========================
# Globals
# =========================
library_data = []
scheduler_started = False
scheduler_lock = threading.Lock()

# =========================
# Database
# =========================
def get_db():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            language TEXT DEFAULT 'fa',
            joined_at TEXT,
            is_banned INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT DEFAULT '',
            state_data TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT,
            content_text TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("🟢 دیتابیس با موفقیت راه‌اندازی شد.")


# =========================
# Default files
# =========================
def ensure_library_file():
    path = Path(LIBRARY_PATH)
    if path.exists():
        return

    seed_library = [
        {
            "title": "قرآن کریم",
            "category": "quran",
            "author": "وحی الهی",
            "summary": "متن قرآن کریم برای جستجو و استفاده در ربات.",
            "keywords": ["قرآن", "سوره", "آیه", "تفسیر"]
        },
        {
            "title": "نهج البلاغه",
            "category": "hadith",
            "author": "امام علی علیه‌السلام",
            "summary": "مجموعه خطبه‌ها، نامه‌ها و حکمت‌ها.",
            "keywords": ["نهج البلاغه", "امام علی", "حکمت", "خطبه"]
        },
        {
            "title": "صحیفه سجادیه",
            "category": "dua",
            "author": "امام سجاد علیه‌السلام",
            "summary": "مجموعه دعاهای ارزشمند و تربیتی.",
            "keywords": ["صحیفه", "دعا", "امام سجاد"]
        },
        {
            "title": "چهل حدیث",
            "category": "book",
            "author": "امام خمینی",
            "summary": "شرح اخلاقی و عرفانی چهل حدیث.",
            "keywords": ["حدیث", "اخلاق", "عرفان"]
        }
    ]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(seed_library, f, ensure_ascii=False, indent=2)


def ensure_settings_file():
    path = Path(SETTINGS_PATH)
    if path.exists():
        return

    seed_settings = {
        "daily_quran": [
            "إِنَّ مَعَ الْعُسْرِ يُسْرًا",
            "وَبَشِّرِ الصَّابِرِينَ",
            "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ"
        ],
        "daily_hadith": [
            "بهترین مردم کسی است که برای مردم سودمندتر باشد.",
            "دانش را بجویید اگرچه در دورترین نقطه باشد.",
            "هر کس خود را بشناسد، پروردگارش را شناخته است."
        ]
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(seed_settings, f, ensure_ascii=False, indent=2)


def load_library():
    global library_data
    ensure_library_file()
    with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
        library_data = json.load(f)
    print("🟢 کتابخانه با موفقیت بارگذاری شد.")


# =========================
# Localization
# =========================
TEXTS = {
    "fa": {
        "welcome": "سلام {name} 🌷\nبه ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.",
        "choose_lang": "لطفاً زبان را انتخاب کن:",
        "main_menu": "یکی از گزینه‌های زیر را انتخاب کن:",
        "ask_ai": "سوالت را بفرست تا پاسخ بدهم.",
        "ask_search": "عبارت جستجو را بفرست.",
        "joined_required": "برای استفاده از ربات، ابتدا عضو کانال شوید.",
        "unknown": "متوجه نشدم. از منوی اصلی یکی از گزینه‌ها را انتخاب کن.",
        "search_empty": "چیزی پیدا نشد.",
        "admin_only": "این بخش فقط برای ادمین است.",
        "daily_sent": "ارسال روزانه انجام شد.",
        "webhook_ok": "Webhook endpoint is alive."
    },
    "en": {
        "welcome": "Hello {name} 🌷\nWelcome to the Quran and Etrat Center bot.",
        "choose_lang": "Please choose your language:",
        "main_menu": "Choose one option:",
        "ask_ai": "Send your question.",
        "ask_search": "Send your search query.",
        "joined_required": "Please join the channel first.",
        "unknown": "I did not understand. Choose from the main menu.",
        "search_empty": "Nothing found.",
        "admin_only": "This section is for admins only.",
        "daily_sent": "Daily post sent.",
        "webhook_ok": "Webhook endpoint is alive."
    },
    "ar": {
        "welcome": "مرحباً {name} 🌷\nأهلاً بك في بوت مركز القرآن والعترة.",
        "choose_lang": "الرجاء اختيار اللغة:",
        "main_menu": "اختر أحد الخيارات:",
        "ask_ai": "أرسل سؤالك.",
        "ask_search": "أرسل عبارة البحث.",
        "joined_required": "يرجى الانضمام إلى القناة أولاً.",
        "unknown": "لم أفهم. اختر من القائمة الرئيسية.",
        "search_empty": "لم يتم العثور على شيء.",
        "admin_only": "هذا القسم للمشرف فقط.",
        "daily_sent": "تم الإرسال اليومي.",
        "webhook_ok": "Webhook endpoint is alive."
    },
    "tr": {
        "welcome": "Merhaba {name} 🌷\nKur'an ve Etrat Merkezi botuna hos geldiniz.",
        "choose_lang": "Lutfen dil secin:",
        "main_menu": "Bir secenek secin:",
        "ask_ai": "Sorunuzu gonderin.",
        "ask_search": "Arama ifadesini gonderin.",
        "joined_required": "Lutfen once kanala katilin.",
        "unknown": "Anlayamadim. Ana menuden bir secenek secin.",
        "search_empty": "Sonuc bulunamadi.",
        "admin_only": "Bu bolum sadece yonetici icindir.",
        "daily_sent": "Gunluk gonderi gonderildi.",
        "webhook_ok": "Webhook endpoint is alive."
    }
}


def tr(user_id, key):
    lang = get_user_language(user_id)
    return TEXTS.get(lang, TEXTS["fa"]).get(key, key)


# =========================
# User helpers
# =========================
def now_str():
    return datetime.utcnow().isoformat()


def log_action(user_id, action):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (user_id, action, created_at) VALUES (?, ?, ?)",
        (user_id, action, now_str())
    )
    conn.commit()
    conn.close()


def upsert_user(user):
    user_id = user.get("id")
    if not user_id:
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, first_name, last_name, username, joined_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username
    """, (
        user_id,
        user.get("first_name", ""),
        user.get("last_name", ""),
        user.get("username", ""),
        now_str()
    ))
    conn.commit()
    conn.close()


def get_user_language(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["language"] if row and row["language"] else "fa"


def set_user_language(user_id, language):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()


def get_user_state(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT state, state_data FROM user_states WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return "", {}
    try:
        state_data = json.loads(row["state_data"]) if row["state_data"] else {}
    except Exception:
        state_data = {}
    return row["state"], state_data


def set_user_state(user_id, state, state_data=None):
    state_data = state_data or {}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_states (user_id, state, state_data)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            state=excluded.state,
            state_data=excluded.state_data
    """, (user_id, state, json.dumps(state_data, ensure_ascii=False)))
    conn.commit()
    conn.close()


def is_admin(user_id):
    return user_id in ADMIN_IDS


# =========================
# Bale API helpers
# =========================
def bale_request(method, payload=None, timeout=20):
    if not TOKEN:
        return {"ok": False, "error": "BOT_TOKEN is not set"}

    url = f"{BALE_API_BASE}/{method}"
    try:
        resp = requests.post(url, json=payload or {}, timeout=timeout)
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return bale_request("sendMessage", payload)


def get_chat_member(chat_id, user_id):
    payload = {
        "chat_id": chat_id,
        "user_id": user_id
    }
    return bale_request("getChatMember", payload)


# =========================
# Keyboards
# =========================
def language_keyboard():
    return {
        "keyboard": [
            [{"text": "فارسی"}, {"text": "English"}],
            [{"text": "العربية"}, {"text": "Türkçe"}]
        ],
        "resize_keyboard": True
    }


def main_keyboard(lang="fa", is_admin_user=False):
    rows = {
        "fa": [
            [{"text": "📚 جستجوی کتابخانه"}, {"text": "🤖 پرسش از هوش مصنوعی"}],
            [{"text": "🌐 تغییر زبان"}, {"text": "ℹ️ درباره ربات"}]
        ],
        "en": [
            [{"text": "📚 Library Search"}, {"text": "🤖 Ask AI"}],
            [{"text": "🌐 Change Language"}, {"text": "ℹ️ About Bot"}]
        ],
        "ar": [
            [{"text": "📚 البحث في المكتبة"}, {"text": "🤖 اسأل الذكاء الاصطناعي"}],
            [{"text": "🌐 تغيير اللغة"}, {"text": "ℹ️ حول البوت"}]
        ],
        "tr": [
            [{"text": "📚 Kutuphane Arama"}, {"text": "🤖 Yapay Zeka Sor"}],
            [{"text": "🌐 Dili Degistir"}, {"text": "ℹ️ Bot Hakkinda"}]
        ]
    }

    kb = rows.get(lang, rows["fa"])
    if is_admin_user:
        kb.append([{"text": "🛠 پنل ادمین"}])

    return {
        "keyboard": kb,
        "resize_keyboard": True
    }


# =========================
# Channel membership
# =========================
def is_user_joined(user_id):
    if not CHANNEL_ID:
        return True

    result = get_chat_member(CHANNEL_ID, user_id)
    if not result or not result.get("ok"):
        return True

    member = result.get("result", {})
    status = member.get("status", "")
    return status in ("member", "administrator", "creator")


# =========================
# DeepSeek
# =========================
def ask_deepseek(prompt, user_lang="fa"):
    if not DEEPSEEK_API_KEY:
        return "کلید DeepSeek تنظیم نشده است."

    system_prompt = (
        "You are a helpful Islamic educational assistant for "
        "Kanoon Quran va Etrat of Shiraz University of Medical Sciences. "
        "Answer clearly, respectfully, and concisely in the user's language."
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        data = resp.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"].strip()
        return "پاسخی از مدل دریافت نشد."
    except Exception as e:
        return f"خطا در ارتباط با DeepSeek: {e}"


# =========================
# Library search
# =========================
def search_library(query):
    q = query.strip().lower()
    if not q:
        return []

    results = []
    for item in library_data:
        haystack = " ".join([
            str(item.get("title", "")),
            str(item.get("category", "")),
            str(item.get("author", "")),
            str(item.get("summary", "")),
            " ".join(item.get("keywords", []))
        ]).lower()

        if q in haystack:
            results.append(item)

    return results[:10]


def format_search_results(results):
    lines = []
    for idx, item in enumerate(results, start=1):
        lines.append(
            f"{idx}. {item.get('title', '-')}\n"
            f"نویسنده: {item.get('author', '-')}\n"
            f"دسته: {item.get('category', '-')}\n"
            f"توضیح: {item.get('summary', '-')}"
        )
    return "\n\n".join(lines)


# =========================
# Daily posts
# =========================
def load_settings():
    ensure_settings_file()
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_daily_post(content_type, content_text):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO daily_posts (content_type, content_text, created_at) VALUES (?, ?, ?)",
        (content_type, content_text, now_str())
    )
    conn.commit()
    conn.close()


def send_daily_posts():
    if not CHANNEL_ID:
        print("⚠️ CHANNEL_ID تنظیم نشده، ارسال روزانه انجام نشد.")
        return

    settings = load_settings()
    quran_items = settings.get("daily_quran", [])
    hadith_items = settings.get("daily_hadith", [])

    if quran_items:
        quran_text = quran_items[int(time.time()) % len(quran_items)]
        msg = f"📖 آیه روز:\n\n{quran_text}"
        send_message(CHANNEL_ID, msg)
        save_daily_post("quran", quran_text)

    if hadith_items:
        hadith_text = hadith_items[int(time.time() + 1) % len(hadith_items)]
        msg = f"🕊 حدیث روز:\n\n{hadith_text}"
        send_message(CHANNEL_ID, msg)
        save_daily_post("hadith", hadith_text)

    print("✅ ارسال روزانه با موفقیت انجام شد.")


def seconds_until_next_run(hour=8, minute=0):
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target = target.replace(day=now.day + 1)
    return max(60, int((target - now).total_seconds()))


def daily_scheduler():
    print("🟢 Daily scheduler started.")
    while True:
        try:
            send_daily_posts()
        except Exception as e:
            print(f"❌ خطا در ارسال روزانه: {e}")

        # ساده و کاربردی: هر 24 ساعت
        time.sleep(24 * 60 * 60)


def start_scheduler_once():
    global scheduler_started

    if not ENABLE_SCHEDULER:
        print("🟡 Scheduler disabled.")
        return

    with scheduler_lock:
        if scheduler_started:
            return
        t = threading.Thread(target=daily_scheduler, daemon=True)
        t.start()
        scheduler_started = True


# =========================
# Message handlers
# =========================
def normalize_language_choice(text):
    mapping = {
        "فارسی": "fa",
        "english": "en",
        "العربية": "ar",
        "türkçe": "tr",
        "turkce": "tr"
    }
    return mapping.get(text.strip().lower())


def handle_start(chat_id, user):
    user_id = user["id"]
    name = user.get("first_name", "دوست عزیز")
    send_message(chat_id, TEXTS["fa"]["welcome"].format(name=name), language_keyboard())
    set_user_state(user_id, "choosing_language")
    log_action(user_id, "/start")


def handle_language_choice(chat_id, user_id, text):
    lang = normalize_language_choice(text)
    if not lang:
        send_message(chat_id, TEXTS["fa"]["choose_lang"], language_keyboard())
        return

    set_user_language(user_id, lang)
    set_user_state(user_id, "")
    send_message(chat_id, tr(user_id, "main_menu"), main_keyboard(lang, is_admin(user_id)))


def handle_main_menu(chat_id, user_id, text):
    lang = get_user_language(user_id)

    if text in ["🌐 تغییر زبان", "🌐 Change Language", "🌐 تغيير اللغة", "🌐 Dili Degistir"]:
        set_user_state(user_id, "choosing_language")
        send_message(chat_id, tr(user_id, "choose_lang"), language_keyboard())
        return

    if text in ["📚 جستجوی کتابخانه", "📚 Library Search", "📚 البحث في المكتبة", "📚 Kutuphane Arama"]:
        set_user_state(user_id, "awaiting_search")
        send_message(chat_id, tr(user_id, "ask_search"))
        return

    if text in ["🤖 پرسش از هوش مصنوعی", "🤖 Ask AI", "🤖 اسأل الذكاء الاصطناعي", "🤖 Yapay Zeka Sor"]:
        set_user_state(user_id, "awaiting_ai")
        send_message(chat_id, tr(user_id, "ask_ai"))
        return

    if text in ["ℹ️ درباره ربات", "ℹ️ About Bot", "ℹ️ حول البوت", "ℹ️ Bot Hakkinda"]:
        about_text = (
            "ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز\n\n"
            "امکانات:\n"
            "- جستجو در کتابخانه\n"
            "- پاسخ‌گویی هوشمند\n"
            "- پشتیبانی چندزبانه\n"
            "- ارسال محتوای روزانه"
        )
        send_message(chat_id, about_text, main_keyboard(lang, is_admin(user_id)))
        return

    if text == "🛠 پنل ادمین":
        if not is_admin(user_id):
            send_message(chat_id, tr(user_id, "admin_only"))
            return
        admin_text = (
            "پنل ادمین:\n"
            "/stats - آمار کاربران\n"
            "/senddaily - ارسال دستی محتوای روزانه"
        )
        send_message(chat_id, admin_text, main_keyboard(lang, True))
        return

    send_message(chat_id, tr(user_id, "unknown"), main_keyboard(lang, is_admin(user_id)))


def handle_stateful_message(chat_id, user_id, text):
    state, _ = get_user_state(user_id)
    lang = get_user_language(user_id)

    if state == "choosing_language":
        handle_language_choice(chat_id, user_id, text)
        return

    if state == "awaiting_search":
        results = search_library(text)
        if results:
            send_message(chat_id, format_search_results(results), main_keyboard(lang, is_admin(user_id)))
        else:
            send_message(chat_id, tr(user_id, "search_empty"), main_keyboard(lang, is_admin(user_id)))
        set_user_state(user_id, "")
        return

    if state == "awaiting_ai":
        answer = ask_deepseek(text, lang)
        send_message(chat_id, answer, main_keyboard(lang, is_admin(user_id)))
        set_user_state(user_id, "")
        return

    handle_main_menu(chat_id, user_id, text)


def handle_command(chat_id, user, text):
    user_id = user["id"]

    if text == "/start":
        handle_start(chat_id, user)
        return

    if text == "/stats":
        if not is_admin(user_id):
            send_message(chat_id, tr(user_id, "admin_only"))
            return

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        user_count = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM daily_posts")
        post_count = cur.fetchone()["c"]
        conn.close()

        send_message(
            chat_id,
            f"📊 آمار ربات\n\nتعداد کاربران: {user_count}\nتعداد ارسال‌های روزانه: {post_count}"
        )
        return

    if text == "/senddaily":
        if not is_admin(user_id):
            send_message(chat_id, tr(user_id, "admin_only"))
            return
        send_daily_posts()
        send_message(chat_id, tr(user_id, "daily_sent"))
        return

    handle_stateful_message(chat_id, user_id, text)


def extract_message(update):
    if "message" in update:
        return update["message"]
    if "edited_message" in update:
        return update["edited_message"]
    return None


# =========================
# Routes
# =========================
@app.route("/", methods=["GET"])
def health():
    return "MegaBot is running! ✅", 200


# این بخش عمداً GET/HEAD را هم قبول می‌کند تا باز کردن آدرس webhook در مرورگر 405 ندهد
@app.route(f"/{TOKEN}", methods=["GET", "HEAD", "POST"])
def webhook():
    if request.method in ("GET", "HEAD"):
        return TEXTS["fa"]["webhook_ok"], 200

    try:
        update = request.get_json(force=True, silent=True) or {}
        message = extract_message(update)

        if not message:
            return jsonify({"ok": True, "ignored": "no_message"}), 200

        chat = message.get("chat", {})
        user = message.get("from", {})
        text = message.get("text", "")

        chat_id = chat.get("id")
        user_id = user.get("id")

        if not chat_id or not user_id:
            return jsonify({"ok": True, "ignored": "missing_ids"}), 200

        upsert_user(user)

        if not is_user_joined(user_id):
            join_text = tr(user_id, "joined_required")
            if CHANNEL_USERNAME:
                join_text += f"\n\n@{CHANNEL_USERNAME}"
            send_message(chat_id, join_text)
            return jsonify({"ok": True, "blocked": "not_joined"}), 200

        if text:
            handle_command(chat_id, user, text.strip())

        return jsonify({"ok": True}), 200

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 200


# =========================
# Startup
# =========================
def startup():
    ensure_library_file()
    ensure_settings_file()
    init_db()
    load_library()
    start_scheduler_once()


startup()

# =========================
# Local / Worker entrypoint
# =========================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "scheduler":
        ENABLE_SCHEDULER = True
        start_scheduler_once()
        while True:
            time.sleep(3600)
    else:
        app.run(host="0.0.0.0", port=PORT, debug=False)
