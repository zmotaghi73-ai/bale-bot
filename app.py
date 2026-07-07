# -*- coding: utf-8 -*-
"""
ربات حرفه‌ای کانون قرآن و عترت - نسخه ۳.۰
ویژه دانشگاه علوم پزشکی شیراز
"""

import os
import sqlite3
import random
import requests
import json
import threading
import time
import re
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from functools import wraps
import traceback

# =========================================================
# تنظیمات لاگ‌گیری
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# =========================================================
# ۱. تنظیمات و متغیرهای محیطی اصلی
# =========================================================
TOKEN = os.getenv("BOT_TOKEN", "")
if not TOKEN:
    logger.error("⚠️ BOT_TOKEN تنظیم نشده است!")
    raise ValueError("BOT_TOKEN is required")

DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "722283092"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@quran_sums")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

QURAN_FILE = "quran.json"
NAHJ_FILE = "nahj.json"
SAHIFEH_FILE = "sahifeh.json"

QURAN_DATA = []
NAHJ_DATA = []
SAHIFEH_DATA = []

# =========================================================
# ۲. Feature Flags (کنترل ویژگی‌ها)
# =========================================================
FEATURES = {
    "quran_search": True,
    "deepseek_ai": True,
    "daily_posts": True,
    "articles_search": True,
    "hadith_dhikr": True,
    "instant_quran": True,
    "feedback_system": True,
    "leaderboard": True,
    "daily_receive": True,
    "force_join": True,
    "broadcast": True,
    "admin_panel": True
}

# =========================================================
# ۳. داده‌های اولیه و نمونه
# =========================================================
DEFAULT_QURAN_SEED = [
    {"index": 1, "surah": "حمد", "verse": 1, "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "trans": "به نام خداوند بخشنده مهربان"},
    {"index": 2, "surah": "حمد", "verse": 2, "text": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "trans": "ستایش مخصوص خداوندی است که پروردگار جهانیان است"},
    {"index": 3, "surah": "حمد", "verse": 3, "text": "الرَّحْمَٰنِ الرَّحِيمِ", "trans": "بخشنده و مهربان است"},
    {"index": 4, "surah": "حمد", "verse": 4, "text": "مَالِكِ يَوْمِ الدِّينِ", "trans": "مالک روز جزاست"},
    {"index": 5, "surah": "حمد", "verse": 5, "text": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "trans": "تنها تو را می‌پرستیم و تنها از تو یاری می‌جوییم"},
    {"index": 6, "surah": "بقره", "verse": 153, "text": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "trans": "ای کسانی که ایمان آورده‌اید، از صبر و نماز یاری جویید"},
    {"index": 7, "surah": "بقره", "verse": 255, "text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ", "trans": "خداوند است که هیچ معبودی جز او نیست؛ زنده و پایدار است"},
    {"index": 8, "surah": "بقره", "verse": 286, "text": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "trans": "خداوند هیچ‌کس را جز به اندازه توانش تکلیف نمی‌کند"},
    {"index": 9, "surah": "آل عمران", "verse": 139, "text": "وَلَا تَهِنُوا وَلَا تَحْزَنُوا وَأَنْتُمُ الْأَعْلَوْنَ إِنْ كُنْتُمْ مُؤْمِنِينَ", "trans": "سست نشوید و غمگین نگردید، که اگر مؤمن باشید شما برترید"},
    {"index": 10, "surah": "رعد", "verse": 28, "text": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ", "trans": "آگاه باشید که با یاد خدا دل‌ها آرام می‌گیرد"},
    {"index": 11, "surah": "شرح", "verse": 6, "text": "إِنَّ مَعَ الْعُسْرِ يُسْرًا", "trans": "همانا با سختی، آسانی است"},
    {"index": 12, "surah": "طلاق", "verse": 3, "text": "وَمَنْ يَتَوَكَّلْ عَلَى اللَّهِ فَهُوَ حَسْبُهُ", "trans": "و هر کس بر خدا توکل کند، خدا او را کافی است"},
    {"index": 13, "surah": "زمر", "verse": 53, "text": "لَا تَقْنَطُوا مِنْ رَحْمَةِ اللَّهِ", "trans": "از رحمت خدا نومید نشوید"},
    {"index": 14, "surah": "ابراهیم", "verse": 7, "text": "لَئِنْ شَكَرْتُمْ لَأَزِيدَنَّكُمْ", "trans": "اگر شکر کنید، قطعاً شما را می‌افزایم"},
    {"index": 15, "surah": "نور", "verse": 35, "text": "اللَّهُ نُورُ السَّمَاوَاتِ وَالْأَرْضِ", "trans": "خداوند نور آسمان‌ها و زمین است"},
]

DEFAULT_NAHJ_SEED = [
    {"index": 1, "type": "خطبه", "number": 1, "text": "الْحَمْدُ لِلَّهِ الَّذِی لَا یَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ", "trans": "ستایش خدایی را که سخنوران در ستودن او فرومانند"},
    {"index": 2, "type": "حکمت", "number": 1, "text": "كُنْ فِي الْفِتْنَةِ كَابْنِ اللَّبُونِ لاَ ظَهْرٌ فَيُرْكَبَ، وَلاَ ضَرْعٌ فَيُحْلَبَ", "trans": "در فتنه‌ها چونان شتر دو ساله باش، نه پشتی دارد که سوار شوند و نه پستانی که بدوشند"},
    {"index": 3, "type": "نامه", "number": 31, "text": "يَا بُنَيَّ اجْعَلْ نَفْسَكَ مِيزَاناً فِيما بَيْنَكَ وَبَيْنَ غَيْرِكَ", "trans": "پسرم، خویشتن را میان خود و دیگران ترازویی قرار ده"},
]

DEFAULT_SAHIFEH_SEED = [
    {"index": 1, "dua": 1, "title": "در ستایش پروردگار", "text": "الْحَمْدُ لِلَّهِ الْأَوَّلِ بلا أَوَّلٍ كَانَ قَبْلَهُ", "trans": "ستایش خدای را که نخستین است و پیش از او نخستینی نبوده"},
    {"index": 2, "dua": 20, "title": "دعای مکارم الاخلاق", "text": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَ آلِهِ ، وَ بَلِّغْ بِإِیمَانِی أَکْمَلَ الْإِیمَانِ", "trans": "بار خدایا بر محمد و آلش درود فرست، و ایمان مرا به کامل‌ترین مرتبه ایمان برسان"},
]

# =========================================================
# ۴. احادیث و ذکر روزانه
# =========================================================
HADITHS_WITH_DHIKR = [
    {"hadith": "بهترین شما کسی است که قرآن را بیاموزد و به دیگران یاد دهد. 🌸", "dhikr": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ (۱۰۰ بار)"},
    {"hadith": "در قرآن بیندیشید که بهار دل‌هاست. ✨", "dhikr": "لَا إِلَٰهَ إِلَّا اللَّهُ (۱۰۰ بار)"},
    {"hadith": "قرآن عهد الهی با بندگان است؛ شایسته است هر روز در آن نظر شود. 📖", "dhikr": "اللَّهُ أَكْبَرُ (۱۰۰ بار)"},
    {"hadith": "خانه‌هایتان را با تلاوت قرآن نورانی کنید. 🕯️", "dhikr": "أَسْتَغْفِرُ اللَّهَ (۱۰۰ بار)"},
    {"hadith": "هر کس قرآن را با صدای بلند بخواند، خداوند به او اجر شهید می‌دهد. 🌹", "dhikr": "سُبْحَانَ اللَّهِ وَالْحَمْدُ لِلَّهِ (۱۰۰ بار)"},
]

INSTANT_QURAN_FULL = [
    {"surah": "الرحمن", "verse": 60, "arabic": "هَلْ جَزَاءُ الْإِحْسَانِ إِلَّا الْإِحْسَانُ", "trans": "آیا پاداش نیکی جز نیکی است؟"},
    {"surah": "الضحی", "verse": 1, "arabic": "وَالضُّحَىٰ", "trans": "سوگند به روشنایی روز"},
    {"surah": "الشرح", "verse": 5, "arabic": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا", "trans": "پس یقیناً با دشواری آسانی است"},
    {"surah": "التين", "verse": 1, "arabic": "وَالتِّينِ وَالزَّيْتُونِ", "trans": "سوگند به انجیر و زیتون"},
    {"surah": "العلق", "verse": 1, "arabic": "اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ", "trans": "بخوان به نام پروردگارت که آفرید"},
    {"surah": "القدر", "verse": 1, "arabic": "إِنَّا أَنزَلْنَاهُ فِي لَيْلَةِ الْقَدْرِ", "trans": "ما آن را در شب قدر نازل کردیم"},
]

# =========================================================
# ۵. توابع راه‌اندازی و مدیریت فایل‌های JSON
# =========================================================
def ensure_library_files():
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
    global QURAN_DATA, NAHJ_DATA, SAHIFEH_DATA
    try:
        ensure_library_files()
        with open(QURAN_FILE, "r", encoding="utf-8") as f:
            QURAN_DATA = json.load(f)
        with open(NAHJ_FILE, "r", encoding="utf-8") as f:
            NAHJ_DATA = json.load(f)
        with open(SAHIFEH_FILE, "r", encoding="utf-8") as f:
            SAHIFEH_DATA = json.load(f)
        logger.info(f"کتابخانه بارگذاری شد: قرآن={len(QURAN_DATA)}, نهج={len(NAHJ_DATA)}, صحیفه={len(SAHIFEH_DATA)}")
    except Exception as e:
        logger.error(f"خطا در بارگذاری فایل‌های کتابخانه: {e}")

# =========================================================
# ۶. مدیریت دیتابیس (کامل)
# =========================================================
def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = db_conn()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT '',
            lang TEXT DEFAULT 'fa',
            score INTEGER DEFAULT 0,
            search_count INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            feedback_score INTEGER DEFAULT 0,
            last_active TEXT,
            join_date TEXT DEFAULT CURRENT_TIMESTAMP,
            receive_daily INTEGER DEFAULT 0,
            state TEXT DEFAULT 'none'
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS publish_state (
            book_name TEXT PRIMARY KEY,
            last_index INTEGER DEFAULT 0,
            last_publish_date TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT,
            content_text TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            type TEXT,
            content TEXT,
            score INTEGER DEFAULT 0,
            created_at TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_type TEXT,
            content TEXT,
            sent_to TEXT,
            created_at TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type TEXT,
            error_message TEXT,
            traceback TEXT,
            user_id INTEGER,
            created_at TEXT
        )
    """)
    
    for book in ["quran", "nahj", "sahifeh"]:
        cur.execute("INSERT OR IGNORE INTO publish_state (book_name, last_index) VALUES (?, 0)", (book,))
    
    conn.commit()
    conn.close()
    logger.info("دیتابیس راه‌اندازی شد.")

def get_user(chat_id):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT name, lang, score, search_count, streak, feedback_score, last_active, join_date, receive_daily, state FROM users WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "name": row[0] or "",
                "lang": row[1] if row[1] in ["fa", "en", "ar", "tr"] else "fa",
                "score": row[2] or 0,
                "search_count": row[3] or 0,
                "streak": row[4] or 0,
                "feedback_score": row[5] or 0,
                "last_active": row[6] or "",
                "join_date": row[7] or "",
                "receive_daily": row[8] or 0,
                "state": row[9] or "none"
            }
    except Exception as e:
        logger.error(f"خطا در دریافت کاربر: {e}")
    return {"name": "", "lang": "fa", "score": 0, "search_count": 0, "streak": 0, "feedback_score": 0, "last_active": "", "join_date": "", "receive_daily": 0, "state": "none"}

def ensure_user(chat_id, name=""):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO users (chat_id, name, lang, join_date, last_active)
            VALUES (?, ?, 'fa', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (chat_id, name))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر: {e}")

def update_user(chat_id, **kwargs):
    try:
        conn = db_conn()
        cur = conn.cursor()
        for key, value in kwargs.items():
            if key == "lang" and value not in ["fa", "en", "ar", "tr"]:
                continue
            cur.execute(f"UPDATE users SET {key}=? WHERE chat_id=?", (value, chat_id))
        cur.execute("UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی کاربر: {e}")

def get_publish_index(book_name):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT last_index, last_publish_date FROM publish_state WHERE book_name = ?", (book_name,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0, row[1] if row and row[1] else ""
    except Exception as e:
        logger.error(f"خطا در دریافت وضعیت انتشار: {e}")
        return 0, ""

def set_publish_index(book_name, index_value):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("UPDATE publish_state SET last_index = ?, last_publish_date = CURRENT_TIMESTAMP WHERE book_name = ?", (index_value, book_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در تنظیم وضعیت انتشار: {e}")

def get_leaderboard(limit=10):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT name, score FROM users WHERE score > 0 ORDER BY score DESC LIMIT ?", (limit,))
        users = cur.fetchall()
        conn.close()
        return users
    except Exception as e:
        logger.error(f"خطا در دریافت لیگ قرآنی: {e}")
        return []

def get_user_rank(chat_id):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) + 1 FROM users WHERE score > (SELECT score FROM users WHERE chat_id = ?)", (chat_id,))
        rank = cur.fetchone()[0]
        conn.close()
        return rank
    except Exception as e:
        logger.error(f"خطا در دریافت رتبه کاربر: {e}")
        return 1

def get_user_count():
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"خطا در دریافت تعداد کاربران: {e}")
        return 0

def get_highest_score():
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT MAX(score) FROM users")
        score = cur.fetchone()[0]
        conn.close()
        return score or 0
    except Exception as e:
        logger.error(f"خطا در دریافت بالاترین امتیاز: {e}")
        return 0

def get_all_users(limit=10000):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT chat_id, name, score FROM users ORDER BY score DESC LIMIT ?", (limit,))
        users = cur.fetchall()
        conn.close()
        return users
    except Exception as e:
        logger.error(f"خطا در دریافت لیست کاربران: {e}")
        return []

def log_error(error_type, error_message, traceback_str, user_id=None):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO error_logs (error_type, error_message, traceback, user_id, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (error_type, error_message, traceback_str, user_id))
        conn.commit()
        conn.close()
    except:
        pass

def save_sent_message(message_type, content, sent_to):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sent_messages (message_type, content, sent_to, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (message_type, content, sent_to))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره پیام ارسالی: {e}")

# =========================================================
# ۷. ابزارهای ارسال پیام به بله
# =========================================================
def send_bale(method, data):
    if not TOKEN:
        return {"ok": False, "error": "TOKEN not set"}
    
    url = f"{BASE_URL}/{method}"
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"BALE API status {response.status_code}: {response.text[:200]}")
            return {"ok": False, "error": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        logger.error(f"Timeout در {method}")
        return {"ok": False, "error": "Timeout"}
    except Exception as e:
        logger.error(f"BALE API ERROR in {method}: {e}")
        return {"ok": False, "error": str(e)}

def answer_callback(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    return send_bale("answerCallbackQuery", payload)

def send_message(chat_id, text, reply_markup=None):
    if not text:
        return None
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            send_message(chat_id, part, reply_markup if i == 0 else None)
        return {"ok": True}
    
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return send_bale("sendMessage", payload)

def send_message_with_retry(chat_id, text, reply_markup=None, max_retries=3):
    for attempt in range(max_retries):
        result = send_message(chat_id, text, reply_markup)
        if result and result.get("ok"):
            return result
        time.sleep(2 ** attempt)
    return None

# =========================================================
# ۸. سیستم چندزبانه (کامل با ۱۲ دکمه)
# =========================================================
LANGS = {
    "fa": {
        "select_lang": "🌍 لطفاً زبان موردنظرت را انتخاب کن:",
        "welcome": "سلام {name} عزیز! 😍\nبه ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.\n\n🌟 همراه همیشگی تو در مسیر نور و معرفت.\n\nاز منوی زیر انتخاب کن:",
        "force_join": "🌸 سلام {name} جان!\n\nبرای استفاده از ربات، لطفاً ابتدا عضو کانال کانون قرآن شو:\n{channel}\n\nپس از عضویت، دوباره /start را بزن.",
        "joined_success": "✅ عضویتت تایید شد. خوش اومدی زندگی! 🌸",
        "not_joined_yet": "🥲 هنوز عضویتت تایید نشده. اول عضو کانال شو، بعد دوباره روی دکمه تأیید بزن.",
        "ai_prompt": "🤖 سوالت رو بپرس زندگی! من با عشق جواب می‌دم.",
        "ai_wait": "⏳ یک لحظه صبر کن... دارم با تمام وجود فکر می‌کنم!",
        "admin_msg_prompt": "📩 با خیال راحت پیامت رو بنویس. من می‌رسونم به ادمین.",
        "admin_msg_sent": "✅ پیامت با عشق برای ادمین ارسال شد. 🙏",
        "under_construction": "🚧 این بخش در حال زیباتر شدن است. به‌زودی می‌آید.",
        "stats": "📊 آمار تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}\n⭐ امتیاز پیشنهادات: {feedback_score}\n📅 تاریخ عضویت: {join_date}",
        "about": "این ربات با عشق توسط کانون قرآن و عترت دانشگاه علوم پزشکی شیراز طراحی شده است. ❤️\n\n📚 امکانات:\n• جستجو در قرآن 📖\n• هوش مصنوعی DeepSeek 🤖\n• مقالات علمی 📚\n• حدیث و ذکر روزانه 🕊️\n• قرآن در لحظه ✨\n• کارنامه و لیگ قرآنی 🏆\n• ارسال روزانه 🔔\n• ارسال پیشنهاد و انتقاد با امتیاز ⭐",
        "daily_enable": "✅ دریافت روزانه فعال شد. هر روز با عشق محتوای جدید می‌فرستم.",
        "daily_disable": "❌ دریافت روزانه غیرفعال شد. هر وقت خواستی فعالش کن.",
        "daily_toggle": "🔔 دریافت روزانه",
        "back_to_menu": "🏠 برگشت به منوی اصلی",
        "search_quran_prompt": "📖 کلمه یا عبارت قرآنی موردنظرت رو بفرست تا با عشق جستجو کنیم.",
        "article_prompt": "📚 موضوع مقاله یا کلیدواژه‌ات رو بفرست.",
        "league_text": "🏆 لیگ قرآنی:\n\n{leaderboard}",
        "scorecard_text": "📋 کارنامه و رتبه تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n🎯 رتبه: {rank}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}\n⭐ امتیاز پیشنهادات: {feedback_score}",
        "events_text": "📢 رویدادها و مسابقات کانون:\n\n🔹 جشنواره قرآن و عترت\n🔹 مسابقات حفظ و مفاهیم قرآن\n🔹 کارگاه‌های تفسیر و تدبر\n🔹 برنامه‌های ماه رمضان\n\nبرای اطلاعات بیشتر به کانال مراجعه کن.",
        "unknown_error": "⚠️ یه خطای کوچک رخ داد. دوباره امتحان کن، مطمئنم موفق می‌شی.",
        "article_result": "📚 نتایج جستجوی مقالات علمی برای «{query}»:\n\n{results}",
        "feedback_score_msg": "✅ پیشنهاد ارزشمند شما ثبت شد. {score} امتیاز به شما تعلق گرفت! 🌸",
        "feedback_no_score": "✅ پیشنهاد شما ثبت شد. برای دریافت امتیاز بیشتر، پیشنهاد خود را دقیق‌تر و تأثیرگذارتر بنویسید. 💪",
        "broadcast_prompt": "📢 لطفاً متن اطلاع‌رسانی عمومی را ارسال کنید:",
        "broadcast_success": "✅ پیام همگانی با موفقیت به {count} کاربر ارسال شد. 🌸",
        "broadcast_error": "⚠️ متنی برای ارسال وجود ندارد.",
        "admin_panel": "🛠️ پنل ادمین",
        "admin_stats": "📊 آمار ربات",
        "admin_feedbacks": "📩 لیست انتقادات",
        "admin_broadcast": "📢 ارسال همگانی",
        "admin_users": "👥 لیست کاربران",
        "admin_schedule": "⏰ تنظیمات زمان‌بندی",
        "admin_features": "⚙️ کنترل ویژگی‌ها",
        "admin_logs": "📋 گزارش خطاها",
        "admin_back": "🔄 بازگشت",
        "menu_labels": {
            "search_quran": "📖 جستجوی قرآن",
            "ai": "🤖 هوش مصنوعی",
            "articles": "📚 مقالات علمی",
            "hadith": "🕊️ حدیث و ذکر روز",
            "instant_quran": "✨ قرآن در لحظه",
            "events": "📢 رویدادها و مسابقات",
            "feedback": "📝 پیشنهاد/انتقاد",
            "admin_msg": "📨 پیام به ادمین",
            "stats": "📊 آمار من",
            "league": "🏆 لیگ قرآنی",
            "scorecard": "📋 کارنامه من",
            "change_lang": "🌍 تغییر زبان",
            "daily_toggle": "🔔 دریافت روزانه",
            "about": "ℹ️ درباره ربات"
        }
    },
    "en": {
        "select_lang": "🌍 Please choose your language:",
        "welcome": "Hello {name}! 😍\nWelcome to the Quran & Etrat bot of SUMS.\nPlease choose an option:",
        "force_join": "🌸 To use the bot services, please join our channel first:\n{channel}\n\nThen press /start again.",
        "joined_success": "✅ Membership confirmed. Welcome!",
        "not_joined_yet": "🥲 Your membership is not confirmed yet. Please join first.",
        "ai_prompt": "🤖 Ask your question, dear!",
        "ai_wait": "⏳ Please wait... thinking smart!",
        "admin_msg_prompt": "📩 Send your message and I'll forward it to admin:",
        "admin_msg_sent": "✅ Your message was sent to admin.",
        "under_construction": "🚧 This section is under construction.",
        "stats": "📊 Your stats:\n\n👤 Name: {name}\n🏆 Score: {score}\n📖 Searches: {search_count}\n🔥 Streak: {streak}\n⭐ Feedback Score: {feedback_score}\n📅 Join Date: {join_date}",
        "about": "This bot is designed by the Quran & Etrat Center of Shiraz University of Medical Sciences. ❤️",
        "daily_enable": "✅ Daily receive enabled.",
        "daily_disable": "❌ Daily receive disabled.",
        "daily_toggle": "🔔 Daily Receive",
        "back_to_menu": "🏠 Back to main menu",
        "search_quran_prompt": "📖 Send a Quranic word or phrase to search.",
        "article_prompt": "📚 Send your article topic or keyword.",
        "league_text": "🏆 Quran League:\n\n{leaderboard}",
        "scorecard_text": "📋 Your scorecard and rank:\n\n👤 Name: {name}\n🏆 Score: {score}\n🎯 Rank: {rank}\n📖 Searches: {search_count}\n🔥 Streak: {streak}\n⭐ Feedback Score: {feedback_score}",
        "events_text": "📢 Events and contests:\n\n🔹 Quran and Etrat Festival\n🔹 Memorization contests\n🔹 Interpretation workshops\n🔹 Ramadan programs",
        "unknown_error": "⚠️ A small error occurred. Please try again.",
        "article_result": "📚 Scientific article results for «{query}»:\n\n{results}",
        "feedback_score_msg": "✅ Your valuable suggestion was recorded. You earned {score} points! 🌸",
        "feedback_no_score": "✅ Your suggestion was recorded. To earn more points, write a more detailed and impactful suggestion. 💪",
        "broadcast_prompt": "📢 Please send the broadcast message:",
        "broadcast_success": "✅ Broadcast sent successfully to {count} users. 🌸",
        "broadcast_error": "⚠️ No message to send.",
        "admin_panel": "🛠️ Admin Panel",
        "admin_stats": "📊 Bot Statistics",
        "admin_feedbacks": "📩 Feedback List",
        "admin_broadcast": "📢 Broadcast",
        "admin_users": "👥 User List",
        "admin_schedule": "⏰ Schedule Settings",
        "admin_features": "⚙️ Feature Flags",
        "admin_logs": "📋 Error Logs",
        "admin_back": "🔄 Back",
        "menu_labels": {
            "search_quran": "📖 Quran Search",
            "ai": "🤖 AI Assistant",
            "articles": "📚 Scientific Articles",
            "hadith": "🕊️ Hadith & Dhikr",
            "instant_quran": "✨ Instant Quran",
            "events": "📢 Events & Contests",
            "feedback": "📝 Suggestion/Critique",
            "admin_msg": "📨 Message Admin",
            "stats": "📊 My Stats",
            "league": "🏆 Quran League",
            "scorecard": "📋 My Scorecard",
            "change_lang": "🌍 Change Language",
            "daily_toggle": "🔔 Daily Receive",
            "about": "ℹ️ About Bot"
        }
    }
}

def safe_lang_dict(lang_code):
    return LANGS.get(lang_code, LANGS["fa"])

def safe_text(lang_code, key, default=None, **kwargs):
    lang_dict = safe_lang_dict(lang_code)
    text = lang_dict.get(key, default if default is not None else key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

# =========================================================
# ۹. کیبوردهای اینلاین (۱۲ دکمه کامل)
# =========================================================
def lang_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🇮🇷 فارسی", "callback_data": "setlang_fa"}],
            [{"text": "🇬🇧 English", "callback_data": "setlang_en"}],
            [{"text": "🇸🇦 العربية", "callback_data": "setlang_ar"}],
            [{"text": "🇹🇷 Türkçe", "callback_data": "setlang_tr"}]
        ]
    }

def join_keyboard():
    channel_username = CHANNEL_ID.replace("@", "")
    return {
        "inline_keyboard": [
            [{"text": "📢 ورود به کانال", "url": f"https://ble.ir/{channel_username}"}],
            [{"text": "✅ تایید عضویت", "callback_data": "check_join"}]
        ]
    }

def back_menu_keyboard(lang):
    text = safe_text(lang, "back_to_menu")
    return {"inline_keyboard": [[{"text": text, "callback_data": "back_main"}]]}

def main_menu(chat_id, lang):
    labels = safe_lang_dict(lang)["menu_labels"]
    buttons = [
        [{"text": labels["search_quran"], "callback_data": "menu_search_quran"},
         {"text": labels["ai"], "callback_data": "menu_ai"}],
        [{"text": labels["articles"], "callback_data": "menu_articles"},
         {"text": labels["hadith"], "callback_data": "menu_hadith"}],
        [{"text": labels["instant_quran"], "callback_data": "menu_instant_quran"},
         {"text": labels["events"], "callback_data": "menu_events"}],
        [{"text": labels["feedback"], "callback_data": "menu_feedback"},
         {"text": labels["admin_msg"], "callback_data": "menu_admin_msg"}],
        [{"text": labels["stats"], "callback_data": "menu_stats"},
         {"text": labels["league"], "callback_data": "menu_league"}],
        [{"text": labels["scorecard"], "callback_data": "menu_scorecard"},
         {"text": labels["daily_toggle"], "callback_data": "menu_daily_toggle"}],
        [{"text": labels["change_lang"], "callback_data": "menu_change_lang"},
         {"text": labels["about"], "callback_data": "menu_about"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]
    
    if chat_id == ADMIN_ID and FEATURES["admin_panel"]:
        buttons.append([{"text": safe_text(lang, "admin_panel"), "callback_data": "admin_panel"}])
    
    return {"inline_keyboard": buttons}

def admin_menu(chat_id, lang="fa"):
    return {
        "inline_keyboard": [
            [{"text": safe_text(lang, "admin_stats"), "callback_data": "admin_stats"}],
            [{"text": safe_text(lang, "admin_feedbacks"), "callback_data": "admin_feedbacks"}],
            [{"text": safe_text(lang, "admin_broadcast"), "callback_data": "admin_broadcast"}],
            [{"text": safe_text(lang, "admin_users"), "callback_data": "admin_users"}],
            [{"text": safe_text(lang, "admin_schedule"), "callback_data": "admin_schedule"}],
            [{"text": safe_text(lang, "admin_features"), "callback_data": "admin_features"}],
            [{"text": safe_text(lang, "admin_logs"), "callback_data": "admin_logs"}],
            [{"text": safe_text(lang, "admin_back"), "callback_data": "back_main"}]
        ]
    }

# =========================================================
# ۱۰. عضویت اجباری کانال بله
# =========================================================
def check_membership(chat_id):
    if not CHANNEL_ID or not FEATURES["force_join"]:
        return True
    
    try:
        result = send_bale("getChatMember", {
            "chat_id": CHANNEL_ID,
            "user_id": chat_id
        })
        if result and result.get("ok"):
            status = result.get("result", {}).get("status", "")
            return status in ["member", "administrator", "creator"]
        return False
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

# =========================================================
# ۱۱. اتصال هوش مصنوعی DeepSeek (استاندارد شده)
# =========================================================
def ask_deepseek(question, lang):
    if not FEATURES["deepseek_ai"]:
        return "🔧 این ویژگی در حال حاضر غیرفعال است."
    
    if not DEEPSEEK_KEY:
        return "🔑 کلید API هوش مصنوعی DeepSeek تنظیم نشده است. لطفاً با ادمین تماس بگیرید."
    
    language_name = {"fa": "Persian", "en": "English", "ar": "Arabic", "tr": "Turkish"}.get(lang, "Persian")
    
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": f"You are a warm, respectful, accurate assistant for a Quranic student bot at Shiraz University of Medical Sciences. Reply in {language_name}. Keep the answer useful, friendly, and well-formatted."},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7
    }
    
    try:
        res = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=40)
        data = res.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        return "⚠️ خطا در ارتباط با هوش مصنوعی. لطفاً بعداً تلاش کنید."
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "⚠️ خطا در ارتباط با هوش مصنوعی. لطفاً بعداً تلاش کنید."

# =========================================================
# ۱۲. جستجوی قرآن
# =========================================================
def search_quran_only(q):
    if not FEATURES["quran_search"]:
        return []
    
    q = q.strip().lower()
    if not q:
        return []

    results = []
    for item in QURAN_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("surah", ""))
        ]).lower()
        
        if q in search_text:
            results.append(item)
    
    seen = set()
    unique_results = []
    for item in results:
        item_key = str(item.get("index", "")) + str(item.get("text", ""))
        if item_key not in seen:
            seen.add(item_key)
            unique_results.append(item)
    
    return unique_results[:10]

def search_other_books(q):
    q = q.strip().lower()
    if not q:
        return []

    results = []
    for item in NAHJ_DATA + SAHIFEH_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("title", "")),
            str(item.get("type", ""))
        ]).lower()
        
        if q in search_text:
            results.append(item)
    
    seen = set()
    unique_results = []
    for item in results:
        item_key = str(item.get("index", "")) + str(item.get("text", ""))
        if item_key not in seen:
            seen.add(item_key)
            unique_results.append(item)
    
    return unique_results[:5]

# =========================================================
# ۱۳. جستجوی مقالات علمی
# =========================================================
def search_articles(query):
    if not FEATURES["articles_search"]:
        return "🔧 این ویژگی در حال حاضر غیرفعال است."
    
    try:
        url = f"https://api.openalex.org/works?search={query.replace(' ', '+')}&per-page=5"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        results = []
        for work in data.get("results", []):
            title = work.get("title", "بدون عنوان")
            doi = work.get("doi", "")
            link = f"https://doi.org/{doi}" if doi else ""
            if title and link:
                results.append(f"📄 <b>{title}</b>\n🔗 <a href='{link}'>{link}</a>")
        
        return '\n\n'.join(results) if results else "مقاله‌ای یافت نشد."
    except Exception as e:
        logger.error(f"Article search error: {e}")
        return f"خطا در جستجوی مقالات: {e}"

# =========================================================
# ۱۴. سیستم ارسال روزانه (۳ زمان مختلف)
# =========================================================
def send_daily_posts():
    try:
        if not FEATURES["daily_posts"]:
            return
        
        now = datetime.now()
        
        # ارسال در ۳ زمان: ۸ صبح، ۱۲ ظهر، ۱۸ عصر
        scheduled_times = [
            (8, 0, "صبح"),
            (12, 0, "ظهر"),
            (18, 0, "عصر")
        ]
        
        for hour, minute, time_name in scheduled_times:
            if now.hour == hour and now.minute == minute:
                logger.info(f"ارسال پست روزانه - زمان {time_name}")
                
                # ۱. آیه روز از قرآن
                q_item, q_idx = next_item("quran", QURAN_DATA)
                if q_item:
                    q_msg = format_daily_message("quran", q_item)
                    if q_msg:
                        send_message(CHANNEL_ID, q_msg)
                        set_publish_index("quran", q_idx)
                        save_sent_message("daily_quran", q_msg, CHANNEL_ID)
                        logger.info(f"آیه روزانه ارسال شد - {time_name}")
                        time.sleep(2)
                
                # ۲. حدیث روز
                hadith_item = random.choice(HADITHS_WITH_DHIKR)
                hadith_msg = f"🕊️ <b>حدیث روز</b>\n\n{hadith_item['hadith']}\n\n🔹 <b>ذکر روزانه:</b>\n{hadith_item['dhikr']}\n\n💚 با یاد خدا دل‌ها آرام می‌گیرد."
                send_message(CHANNEL_ID, hadith_msg)
                save_sent_message("daily_hadith", hadith_msg, CHANNEL_ID)
                logger.info(f"حدیث روزانه ارسال شد - {time_name}")
                time.sleep(2)
                
                # ۳. ارسال به کاربرانی که دریافت روزانه فعال دارند
                conn = db_conn()
                cur = conn.cursor()
                cur.execute("SELECT chat_id, name, lang FROM users WHERE receive_daily = 1")
                users = cur.fetchall()
                conn.close()
                
                for user in users:
                    try:
                        daily_msg = f"🌅 <b>پیام روزانه کانون قرآن</b>\n\n{q_msg or ''}\n\n{hadith_msg}\n\n🙏 از همراهی شما سپاسگزاریم."
                        send_message(user[0], daily_msg)
                        time.sleep(0.3)
                    except Exception as e:
                        logger.error(f"ارسال به {user[0]} ناموفق: {e}")
                
                logger.info(f"ارسال روزانه کامل شد - {time_name}")
                break
        
        time.sleep(10)
    except Exception as e:
        logger.error(f"خطا در ارسال روزانه: {e}")

def next_item(book_name, data_list):
    if not data_list:
        return None, 0
    
    current_idx, last_date = get_publish_index(book_name)
    
    today = datetime.now().date().isoformat()
    if last_date and today in last_date:
        return None, current_idx
    
    idx = current_idx
    if idx >= len(data_list):
        idx = 0
    
    item = data_list[idx]
    new_idx = (idx + 1) % len(data_list)
    
    return item, new_idx

def format_daily_message(book_name, item):
    if not item:
        return None
    
    if book_name == "quran":
        return f"📘 آیه منتخب روز\n\nسوره {item['surah']} - آیه {item['verse']}\n\n{item['text']}\n\n🔹 ترجمه:\n{item['trans']}"
    
    if book_name == "nahj":
        return f"📜 فراز روز از نهج‌البلاغه\n\n{item['type']} {item['number']}\n\n{item['text']}\n\n🔹 ترجمه:\n{item['trans']}"
    
    if book_name == "sahifeh":
        return f"🤲 فراز روز از صحیفه سجادیه\n\n{item['title']} (دعای {item['dua']})\n\n{item['text']}\n\n🔹 ترجمه:\n{item['trans']}"
    
    return None

def daily_scheduler():
    """اسکجولر روزانه - هر دقیقه بررسی می‌کند"""
    time.sleep(30)
    while True:
        try:
            send_daily_posts()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        time.sleep(60)  # هر دقیقه یکبار بررسی

# =========================================================
# ۱۵. مدیریت پردازش وضعیت‌های خاص کاربر
# =========================================================
def handle_state_message(chat_id, text, user):
    lang = user["lang"]
    state = user["state"]
    name = user["name"] or "کاربر گرامی"

    # وضعیت هوش مصنوعی
    if state == "waiting_ai":
        send_message(chat_id, safe_text(lang, "ai_wait"))
        answer = ask_deepseek(text, lang)
        send_message(chat_id, f"🤖 {answer}", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=2)
        return True

    # وضعیت پیام به ادمین
    if state == "waiting_admin_msg":
        send_message(
            ADMIN_ID,
            f"📩 پیام جدید از کاربر:\n\n👤 نام: {name}\n🆔 chat_id: {chat_id}\n💬 متن:\n{text}"
        )
        send_message(chat_id, safe_text(lang, "admin_msg_sent"), main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=1)
        return True

    # وضعیت جستجوی قرآن
    if state == "waiting_quran_search":
        results = search_quran_only(text)
        if results:
            msg = f"📖 <b>نتایج جستجو در قرآن:</b>\n\n"
            for i, item in enumerate(results[:5], 1):
                msg += f"{i}. <b>{item['surah']} (آیه {item['verse']})</b>\n{item['text']}\n✨ {item['trans']}\n\n"
            send_message(chat_id, msg, main_menu(chat_id, lang))
        else:
            other_results = search_other_books(text)
            if other_results:
                msg = f"📚 <b>در قرآن یافت نشد، اما در سایر کتاب‌ها:</b>\n\n"
                for i, item in enumerate(other_results[:3], 1):
                    book_type = "نهج‌البلاغه" if item.get('type') else "صحیفه سجادیه"
                    title = item.get('title') or f"{item.get('type', '')} {item.get('number', '')}"
                    msg += f"{i}. <b>{title}</b>\n{item['text']}\n✨ {item['trans']}\n\n"
                send_message(chat_id, msg, main_menu(chat_id, lang))
            else:
                send_message(chat_id, "😔 نتیجه‌ای برای عبارت مورد نظر شما پیدا نشد.\n\n💡 شاید با کلمات کلیدی دیگری امتحان کنید.", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=1, search_add=1)
        return True

    # وضعیت مقالات علمی
    if state == "waiting_article":
        send_message(chat_id, "📚 در حال جستجوی مقالات...")
        result = search_articles(text)
        send_message(chat_id, safe_text(lang, "article_result", query=text, results=result), main_menu(chat_id, lang))
        update_user(chat_id, state="none")
        return True
    
    # وضعیت انتقاد و پیشنهاد
    if state == "waiting_feedback":
        if not FEATURES["feedback_system"]:
            send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
            update_user(chat_id, state="none")
            return True
        
        update_user(chat_id, state="none")
        
        # امتیازدهی هوشمند
        score = 0
        if len(text) > 20:
            score += 5
        if "لطفا" in text or "متشکرم" in text or "خواهش" in text:
            score += 3
        if "قرآن" in text or "حدیث" in text or "دعا" in text:
            score += 2
        if "پیشنهاد" in text or "انتقاد" in text or "بهبود" in text:
            score += 3
        
        try:
            conn = db_conn()
            cur = conn.cursor()
            cur.execute("INSERT INTO feedbacks (user_id, user_name, type, content, score, created_at) VALUES (?, ?, 'suggestion', ?, ?, CURRENT_TIMESTAMP)", 
                       (chat_id, name, text, score))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطا در ذخیره پیشنهاد: {e}")
        
        if score >= 7:
            update_user(chat_id, score_add=score, feedback_score=score)
            send_message(chat_id, safe_text(lang, "feedback_score_msg", score=score), main_menu(chat_id, lang))
            send_message(ADMIN_ID, f"📩 پیشنهاد جدید:\n👤 {name}\n📝 {text}\n⭐ امتیاز: {score}")
        else:
            send_message(chat_id, safe_text(lang, "feedback_no_score"), main_menu(chat_id, lang))
            send_message(ADMIN_ID, f"📩 پیشنهاد جدید:\n👤 {name}\n📝 {text}\n⭐ امتیاز: {score}")
        return True

    # وضعیت ارسال همگانی
    if state == "waiting_broadcast":
        if chat_id != ADMIN_ID:
            send_message(chat_id, "⛔ دسترسی غیرمجاز.")
            update_user(chat_id, state="none")
            return True
        
        if not FEATURES["broadcast"]:
            send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", admin_menu(chat_id, lang))
            update_user(chat_id, state="none")
            return True
        
        update_user(chat_id, state="none")
        
        # ارسال به همه کاربران
        users = get_all_users(10000)
        count = 0
        for uid, name, score in users:
            try:
                send_message(int(uid), f"📢 <b>اطلاعیه کانون قرآن و عترت</b>\n\n{text}\n\n🙏 از همراهی شما سپاسگزاریم.")
                count += 1
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"خطا در ارسال به {uid}: {e}")
        
        save_sent_message("broadcast", text, f"{count} users")
        send_message(chat_id, safe_text(lang, "broadcast_success", count=count), admin_menu(chat_id, lang))
        return True

    return False

# =========================================================
# ۱۶. توابع کمکی
# =========================================================
def get_user_state(chat_id):
    """دریافت وضعیت کاربر از دیتابیس"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT state FROM users WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else "none"
    except Exception as e:
        logger.error(f"خطا در دریافت وضعیت کاربر: {e}")
        return "none"

# =========================================================
# ۱۷. مسیرهای تست و سلامت
# =========================================================
@app.route("/", methods=["GET", "HEAD"])
def health():
    return jsonify({
        "status": "ok",
        "service": "labbayk_quranbot",
        "version": "3.0",
        "port": os.getenv("PORT", "10000"),
        "quran_records": len(QURAN_DATA),
        "nahj_records": len(NAHJ_DATA),
        "sahifeh_records": len(SAHIFEH_DATA),
        "total_users": get_user_count(),
        "features": FEATURES
    }), 200

@app.route("/webhook", methods=["GET", "HEAD"])
def webhook_check():
    return jsonify({"status": "ok", "message": "Webhook is alive"}), 200

# =========================================================
# ۱۸. وب هوک و مدیریت یکپارچه درخواست‌ها
# =========================================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_token():
    try:
        data = request.get_json(force=True, silent=True) or {}
        
        if "message" in data:
            msg = data["message"]
            chat = msg.get("chat", {})
            sender = msg.get("from", {})

            chat_id = chat.get("id")
            text = msg.get("text", "")
            first_name = sender.get("first_name", "زندگی")

            if not chat_id:
                return "OK", 200

            chat_id = int(chat_id)
            ensure_user(chat_id, first_name)
            update_user(chat_id, name=first_name)

            user = get_user(chat_id)
            lang = user["lang"]

            if text == "/start" or text == "شروع" or text == "/start@labbayk_quranbot":
                update_user(chat_id, state="none")
                send_message(
                    chat_id,
                    safe_text(lang, "select_lang"),
                    lang_keyboard()
                )
                return "OK", 200

            if chat_id != ADMIN_ID:
                if not check_membership(chat_id):
                    send_message(
                        chat_id,
                        safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID),
                        join_keyboard()
                    )
                    return "OK", 200

            try:
                handled = handle_state_message(chat_id, text, user)
                if handled:
                    return "OK", 200
            except Exception as e:
                logger.error(f"State message error: {e}")
                send_message(chat_id, "⚠️ خطایی در پردازش پیام رخ داد. لطفاً دوباره تلاش کنید.")
                update_user(chat_id, state="none")
                return "OK", 200

            hour = datetime.now().hour
            if 5 <= hour < 12:
                greeting = "صبح بخیر 🌅"
            elif 12 <= hour < 17:
                greeting = "ظهر بخیر ☀️"
            elif 17 <= hour < 21:
                greeting = "عصر بخیر 🌇"
            else:
                greeting = "شب بخیر 🌙"
            
            welcome_text = f"""{greeting} {first_name} جان! 😍

به ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.

✨ اینجا همراه همیشگی تو در مسیر نور و معرفت است:
• جستجو در قرآن با ترجمه 📖
• هوش مصنوعی پاسخ‌گو 🤖
• مقالات علمی 📚
• حدیث و ذکر روزانه 🕊️
• قرآن در لحظه با ترجمه ✨
• پیشنهاد و انتقاد با امتیاز ⭐

👇 از منوی زیبای زیر استفاده کن:"""
            send_message(chat_id, welcome_text, main_menu(chat_id, lang))
            return "OK", 200

        elif "callback_query" in data:
            cb = data["callback_query"]
            cb_id = cb.get("id")
            cb_data = cb.get("data", "")
            cb_message = cb.get("message", {})
            chat = cb_message.get("chat", {})
            sender = cb.get("from", {})

            chat_id = chat.get("id")
            first_name = sender.get("first_name", "زندگی")

            if not chat_id:
                return "OK", 200

            chat_id = int(chat_id)
            ensure_user(chat_id, first_name)
            update_user(chat_id, name=first_name)

            user = get_user(chat_id)
            lang = user["lang"]

            answer_callback(cb_id)

            # ===========================
            # تغییر زبان
            # ===========================
            if cb_data.startswith("setlang_"):
                new_lang = cb_data.replace("setlang_", "").strip()
                if new_lang not in LANGS:
                    new_lang = "fa"

                update_user(chat_id, lang=new_lang, state="none")
                user = get_user(chat_id)
                lang = user["lang"]

                if chat_id != ADMIN_ID and not check_membership(chat_id):
                    send_message(
                        chat_id,
                        safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID),
                        join_keyboard()
                    )
                else:
                    hour = datetime.now().hour
                    if 5 <= hour < 12:
                        greeting = "صبح بخیر 🌅"
                    elif 12 <= hour < 17:
                        greeting = "ظهر بخیر ☀️"
                    elif 17 <= hour < 21:
                        greeting = "عصر بخیر 🌇"
                    else:
                        greeting = "شب بخیر 🌙"
                    
                    welcome_text = f"{greeting} {first_name} جان! 😍\n\nبه ربات کانون قرآن و عترت خوش آمدی.\nاز منوی زیر استفاده کن:"
                    send_message(chat_id, welcome_text, main_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # تأیید عضویت
            # ===========================
            if cb_data == "check_join":
                if check_membership(chat_id):
                    send_message(
                        chat_id,
                        safe_text(lang, "joined_success"),
                        main_menu(chat_id, lang)
                    )
                else:
                    send_message(
                        chat_id,
                        safe_text(lang, "not_joined_yet"),
                        join_keyboard()
                    )
                return "OK", 200

            # ===========================
            # بازگشت به منوی اصلی
            # ===========================
            if cb_data == "back_main":
                update_user(chat_id, state="none")
                hour = datetime.now().hour
                if 5 <= hour < 12:
                    greeting = "صبح بخیر 🌅"
                elif 12 <= hour < 17:
                    greeting = "ظهر بخیر ☀️"
                elif 17 <= hour < 21:
                    greeting = "عصر بخیر 🌇"
                else:
                    greeting = "شب بخیر 🌙"
                
                send_message(
                    chat_id,
                    f"{greeting} {first_name} جان! 🍃\nبه منوی اصلی خوش اومدی.",
                    main_menu(chat_id, lang)
                )
                return "OK", 200

            # ===========================
            # بررسی عضویت
            # ===========================
            if chat_id != ADMIN_ID and not check_membership(chat_id):
                send_message(
                    chat_id,
                    safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID),
                    join_keyboard()
                )
                return "OK", 200

            # ===========================
            # پنل ادمین
            # ===========================
            if cb_data == "admin_panel":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                if not FEATURES["admin_panel"]:
                    send_message(chat_id, "🔧 پنل ادمین در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                
                conn = db_conn()
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM feedbacks WHERE status='pending'")
                pending_feedback = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM error_logs WHERE created_at > datetime('now', '-7 days')")
                recent_errors = cur.fetchone()[0]
                conn.close()
                
                admin_text = f"""🛠️ <b>پنل ادمین</b>

📊 آمار کلی:
👥 کاربران: {total_users}
📩 انتقادات در انتظار: {pending_feedback}
🏆 برترین امتیاز: {get_highest_score()}
⚠️ خطاهای اخیر: {recent_errors}

📌 از منوی زیر مدیریت کن:"""
                send_message(chat_id, admin_text, admin_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # آمار ادمین
            # ===========================
            if cb_data == "admin_stats":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                conn = db_conn()
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM feedbacks WHERE status='pending'")
                pending_feedback = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM feedbacks")
                total_feedback = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM sent_messages WHERE created_at > datetime('now', '-7 days')")
                recent_sent = cur.fetchone()[0]
                conn.close()
                
                stats_text = f"""📊 <b>آمار کامل ربات</b>

👥 کل کاربران: {total_users}
📩 انتقادات در انتظار: {pending_feedback}
📝 کل انتقادات: {total_feedback}
📨 پیام‌های ارسالی (۷ روز): {recent_sent}
🏆 برترین امتیاز: {get_highest_score()}

📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
                send_message(chat_id, stats_text, admin_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # لیست انتقادات
            # ===========================
            if cb_data == "admin_feedbacks":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                conn = db_conn()
                cur = conn.cursor()
                cur.execute("SELECT id, user_name, content, score, created_at FROM feedbacks WHERE status='pending' ORDER BY id DESC LIMIT 10")
                feedbacks = cur.fetchall()
                conn.close()
                
                if feedbacks:
                    msg = "📩 لیست انتقادات و پیشنهادات:\n\n"
                    for f in feedbacks:
                        msg += f"📌 {f[1]}\n📝 {f[2][:100]}...\n⭐ امتیاز: {f[3]}\n📅 {f[4]}\n\n"
                    send_message(chat_id, msg, admin_menu(chat_id, lang))
                else:
                    send_message(chat_id, "📩 هیچ انتقاد یا پیشنهاد جدیدی وجود ندارد.", admin_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # ارسال همگانی
            # ===========================
            if cb_data == "admin_broadcast":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                if not FEATURES["broadcast"]:
                    send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", admin_menu(chat_id, lang))
                    return "OK", 200
                
                update_user(chat_id, state="waiting_broadcast")
                send_message(chat_id, safe_text(lang, "broadcast_prompt"), back_menu_keyboard(lang))
                return "OK", 200

            # ===========================
            # لیست کاربران
            # ===========================
            if cb_data == "admin_users":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                users = get_all_users(20)
                if users:
                    msg = "👥 لیست کاربران (۲۰ نفر برتر):\n\n"
                    for i, (uid, name, score) in enumerate(users, 1):
                        msg += f"{i}. {name} — {score} امتیاز\n"
                    send_message(chat_id, msg, admin_menu(chat_id, lang))
                else:
                    send_message(chat_id, "👥 هنوز کاربری ثبت نشده است.", admin_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # تنظیمات زمان‌بندی
            # ===========================
            if cb_data == "admin_schedule":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                schedule_status = "فعال ✅" if FEATURES["daily_posts"] else "غیرفعال ❌"
                times = "۸:۰۰ صبح، ۱۲:۰۰ ظهر، ۱۸:۰۰ عصر"
                
                send_message(chat_id, f"""⏰ <b>تنظیمات زمان‌بندی</b>

وضعیت: {schedule_status}
زمان‌های ارسال: {times}

📌 برای تغییر وضعیت، از دکمه «کنترل ویژگی‌ها» استفاده کنید.
""", admin_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # کنترل ویژگی‌ها
            # ===========================
            if cb_data == "admin_features":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                features_text = "⚙️ <b>کنترل ویژگی‌ها</b>\n\n"
                for key, value in FEATURES.items():
                    status = "✅" if value else "❌"
                    features_text += f"{status} {key}\n"
                
                features_text += "\n📌 برای تغییر، لطفاً از ادمین اصلی درخواست کنید."
                send_message(chat_id, features_text, admin_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # گزارش خطاها
            # ===========================
            if cb_data == "admin_logs":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                
                conn = db_conn()
                cur = conn.cursor()
                cur.execute("SELECT error_type, error_message, created_at FROM error_logs ORDER BY id DESC LIMIT 10")
                logs = cur.fetchall()
                conn.close()
                
                if logs:
                    msg = "📋 <b>گزارش خطاهای اخیر</b>\n\n"
                    for log in logs:
                        msg += f"🔴 {log[0]}\n📝 {log[1][:100]}...\n📅 {log[2]}\n\n"
                    send_message(chat_id, msg, admin_menu(chat_id, lang))
                else:
                    send_message(chat_id, "📋 هیچ خطایی ثبت نشده است.", admin_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # دکمه‌های منوی اصلی
            # ===========================
            if cb_data.startswith("menu_"):
                action = cb_data.replace("menu_", "")
                
                if action == "search_quran":
                    if not FEATURES["quran_search"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    update_user(chat_id, state="waiting_quran_search")
                    send_message(chat_id, safe_text(lang, "search_quran_prompt"), back_menu_keyboard(lang))
                
                elif action == "ai":
                    if not FEATURES["deepseek_ai"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    update_user(chat_id, state="waiting_ai")
                    send_message(chat_id, safe_text(lang, "ai_prompt"), back_menu_keyboard(lang))
                
                elif action == "articles":
                    if not FEATURES["articles_search"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    update_user(chat_id, state="waiting_article")
                    send_message(chat_id, safe_text(lang, "article_prompt"), back_menu_keyboard(lang))
                
                elif action == "hadith":
                    if not FEATURES["hadith_dhikr"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    item = random.choice(HADITHS_WITH_DHIKR)
                    msg = f"""🕊️ <b>حدیث روز</b>

{item['hadith']}

🔹 <b>ذکر روزانه:</b>
{item['dhikr']}

💚 با یاد خدا دل‌ها آرام می‌گیرد."""
                    send_message(chat_id, msg, main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)
                
                elif action == "instant_quran":
                    if not FEATURES["instant_quran"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    item = random.choice(INSTANT_QURAN_FULL)
                    msg = f"""📖 <b>قرآن در لحظه</b>

<b>{item['surah']} (آیه {item['verse']})</b>

{item['arabic']}

✨ {item['trans']}

💚 هر لحظه با قرآن، هر لحظه با نور."""
                    send_message(chat_id, msg, main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)
                
                elif action == "events":
                    send_message(chat_id, safe_text(lang, "events_text"), main_menu(chat_id, lang))
                
                elif action == "feedback":
                    if not FEATURES["feedback_system"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    update_user(chat_id, state="waiting_feedback")
                    send_message(chat_id, "📝 لطفاً پیشنهاد یا انتقاد خود را بنویسید.\n💡 برای دریافت امتیاز، پیشنهادتان دقیق و تأثیرگذار باشد.", back_menu_keyboard(lang))
                
                elif action == "admin_msg":
                    update_user(chat_id, state="waiting_admin_msg")
                    send_message(chat_id, safe_text(lang, "admin_msg_prompt"), back_menu_keyboard(lang))
                
                elif action == "stats":
                    latest_user = get_user(chat_id)
                    send_message(
                        chat_id,
                        safe_text(lang, "stats", 
                            name=first_name,
                            score=latest_user["score"],
                            search_count=latest_user["search_count"],
                            streak=latest_user["streak"],
                            feedback_score=latest_user["feedback_score"],
                            join_date=latest_user["join_date"]
                        ),
                        main_menu(chat_id, lang)
                    )
                
                elif action == "league":
                    if not FEATURES["leaderboard"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    top_users = get_leaderboard(10)
                    if top_users:
                        leaderboard = ""
                        medals = ["🥇", "🥈", "🥉"]
                        for i, (name, score) in enumerate(top_users, 1):
                            if i <= 3:
                                leaderboard += f"{medals[i-1]} {name} — {score} امتیاز\n"
                            else:
                                leaderboard += f"{i}. {name} — {score} امتیاز\n"
                    else:
                        leaderboard = "هنوز کاربری در لیگ قرآنی ثبت نشده است.\n\n🌟 اولین نفر باش!"
                    
                    send_message(
                        chat_id,
                        safe_text(lang, "league_text", leaderboard=leaderboard),
                        main_menu(chat_id, lang)
                    )
                
                elif action == "scorecard":
                    rank = get_user_rank(chat_id)
                    latest_user = get_user(chat_id)
                    send_message(
                        chat_id,
                        safe_text(lang, "scorecard_text",
                            name=first_name,
                            score=latest_user["score"],
                            rank=rank,
                            search_count=latest_user["search_count"],
                            streak=latest_user["streak"],
                            feedback_score=latest_user["feedback_score"]
                        ),
                        main_menu(chat_id, lang)
                    )
                
                elif action == "change_lang":
                    send_message(chat_id, safe_text(lang, "select_lang"), lang_keyboard())
                
                elif action == "daily_toggle":
                    if not FEATURES["daily_receive"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    current = user.get("receive_daily", 0)
                    new_value = 0 if current == 1 else 1
                    update_user(chat_id, receive_daily=new_value)
                    if new_value == 1:
                        send_message(chat_id, safe_text(lang, "daily_enable"), main_menu(chat_id, lang))
                    else:
                        send_message(chat_id, safe_text(lang, "daily_disable"), main_menu(chat_id, lang))
                
                elif action == "about":
                    send_message(chat_id, safe_text(lang, "about"), main_menu(chat_id, lang))
                
                else:
                    send_message(chat_id, safe_text(lang, "under_construction"), main_menu(chat_id, lang))

            return "OK", 200

        return "OK", 200

    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"WEBHOOK ERROR: {error_msg}\n{traceback_str}")
        log_error("webhook_error", error_msg, traceback_str)
        return "OK", 200

# =========================================================
# ۱۹. اجرای استارتاپ و سرور وب
# =========================================================
def startup():
    """راه‌اندازی اولیه ربات"""
    try:
        init_db()
        load_library()
        
        # راه‌اندازی اسکجولر روزانه (۳ زمان)
        if FEATURES["daily_posts"]:
            scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("🟢 اسکژولر روزانه (۳ زمان) راه‌اندازی شد.")
        else:
            logger.info("🟡 اسکژولر روزانه غیرفعال است.")
        
        logger.info("🟢 ربات با موفقیت راه‌اندازی شد.")
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی: {e}")

startup()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 ربات روی پورت {port} در حال اجراست...")
    app.run(host="0.0.0.0", port=port, debug=False)
