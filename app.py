# -*- coding: utf-8 -*-
import os
import sqlite3
import random
import requests
import json
import threading
import time
import re
from datetime import datetime
from flask import Flask, request, jsonify

# استفاده از thefuzz فقط در صورت نصب بودن
try:
    from thefuzz import fuzz, process
    FUZZ_AVAILABLE = True
except ImportError:
    FUZZ_AVAILABLE = False
    print("⚠️ thefuzz نصب نیست. جستجوی فازی غیرفعال است.")

app = Flask(__name__)

# =========================================================
# ۱. تنظیمات و متغیرهای محیطی اصلی (اصلاح شده)
# =========================================================
TOKEN = os.getenv("BOT_TOKEN", "")
if not TOKEN:
    print("⚠️ BOT_TOKEN تنظیم نشده است! ربات کار نخواهد کرد.")

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
# ۲. داده‌های اولیه و نمونه (Seed Data)
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
    {"index": 15, "surah": "نور", "verse": 35, "text": "اللَّهُ نُورُ السَّمَاوَاتِ وَالْأَرْضِ", "trans": "خداوند نور آسمان‌ها و زمین است"}
]

DEFAULT_NAHJ_SEED = [
    {"index": 1, "type": "خطبه", "number": 1, "text": "الْحَمْدُ لِلَّهِ الَّذِی لَا یَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ", "trans": "ستایش خدایی را که سخنوران در ستودن او فرومانند"},
    {"index": 2, "type": "خطبه", "number": 2, "text": "صِرَاطًا مُسْتَقِیمًا دَعَا إِلَیْهِ فِی کِتَابِهِ", "trans": "راه راست را در کتابش به آن فرا خوانده است"},
    {"index": 3, "type": "حکمت", "number": 1, "text": "كُنْ فِي الْفِتْنَةِ كَابْنِ اللَّبُونِ لاَ ظَهْرٌ فَيُرْكَبَ، وَلاَ ضَرْعٌ فَيُحْلَبَ", "trans": "در فتنه‌ها چونان شتر دو ساله باش، نه پشتی دارد که سوار شوند و نه پستانی که بدوشند"},
    {"index": 4, "type": "حکمت", "number": 5, "text": "مَنْ أَبْطَأَ بِهِ عَمَلُهُ لَمْ يُسْرِعْ بِهِ نَسَبُهُ", "trans": "کسی که عملش او را کند کرد، نسبش او را سریع نمی‌کند"},
    {"index": 5, "type": "حکمت", "number": 10, "text": "لَا غِنَى كَالْعَقْلِ، وَلَا فَقْرَ كَالْجَهْلِ", "trans": "هیچ بی‌نیازی چون خرد نیست و هیچ فقری چون جهل نیست"},
    {"index": 6, "type": "نامه", "number": 31, "text": "يَا بُنَيَّ اجْعَلْ نَفْسَكَ مِيزَاناً فِيما بَيْنَكَ وَبَيْنَ غَيْرِكَ", "trans": "پسرم، خویشتن را میان خود و دیگران ترازویی قرار ده"},
    {"index": 7, "type": "نامه", "number": 53, "text": "لَا تَكُونَنَّ كَالسَّبُعِ الَّذِي يَأْكُلُ مِنْ حَيْثُ يُمْكِنُهُ", "trans": "چون درنده‌ای مباش که هرجا ممکن شود می‌خورد"},
    {"index": 8, "type": "حکمت", "number": 15, "text": "فَضْلُ الْعِلْمِ خَيْرٌ مِنْ فَضْلِ الْمَالِ", "trans": "برتری دانش بهتر از برتری مال است"},
    {"index": 9, "type": "حکمت", "number": 20, "text": "مَنْ كَثُرَ هَمُّهُ مَرِضَ جَسَدُهُ", "trans": "هر که اندوهش بسیار باشد، بدنش بیمار شود"},
    {"index": 10, "type": "خطبه", "number": 10, "text": "تَبْدَأُ الْأُمُورُ فِي آخِرِ الزَّمَانِ بِالْفِتَنِ", "trans": "در آخرالزمان کارها با فتنه‌ها آغاز می‌شود"}
]

DEFAULT_SAHIFEH_SEED = [
    {"index": 1, "dua": 1, "title": "در ستایش پروردگار", "text": "الْحَمْدُ لِلَّهِ الْأَوَّلِ بلا أَوَّلٍ كَانَ قَبْلَهُ", "trans": "ستایش خدای را که نخستین است و پیش از او نخستینی نبوده"},
    {"index": 2, "dua": 2, "title": "درود بر محمد و آلش", "text": "اللَّهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ عَبْدِكَ وَ رَسُولِكَ", "trans": "بار خدایا بر محمد بنده و فرستاده خود درود فرست"},
    {"index": 3, "dua": 20, "title": "دعای مکارم الاخلاق", "text": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَ آلِهِ ، وَ بَلِّغْ بِإِیمَانِی أَکْمَلَ الْإِیمَانِ", "trans": "بار خدایا بر محمد و آلش درود فرست، و ایمان مرا به کامل‌ترین مرتبه ایمان برسان"},
    {"index": 4, "dua": 5, "title": "دعای روز عرفه", "text": "اللَّهُمَّ لَكَ الْحَمْدُ كَمَا خَلَقْتَنِي فَجَعَلْتَنِي سَمِيعاً", "trans": "بار خدایا ستایش تو راست همانگونه که مرا آفریدی و شنوا ساختی"},
    {"index": 5, "dua": 10, "title": "دعای پناه بردن از بلاها", "text": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنْ جَهْدِ الْبَلَاءِ", "trans": "بار خدایا به تو پناه می‌برم از سختی بلا"},
    {"index": 6, "dua": 15, "title": "دعای شکرگزاری", "text": "اللَّهُمَّ إِنَّ شُكْرِي إِيَّاكَ قَصِيرٌ عَنْ بُلُوغِ مَا أَنْعَمْتَ", "trans": "بار خدایا شکر من برای نعمت‌هایت کوتاه است از رسیدن به آن"},
    {"index": 7, "dua": 25, "title": "دعای توبه", "text": "اللَّهُمَّ إِنِّي أَتُوبُ إِلَيْكَ مِنْ ذُنُوبِي", "trans": "بار خدایا از گناهانم به تو توبه می‌کنم"},
    {"index": 8, "dua": 30, "title": "دعای طلب رزق", "text": "اللَّهُمَّ ارْزُقْنِي رِزْقاً وَاسِعاً حَلَالًا", "trans": "بار خدایا روزی وسیع و حلال به من عطا کن"},
    {"index": 9, "dua": 40, "title": "دعای سلامتی", "text": "اللَّهُمَّ أَنْتَ السَّلَامُ وَمِنْكَ السَّلَامُ", "trans": "بار خدایا تو سلامتی و از توست سلامتی"},
    {"index": 10, "dua": 50, "title": "دعای ختم", "text": "اللَّهُمَّ اخْتِمْ لَنَا بِالسَّعَادَةِ", "trans": "بار خدایا سرانجام ما را به سعادت ختم فرما"}
]

# =========================================================
# ۳. احادیث و آیات تصادفی
# =========================================================
HADITHS = [
    "پیامبر اکرم (ص): بهترین شما کسی است که قرآن را بیاموزد و به دیگران یاد دهد. 🌸",
    "امام علی (ع): در قرآن بیندیشید که بهار دل‌هاست. ✨",
    "امام صادق (ع): قرآن عهد الهی با بندگان است؛ شایسته است هر روز در آن نظر شود. 📖",
    "خانه‌هایتان را با تلاوت قرآن نورانی کنید. 🕯️",
    "امام باقر (ع): هر کس قرآن را با صدای بلند بخواند، خداوند به او اجر شهید می‌دهد. 🌹",
    "پیامبر اکرم (ص): قرآن شفای دردهای شماست. 💚",
    "امام سجاد (ع): آیات قرآن برای دل‌ها نور و روشنایی است. ☀️",
    "امام رضا (ع): هر کس در قرآن تدبر کند، خداوند حکمت به او عطا کند. 📚"
]

INSTANT_QURAN = [
    "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ ❤️",
    "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا ✨",
    "لَا تَقْنَطُوا مِنْ رَحْمَةِ اللَّهِ 🌿",
    "وَهُوَ مَعَكُمْ أَيْنَ مَا كُنتُمْ 🤍",
    "إِنَّ اللَّهَ مَعَ الصَّابِرِينَ 💪",
    "وَتَوَاصَوْا بِالْحَقِّ وَتَوَاصَوْا بِالصَّبْرِ 🤝",
    "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً 🌺",
    "وَالْعَصْرِ إِنَّ الْإِنْسَانَ لَفِي خُسْرٍ ⏳"
]

# =========================================================
# ۴. توابع راه‌اندازی و مدیریت فایل‌های JSON
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
        print(f"🟢 کتابخانه بارگذاری شد: قرآن={len(QURAN_DATA)}, نهج={len(NAHJ_DATA)}, صحیفه={len(SAHIFEH_DATA)}")
    except Exception as e:
        print(f"🔴 خطا در بارگذاری فایل‌های کتابخانه: {e}")

# =========================================================
# ۵. مدیریت دیتابیس
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
    
    for book in ["quran", "nahj", "sahifeh"]:
        cur.execute("INSERT OR IGNORE INTO publish_state (book_name, last_index) VALUES (?, 0)", (book,))
    
    conn.commit()
    conn.close()
    print("🟢 دیتابیس راه‌اندازی شد.")

def get_user(chat_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, lang, score, search_count, streak, last_active, join_date, receive_daily, state FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "name": row[0] or "",
            "lang": row[1] if row[1] in ["fa", "en", "ar", "tr"] else "fa",
            "score": row[2] or 0,
            "search_count": row[3] or 0,
            "streak": row[4] or 0,
            "last_active": row[5] or "",
            "join_date": row[6] or "",
            "receive_daily": row[7] or 0,
            "state": row[8] or "none"
        }
    return {"name": "", "lang": "fa", "score": 0, "search_count": 0, "streak": 0, "last_active": "", "join_date": "", "receive_daily": 0, "state": "none"}

def ensure_user(chat_id, name=""):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (chat_id, name, lang, join_date, last_active)
        VALUES (?, ?, 'fa', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (chat_id, name))
    conn.commit()
    conn.close()

def update_user(chat_id, name=None, lang=None, score=None, search_count=None, streak=None, receive_daily=None, state=None, score_add=None, search_add=None):
    conn = db_conn()
    cur = conn.cursor()
    if name is not None:
        cur.execute("UPDATE users SET name=? WHERE chat_id=?", (name, chat_id))
    if lang is not None:
        safe_lang = lang if lang in ["fa", "en", "ar", "tr"] else "fa"
        cur.execute("UPDATE users SET lang=? WHERE chat_id=?", (safe_lang, chat_id))
    if score is not None:
        cur.execute("UPDATE users SET score=? WHERE chat_id=?", (score, chat_id))
    if search_count is not None:
        cur.execute("UPDATE users SET search_count=? WHERE chat_id=?", (search_count, chat_id))
    if streak is not None:
        cur.execute("UPDATE users SET streak=? WHERE chat_id=?", (streak, chat_id))
    if receive_daily is not None:
        cur.execute("UPDATE users SET receive_daily=? WHERE chat_id=?", (receive_daily, chat_id))
    if state is not None:
        cur.execute("UPDATE users SET state=? WHERE chat_id=?", (state, chat_id))
    if score_add is not None:
        cur.execute("UPDATE users SET score=score+? WHERE chat_id=?", (score_add, chat_id))
    if search_add is not None:
        cur.execute("UPDATE users SET search_count=search_count+? WHERE chat_id=?", (search_add, chat_id))
    cur.execute("UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def get_publish_index(book_name):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT last_index, last_publish_date FROM publish_state WHERE book_name = ?", (book_name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0, row[1] if row and row[1] else ""

def set_publish_index(book_name, index_value):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("UPDATE publish_state SET last_index = ?, last_publish_date = CURRENT_TIMESTAMP WHERE book_name = ?", (index_value, book_name))
    conn.commit()
    conn.close()

def get_leaderboard(limit=10):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT name, score 
        FROM users 
        WHERE score > 0 
        ORDER BY score DESC 
        LIMIT ?
    """, (limit,))
    users = cur.fetchall()
    conn.close()
    return users

def get_user_rank(chat_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) + 1 
        FROM users 
        WHERE score > (SELECT score FROM users WHERE chat_id = ?)
    """, (chat_id,))
    rank = cur.fetchone()[0]
    conn.close()
    return rank

def add_pending_content(content_type, content_text):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pending_content (content_type, content_text, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (content_type, content_text))
    conn.commit()
    conn.close()

def get_pending_content():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, content_type, content_text, created_at FROM pending_content WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row

def update_pending_status(content_id, status):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("UPDATE pending_content SET status = ? WHERE id = ?", (status, content_id))
    conn.commit()
    conn.close()

# =========================================================
# ۶. ابزارهای ارسال پیام به بله (اصلاح شده)
# =========================================================
def send_bale(method, data):
    if not TOKEN:
        print("⚠️ TOKEN تنظیم نشده")
        return {"ok": False, "error": "TOKEN not set"}
    
    url = f"{BASE_URL}/{method}"
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ BALE API status {response.status_code}: {response.text[:200]}")
            return {"ok": False, "error": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout در {method}")
        return {"ok": False, "error": "Timeout"}
    except Exception as e:
        print(f"❌ BALE API ERROR in {method}: {e}")
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
        for part in parts:
            send_message(chat_id, part, reply_markup if part == parts[0] else None)
        return {"ok": True}
    
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)  # اصلاح: تبدیل به JSON
    return send_bale("sendMessage", payload)

def send_message_with_retry(chat_id, text, reply_markup=None, max_retries=3):
    for attempt in range(max_retries):
        result = send_message(chat_id, text, reply_markup)
        if result and result.get("ok"):
            return result
        time.sleep(2 ** attempt)
    return None

# =========================================================
# ۷. سیستم چندزبانه (کامل)
# =========================================================
LANGS = {
    "fa": {
        "select_lang": "🌍 لطفاً زبان موردنظرت را انتخاب کن:",
        "welcome": "سلام {name} عزیز! 😍\nبه ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش اومدی.\nیکی از گزینه‌های زیر رو انتخاب کن:",
        "force_join": "🌸 برای استفاده از خدمات ربات، لطفاً ابتدا عضو کانال کانون شو و بعد روی «تأیید عضویت ✅» بزن:\n{channel}",
        "joined_success": "✅ عضویتت تایید شد. خوش اومدی زندگی!",
        "not_joined_yet": "🥲 هنوز عضویتت تایید نشده. اول عضو کانال شو، بعد دوباره روی دکمه تأیید بزن.",
        "ai_prompt": "🤖 سوالت رو بپرس زندگی! من آماده‌ام.",
        "ai_wait": "⏳ یک لحظه صبر کن... دارم باهوش‌بازی درمیارم!",
        "admin_msg_prompt": "📩 پیامت رو بنویس تا مستقیم برای ادمین ارسال کنم:",
        "admin_msg_sent": "✅ پیامت با موفقیت برای ادمین ارسال شد.",
        "under_construction": "🚧 این بخش هنوز در حال تکمیل است. به‌زودی فعال می‌شود.",
        "stats": "📊 آمار تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}\n📅 تاریخ عضویت: {join_date}",
        "about": "این ربات توسط کانون قرآن و عترت دانشگاه علوم پزشکی شیراز طراحی شده است. ❤️\n\n📚 امکانات:\n• جستجو در قرآن، نهج‌البلاغه و صحیفه سجادیه\n• هوش مصنوعی DeepSeek\n• جستجوی وب و مقالات علمی\n• حدیث و ذکر روزانه\n• قرآن در لحظه\n• کارنامه و لیگ قرآنی\n• ارسال روزانه به کانال",
        "daily_enable": "✅ دریافت روزانه فعال شد. هر روز محتوای جدید برایت ارسال می‌شود.",
        "daily_disable": "❌ دریافت روزانه غیرفعال شد.",
        "daily_toggle": "🔔 دریافت روزانه",
        "back_to_menu": "🏠 بازگشت به منوی اصلی",
        "search_quran_prompt": "📖 کلمه یا عبارت قرآنی موردنظرت رو بفرست تا جستجو کنیم.",
        "web_search_prompt": "🌐 عبارت موردنظرت رو برای جستجوی وب بفرست.",
        "article_prompt": "📚 موضوع مقاله یا کلیدواژه‌ات رو بفرست.",
        "league_text": "🏆 لیگ قرآنی:\n\n{leaderboard}",
        "scorecard_text": "📋 کارنامه و رتبه تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n🎯 رتبه: {rank}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}",
        "events_text": "📢 رویدادها و مسابقات کانون:\n\n🔹 جشنواره قرآن و عترت\n🔹 مسابقات حفظ و مفاهیم قرآن\n🔹 کارگاه‌های تفسیر و تدبر\n🔹 برنامه‌های ماه رمضان\n\nبرای اطلاعات بیشتر به کانال مراجعه کنید.",
        "unknown_error": "⚠️ یک خطای کوچک رخ داد. دوباره امتحان کن.",
        "web_search_result": "🌐 نتایج جستجوی وب برای «{query}»:\n\n{results}",
        "article_result": "📚 نتایج جستجوی مقالات علمی برای «{query}»:\n\n{results}",
        "menu_labels": {
            "search_quran": "📖 جستجوی قرآن",
            "ai": "🤖 هوش مصنوعی",
            "web": "🌐 جستجوی وب",
            "articles": "📚 مقالات علمی",
            "hadith": "🕊️ حدیث و ذکر روز",
            "instant_quran": "✨ قرآن در لحظه",
            "events": "📢 رویدادها و مسابقات",
            "admin_msg": "📨 ارسال پیام به ادمین",
            "stats": "📊 آمار و امتیاز من",
            "league": "🏆 لیگ قرآنی",
            "scorecard": "📋 کارنامه و رتبه",
            "change_lang": "🌍 تغییر زبان",
            "daily_toggle": "🔔 دریافت روزانه",
            "about": "ℹ️ درباره ربات"
        }
    },
    "en": {
        "select_lang": "🌍 Please choose your language:",
        "welcome": "Hello {name}! 😍\nWelcome to the Quran & Etrat bot of SUMS.\nPlease choose an option:",
        "force_join": "🌸 To use the bot services, please join our channel first, then click Confirm ✅:\n{channel}",
        "joined_success": "✅ Membership confirmed. Welcome!",
        "not_joined_yet": "🥲 Your membership is not confirmed yet. Please join first and try again.",
        "ai_prompt": "🤖 Ask your question, dear!",
        "ai_wait": "⏳ Please wait... thinking smart!",
        "admin_msg_prompt": "📩 Send your message and I’ll forward it to admin:",
        "admin_msg_sent": "✅ Your message was sent to admin.",
        "under_construction": "🚧 This section is under construction.",
        "stats": "📊 Your stats:\n\n👤 Name: {name}\n🏆 Score: {score}\n📖 Searches: {search_count}\n🔥 Streak: {streak}\n📅 Join Date: {join_date}",
        "about": "This bot is designed by the Quran & Etrat Center of Shiraz University of Medical Sciences. ❤️",
        "daily_enable": "✅ Daily receive enabled. You will receive new content every day.",
        "daily_disable": "❌ Daily receive disabled.",
        "daily_toggle": "🔔 Daily Receive",
        "back_to_menu": "🏠 Back to main menu",
        "search_quran_prompt": "📖 Send a Quranic word or phrase to search.",
        "web_search_prompt": "🌐 Send your web search query.",
        "article_prompt": "📚 Send your article topic or keyword.",
        "league_text": "🏆 Quran League:\n\n{leaderboard}",
        "scorecard_text": "📋 Your scorecard and rank:\n\n👤 Name: {name}\n🏆 Score: {score}\n🎯 Rank: {rank}\n📖 Searches: {search_count}\n🔥 Streak: {streak}",
        "events_text": "📢 Events and contests:\n\n🔹 Quran and Etrat Festival\n🔹 Memorization contests\n🔹 Interpretation workshops\n🔹 Ramadan programs\n\nFor more info, visit our channel.",
        "unknown_error": "⚠️ A small error occurred. Please try again.",
        "web_search_result": "🌐 Web search results for «{query}»:\n\n{results}",
        "article_result": "📚 Scientific article results for «{query}»:\n\n{results}",
        "menu_labels": {
            "search_quran": "📖 Quran Search",
            "ai": "🤖 AI Assistant",
            "web": "🌐 Web Search",
            "articles": "📚 Scientific Articles",
            "hadith": "🕊️ Hadith & Daily Dhikr",
            "instant_quran": "✨ Instant Quran",
            "events": "📢 Events & Contests",
            "admin_msg": "📨 Message Admin",
            "stats": "📊 My Stats",
            "league": "🏆 Quran League",
            "scorecard": "📋 Scorecard & Rank",
            "change_lang": "🌍 Change Language",
            "daily_toggle": "🔔 Daily Receive",
            "about": "ℹ️ About Bot"
        }
    },
    "ar": {
        "select_lang": "🌍 يرجى اختيار اللغة:",
        "welcome": "مرحباً {name} 😍\nأهلاً بك في بوت كانون القرآن والعترة.\nاختر أحد الخيارات:",
        "force_join": "🌸 لاستخدام خدمات البوت، يرجى الانضمام أولاً إلى القناة ثم الضغط على تأكيد ✅:\n{channel}",
        "joined_success": "✅ تم تأكيد العضوية. أهلاً بك!",
        "not_joined_yet": "🥲 لم يتم تأكيد العضوية بعد. انضم أولاً ثم حاول مرة أخرى.",
        "ai_prompt": "🤖 اكتب سؤالك، أنا جاهز!",
        "ai_wait": "⏳ انتظر قليلاً... أفكر الآن!",
        "admin_msg_prompt": "📩 اكتب رسالتك ليتم إرسالها إلى المشرف:",
        "admin_msg_sent": "✅ تم إرسال رسالتك إلى المشرف.",
        "under_construction": "🚧 هذا القسم قيد التطوير.",
        "stats": "📊 إحصاءاتك:\n\n👤 الاسم: {name}\n🏆 النقاط: {score}\n📖 البحوث: {search_count}\n🔥 الأيام المتتالية: {streak}\n📅 تاريخ الانضمام: {join_date}",
        "about": "تم تصميم هذا البوت بواسطة كانون القرآن والعترة بجامعة شيراز للعلوم الطبية. ❤️",
        "daily_enable": "✅ تم تفعيل الاستلام اليومي. ستتلقى محتوى جديداً كل يوم.",
        "daily_disable": "❌ تم إلغاء تفعيل الاستلام اليومي.",
        "daily_toggle": "🔔 استلام يومي",
        "back_to_menu": "🏠 العودة إلى القائمة الرئيسية",
        "search_quran_prompt": "📖 أرسل كلمة أو عبارة للبحث في القرآن.",
        "web_search_prompt": "🌐 أرسل عبارة البحث.",
        "article_prompt": "📚 أرسل موضوع المقال أو الكلمة المفتاحية.",
        "league_text": "🏆 الدوري القرآني:\n\n{leaderboard}",
        "scorecard_text": "📋 كشف الدرجات والترتيب:\n\n👤 الاسم: {name}\n🏆 النقاط: {score}\n🎯 الترتيب: {rank}\n📖 البحوث: {search_count}\n🔥 الأيام المتتالية: {streak}",
        "events_text": "📢 الفعاليات والمسابقات:\n\n🔹 مهرجان القرآن والعترة\n🔹 مسابقات الحفظ\n🔹 ورش التفسير\n🔹 برامج شهر رمضان\n\nللمزيد، تفضل بزيارة قناتنا.",
        "unknown_error": "⚠️ حدث خطأ صغير. حاول مرة أخرى.",
        "web_search_result": "🌐 نتائج البحث على الويب لـ «{query}»:\n\n{results}",
        "article_result": "📚 نتائج البحث العلمي لـ «{query}»:\n\n{results}",
        "menu_labels": {
            "search_quran": "📖 البحث في القرآن",
            "ai": "🤖 الذكاء الاصطناعي",
            "web": "🌐 البحث في الويب",
            "articles": "📚 مقالات علمية",
            "hadith": "🕊️ حديث وذكر اليوم",
            "instant_quran": "✨ قرآن الآن",
            "events": "📢 الفعاليات والمسابقات",
            "admin_msg": "📨 إرسال رسالة للمشرف",
            "stats": "📊 إحصاءاتي",
            "league": "🏆 الدوري القرآني",
            "scorecard": "📋 كشف الدرجات والترتيب",
            "change_lang": "🌍 تغيير اللغة",
            "daily_toggle": "🔔 استلام يومي",
            "about": "ℹ️ حول البوت"
        }
    },
    "tr": {
        "select_lang": "🌍 Lütfen dilinizi seçin:",
        "welcome": "Merhaba {name}! 😍\nKur'an ve Etrat botuna hoş geldin.\nLütfen bir seçenek seç:",
        "force_join": "🌸 Bot hizmetlerini kullanmak için önce kanala katıl, sonra Onayla ✅ düğmesine bas:\n{channel}",
        "joined_success": "✅ Üyeliğin doğrulandı. Hoş geldin!",
        "not_joined_yet": "🥲 Üyeliğin henüz doğrulanmadı. Önce katıl, sonra tekrar dene.",
        "ai_prompt": "🤖 Sorunu yaz, hazırım!",
        "ai_wait": "⏳ Biraz bekle... düşünüyorum!",
        "admin_msg_prompt": "📩 Mesajını yaz, yöneticine ileteyim:",
        "admin_msg_sent": "✅ Mesajın yöneticiye gönderildi.",
        "under_construction": "🚧 Bu bölüm yapım aşamasında.",
        "stats": "📊 İstatistiklerin:\n\n👤 Ad: {name}\n🏆 Puan: {score}\n📖 Aramalar: {search_count}\n🔥 Seri: {streak}\n📅 Katılma Tarihi: {join_date}",
        "about": "Bu bot, Şiraz Tıp Bilimleri Üniversitesi Kur'an ve Etrat Merkezi tarafından hazırlanmıştır. ❤️",
        "daily_enable": "✅ Günlük alım etkinleştirildi. Her gün yeni içerik alacaksın.",
        "daily_disable": "❌ Günlük alım devre dışı bırakıldı.",
        "daily_toggle": "🔔 Günlük Alım",
        "back_to_menu": "🏠 Ana menüye dön",
        "search_quran_prompt": "📖 Aramak için bir kelime veya ifade gönder.",
        "web_search_prompt": "🌐 Web arama sorgunu gönder.",
        "article_prompt": "📚 Makale konusu veya anahtar kelime gönder.",
        "league_text": "🏆 Kur'an Ligi:\n\n{leaderboard}",
        "scorecard_text": "📋 Karnen ve sıralaman:\n\n👤 Ad: {name}\n🏆 Puan: {score}\n🎯 Sıra: {rank}\n📖 Aramalar: {search_count}\n🔥 Seri: {streak}",
        "events_text": "📢 Etkinlikler ve yarışmalar:\n\n🔹 Kur'an ve Etrat Festivali\n🔹 Ezber yarışmaları\n🔹 Tefsir çalıştayları\n🔹 Ramazan programları\n\nDetaylar için kanalımızı ziyaret edin.",
        "unknown_error": "⚠️ Küçük bir hata oluştu. Tekrar dene.",
        "web_search_result": "🌐 «{query}» için web arama sonuçları:\n\n{results}",
        "article_result": "📚 «{query}» için bilimsel makale sonuçları:\n\n{results}",
        "menu_labels": {
            "search_quran": "📖 Kur'an Arama",
            "ai": "🤖 Yapay Zeka",
            "web": "🌐 Web Arama",
            "articles": "📚 Bilimsel Makaleler",
            "hadith": "🕊️ Hadis ve Günlük Zikir",
            "instant_quran": "✨ Anlık Kur'an",
            "events": "📢 Etkinlikler ve Yarışmalar",
            "admin_msg": "📨 Yöneticiye Mesaj",
            "stats": "📊 İstatistiklerim",
            "league": "🏆 Kur'an Ligi",
            "scorecard": "📋 Karne ve Sıralama",
            "change_lang": "🌍 Dili Değiştir",
            "daily_toggle": "🔔 Günlük Alım",
            "about": "ℹ️ Bot Hakkında"
        }
    }
}

def safe_lang_dict(lang_code):
    return LANGS.get(lang_code, LANGS["fa"])

def safe_text(lang_code, key, default=None):
    lang_dict = safe_lang_dict(lang_code)
    if key in lang_dict:
        return lang_dict[key]
    return default if default is not None else LANGS["fa"].get(key, key)

# =========================================================
# ۸. کیبوردهای اینلاین
# =========================================================
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
        [{"text": labels["search_quran"], "callback_data": "menu_search_quran"}],
        [{"text": labels["ai"], "callback_data": "menu_ai"}],
        [{"text": labels["web"], "callback_data": "menu_web"}],
        [{"text": labels["articles"], "callback_data": "menu_articles"}],
        [{"text": labels["hadith"], "callback_data": "menu_hadith"}],
        [{"text": labels["instant_quran"], "callback_data": "menu_instant_quran"}],
        [{"text": labels["events"], "callback_data": "menu_events"}],
        [{"text": labels["admin_msg"], "callback_data": "menu_admin_msg"}],
        [{"text": labels["stats"], "callback_data": "menu_stats"}],
        [{"text": labels["league"], "callback_data": "menu_league"}],
        [{"text": labels["scorecard"], "callback_data": "menu_scorecard"}],
        [{"text": labels["daily_toggle"], "callback_data": "menu_daily_toggle"}],
        [{"text": labels["change_lang"], "callback_data": "menu_change_lang"}],
        [{"text": labels["about"], "callback_data": "menu_about"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]
    
    if chat_id == ADMIN_ID:
        buttons.append([{"text": "🛠️ پنل ادمین", "callback_data": "admin_panel"}])
    
    return {"inline_keyboard": buttons}

# =========================================================
# ۹. عضویت اجباری کانال بله
# =========================================================
def check_membership(chat_id):
    if not CHANNEL_ID:
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
        print("Membership check error:", e)
        return False

# =========================================================
# ۱۰. اتصال هوش مصنوعی DeepSeek
# =========================================================
def ask_deepseek(question, lang):
    if not DEEPSEEK_KEY or DEEPSEEK_KEY == "YOUR_DEEPSEEK_API_KEY":
        return "کلید API هوش مصنوعی DeepSeek تعریف نشده است."

    language_name = {
        "fa": "Persian",
        "en": "English",
        "ar": "Arabic",
        "tr": "Turkish"
    }.get(lang, "Persian")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": f"You are a warm, respectful, accurate assistant for a Quranic student bot at Shiraz University of Medical Sciences. Reply in {language_name}. Keep the answer useful, friendly, and well-formatted. Use bullet points when helpful."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.7
    }

    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=40
        )
        data = res.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]
        print("DeepSeek unexpected response:", data)
        return "پاسخی از هوش مصنوعی دریافت نشد. لطفاً بعداً تلاش فرمایید."
    except Exception as e:
        print("DeepSeek error:", e)
        return "سیستم ارتباطی با هوش مصنوعی در حال حاضر با وقفه مواجه شده است."

# =========================================================
# ۱۱. سیستم جستجوی چندگانه
# =========================================================
def smart_search(data_list, query, key="text"):
    query = query.strip().lower()
    if not query:
        return []
    
    results = []
    for item in data_list:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("surah", "")),
            str(item.get("title", "")),
            str(item.get("type", ""))
        ]).lower()
        
        if query in search_text:
            results.append(item)
        elif FUZZ_AVAILABLE:
            score = fuzz.partial_ratio(query, search_text)
            if score > 60:
                results.append(item)
    
    seen = set()
    unique_results = []
    for item in results:
        item_key = str(item.get("index", "")) + str(item.get("text", ""))
        if item_key not in seen:
            seen.add(item_key)
            unique_results.append(item)
    
    return unique_results[:10]

def search_library(q, user_id):
    q = q.strip().lower()
    if not q:
        return []

    results = []
    
    for item in smart_search(QURAN_DATA, q):
        results.append(f"📘 قرآن ({item['surah']} - آیه {item['verse']}):\n{item['text']}\n🔹 ترجمه:\n{item['trans']}")

    for item in smart_search(NAHJ_DATA, q):
        results.append(f"📙 نهج‌البلاغه ({item['type']} {item['number']}):\n{item['text']}\n🔹 ترجمه:\n{item['trans']}")

    for item in smart_search(SAHIFEH_DATA, q):
        results.append(f"📗 صحیفه سجادیه ({item['title']}):\n{item['text']}\n🔹 ترجمه:\n{item['trans']}")

    return results[:10]

# =========================================================
# ۱۲. جستجوی وب (DuckDuckGo)
# =========================================================
def search_web(query):
    try:
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.post(url, data=data, headers=headers, timeout=15)
        
        results = []
        pattern = r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>'
        matches = re.findall(pattern, response.text, re.DOTALL)
        
        for link, title in matches[:5]:
            clean_title = re.sub(r'<.*?>', '', title).strip()
            if clean_title and link.startswith('http'):
                results.append(f"🔗 <a href='{link}'>{clean_title}</a>")
        
        return '\n\n'.join(results) if results else "نتیجه‌ای یافت نشد."
    except Exception as e:
        print(f"Web search error: {e}")
        return f"خطا در جستجوی وب: {e}"

# =========================================================
# ۱۳. جستجوی مقالات علمی (OpenAlex)
# =========================================================
def search_articles(query):
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
        print(f"Article search error: {e}")
        return f"خطا در جستجوی مقالات: {e}"

# =========================================================
# ۱۴. سیستم توزیع روزانه پست‌ها (اصلاح شده)
# =========================================================
def next_item(book_name, data_list):
    if not data_list:
        return None, 0
    
    current_idx, last_date = get_publish_index(book_name)
    
    # بررسی اینکه آیا امروز قبلاً ارسال شده
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

def send_daily_posts():
    try:
        q_item, q_idx = next_item("quran", QURAN_DATA)
        if q_item:
            q_msg = format_daily_message("quran", q_item)
            if q_msg:
                send_message(CHANNEL_ID, q_msg)
                set_publish_index("quran", q_idx)
                print("✅ قرآن روزانه ارسال شد.")
                time.sleep(3)
        
        n_item, n_idx = next_item("nahj", NAHJ_DATA)
        if n_item:
            n_msg = format_daily_message("nahj", n_item)
            if n_msg:
                send_message(CHANNEL_ID, n_msg)
                set_publish_index("nahj", n_idx)
                print("✅ نهج‌البلاغه روزانه ارسال شد.")
                time.sleep(3)
        
        s_item, s_idx = next_item("sahifeh", SAHIFEH_DATA)
        if s_item:
            s_msg = format_daily_message("sahifeh", s_item)
            if s_msg:
                send_message(CHANNEL_ID, s_msg)
                set_publish_index("sahifeh", s_idx)
                print("✅ صحیفه سجادیه روزانه ارسال شد.")
                time.sleep(3)
        
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT chat_id, name, lang FROM users WHERE receive_daily = 1")
        users = cur.fetchall()
        conn.close()
        
        for user in users:
            try:
                daily_msg = f"🌅 <b>پیام روزانه کانون قرآن</b>\n\n{q_msg or n_msg or s_msg}\n\n🙏 از همراهی شما سپاسگزاریم."
                send_message(user[0], daily_msg)
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ ارسال به {user[0]} ناموفق: {e}")
        
        print("✅ ارسال روزانه کامل شد.")
    except Exception as e:
        print(f"❌ خطا در ارسال روزانه: {e}")

def daily_scheduler():
    time.sleep(30)
    while True:
        try:
            send_daily_posts()
        except Exception as e:
            print(f"Scheduler error: {e}")
        time.sleep(24 * 60 * 60)

# =========================================================
# ۱۵. مدیریت پردازش وضعیت‌های خاص کاربر
# =========================================================
def handle_state_message(chat_id, text, user):
    lang = user["lang"]
    state = user["state"]
    name = user["name"] or "کاربر گرامی"

    if state == "waiting_ai":
        send_message(chat_id, safe_text(lang, "ai_wait"))
        answer = ask_deepseek(text, lang)
        send_message(chat_id, f"🤖 {answer}", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=2)
        return True

    if state == "waiting_admin_msg":
        send_message(
            ADMIN_ID,
            f"📩 پیام جدید از کاربر:\n\n👤 نام: {name}\n🆔 chat_id: {chat_id}\n💬 متن:\n{text}"
        )
        send_message(chat_id, safe_text(lang, "admin_msg_sent"), main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=1)
        return True

    if state == "waiting_quran_search":
        results = search_library(text, chat_id)
        if not results:
            send_message(chat_id, "نتیجه‌ای یافت نشد. 😔", main_menu(chat_id, lang))
        else:
            for r in results[:5]:
                send_message(chat_id, r)
            send_message(chat_id, "🌿 جستجو به پایان رسید.", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=1, search_add=1)
        return True

    if state == "waiting_web_search":
        send_message(chat_id, "🌐 در حال جستجو...")
        result = search_web(text)
        send_message(chat_id, safe_text(lang, "web_search_result").format(query=text, results=result), main_menu(chat_id, lang))
        update_user(chat_id, state="none")
        return True

    if state == "waiting_article":
        send_message(chat_id, "📚 در حال جستجوی مقالات...")
        result = search_articles(text)
        send_message(chat_id, safe_text(lang, "article_result").format(query=text, results=result), main_menu(chat_id, lang))
        update_user(chat_id, state="none")
        return True

    return False

# =========================================================
# ۱۶. توابع کمکی
# =========================================================
def get_user_count():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_highest_score():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(score) FROM users")
    score = cur.fetchone()[0]
    conn.close()
    return score or 0

# =========================================================
# ۱۷. مسیرهای تست و سلامت (اصلاح شده)
# =========================================================
@app.route("/", methods=["GET", "HEAD"])
def health():
    return jsonify({
        "status": "ok",
        "service": "labbayk_quranbot",
        "port": os.getenv("PORT", "10000"),
        "quran_records": len(QURAN_DATA),
        "nahj_records": len(NAHJ_DATA),
        "sahifeh_records": len(SAHIFEH_DATA),
        "total_users": get_user_count()
    }), 200

@app.route("/webhook", methods=["GET", "HEAD"])
def webhook_check():
    return jsonify({"status": "ok", "message": "Webhook is alive"}), 200

# =========================================================
# ۱۸. وب هوک و مدیریت یکپارچه درخواست‌ها (اصلاح شده)
# =========================================================
@app.route("/", methods=["POST"])
def webhook():
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

            if text == "/start" or text == "شروع":
                update_user(chat_id, state="none")
                send_message(
                    chat_id,
                    safe_text(lang, "select_lang", "لطفاً زبان خود را انتخاب کنید:"),
                    lang_keyboard()
                )
                return "OK", 200

            if chat_id != ADMIN_ID:
                if not check_membership(chat_id):
                    send_message(
                        chat_id,
                        safe_text(lang, "force_join").format(channel=CHANNEL_ID),
                        join_keyboard()
                    )
                    return "OK", 200

            handled = handle_state_message(chat_id, text, user)
            if handled:
                return "OK", 200

            send_message(
                chat_id,
                safe_text(lang, "welcome").format(name=first_name),
                main_menu(chat_id, lang)
            )
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

            if cb_id:
                answer_callback(cb_id)

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
                        safe_text(lang, "force_join").format(channel=CHANNEL_ID),
                        join_keyboard()
                    )
                else:
                    send_message(
                        chat_id,
                        safe_text(lang, "welcome").format(name=first_name),
                        main_menu(chat_id, lang)
                    )
                return "OK", 200

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

            if cb_data == "back_main":
                update_user(chat_id, state="none")
                send_message(
                    chat_id,
                    safe_text(lang, "welcome").format(name=first_name),
                    main_menu(chat_id, lang)
                )
                return "OK", 200

            if chat_id != ADMIN_ID and not check_membership(chat_id):
                send_message(
                    chat_id,
                    safe_text(lang, "force_join").format(channel=CHANNEL_ID),
                    join_keyboard()
                )
                return "OK", 200

            if cb_data == "admin_panel":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200

                admin_text = (
                    "🛠️ <b>پنل ادمین</b>\n\n"
                    f"📖 آیات قرآن: {len(QURAN_DATA)}\n"
                    f"📙 فرازهای نهج‌البلاغه: {len(NAHJ_DATA)}\n"
                    f"📗 ادعیه صحیفه: {len(SAHIFEH_DATA)}\n\n"
                    "📊 آمار کاربران:\n"
                    f"👥 کل کاربران: {get_user_count()}\n"
                    f"🏆 برترین امتیاز: {get_highest_score()}\n\n"
                    "🔧 برای ارسال همگانی:\n"
                    "دستور /broadcast [متن] را بفرستید."
                )
                send_message(chat_id, admin_text, main_menu(chat_id, lang))
                return "OK", 200

            if cb_data.startswith("menu_"):
                action = cb_data.replace("menu_", "")
                
                if action == "search_quran":
                    update_user(chat_id, state="waiting_quran_search")
                    send_message(chat_id, safe_text(lang, "search_quran_prompt"), back_menu_keyboard(lang))
                
                elif action == "ai":
                    update_user(chat_id, state="waiting_ai")
                    send_message(chat_id, safe_text(lang, "ai_prompt"), back_menu_keyboard(lang))
                
                elif action == "web":
                    update_user(chat_id, state="waiting_web_search")
                    send_message(chat_id, safe_text(lang, "web_search_prompt"), back_menu_keyboard(lang))
                
                elif action == "articles":
                    update_user(chat_id, state="waiting_article")
                    send_message(chat_id, safe_text(lang, "article_prompt"), back_menu_keyboard(lang))
                
                elif action == "hadith":
                    item = random.choice(HADITHS)
                    send_message(chat_id, f"🕊️ {item}", main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)
                
                elif action == "instant_quran":
                    item = random.choice(INSTANT_QURAN)
                    send_message(chat_id, f"✨ {item}", main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)
                
                elif action == "events":
                    send_message(chat_id, safe_text(lang, "events_text"), main_menu(chat_id, lang))
                
                elif action == "admin_msg":
                    update_user(chat_id, state="waiting_admin_msg")
                    send_message(chat_id, safe_text(lang, "admin_msg_prompt"), back_menu_keyboard(lang))
                
                elif action == "stats":
                    latest_user = get_user(chat_id)
                    send_message(
                        chat_id,
                        safe_text(lang, "stats").format(
                            name=first_name,
                            score=latest_user["score"],
                            search_count=latest_user["search_count"],
                            streak=latest_user["streak"],
                            join_date=latest_user["join_date"]
                        ),
                        main_menu(chat_id, lang)
                    )
                
                elif action == "league":
                    top_users = get_leaderboard(10)
                    if top_users:
                        leaderboard = ""
                        medals = ["🥇", "🥈", "🥉"]
                        for idx, (name, score) in enumerate(top_users, 1):
                            if idx <= 3:
                                leaderboard += f"{medals[idx-1]} {name} — {score} امتیاز\n"
                            else:
                                leaderboard += f"{idx}. {name} — {score} امتیاز\n"
                    else:
                        leaderboard = "هیچ کاربری در لیگ قرآنی ثبت نشده است."
                    
                    send_message(
                        chat_id,
                        safe_text(lang, "league_text").format(leaderboard=leaderboard),
                        main_menu(chat_id, lang)
                    )
                
                elif action == "scorecard":
                    rank = get_user_rank(chat_id)
                    latest_user = get_user(chat_id)
                    send_message(
                        chat_id,
                        safe_text(lang, "scorecard_text").format(
                            name=first_name,
                            score=latest_user["score"],
                            rank=rank,
                            search_count=latest_user["search_count"],
                            streak=latest_user["streak"]
                        ),
                        main_menu(chat_id, lang)
                    )
                
                elif action == "change_lang":
                    send_message(chat_id, safe_text(lang, "select_lang"), lang_keyboard())
                
                elif action == "daily_toggle":
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
        print(f"WEBHOOK ERROR: {e}")
        return "OK", 200

# =========================================================
# ۱۹. اجرای استارتاپ و سرور وب
# =========================================================
def startup():
    init_db()
    load_library()
    
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        sched_thread = threading.Thread(target=daily_scheduler, daemon=True)
        sched_thread.start()
        print("🟢 اسکژولر روزانه راه‌اندازی شد.")
    else:
        print("🟡 اسکژولر غیرفعال است. (ENABLE_SCHEDULER=false)")

startup()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 ربات روی پورت {port} در حال اجراست...")
    app.run(host="0.0.0.0", port=port, debug=False)
