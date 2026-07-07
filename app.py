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
        safe_lang = lang if lang in ["fa", "en", "ar", "tr"] else "fa"
        cur.execute("UPDATE users SET lang=? WHERE chat_id=?", (safe_lang, chat_id))
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
def send_bale(method, data):
    url = f"{BASE_URL}/{method}"
    try:
        response = requests.post(url, json=data, timeout=20)
        return response.json()
    except Exception as e:
        print(f"BALE API ERROR in {method}: {e}")
        return None

def answer_callback(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    send_bale("answerCallbackQuery", payload)

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return send_bale("sendMessage", payload)

# =========================================================
# ۶. سیستم چندزبانه (FA / EN / AR / TR)
# =========================================================
LANGS = {
    "fa": {
        "select_lang": "🌍 لطفاً زبان موردنظرت را انتخاب کن:",
       "welcome": """سلام {name} عزیز! 😍
به کانون قرآن و عترت خوش آمدید."""
به ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش اومدی.
یکی از گزینه‌های زیر رو انتخاب کن:",
        "force_join": "🌸 برای استفاده از خدمات ربات، لطفاً ابتدا عضو کانال کانون شو و بعد روی «تأیید عضویت ✅» بزن:
{channel}",
        "joined_success": "✅ عضویتت تایید شد. خوش اومدی زندگی!",
        "not_joined_yet": "🥲 هنوز عضویتت تایید نشده. اول عضو کانال شو، بعد دوباره روی دکمه تأیید بزن.",
        "ai_prompt": "🤖 سوالت رو بپرس زندگی! من آماده‌ام.",
        "ai_wait": "⏳ یک لحظه صبر کن... دارم باهوش‌بازی درمیارم!",
        "admin_msg_prompt": "📩 پیامت رو بنویس تا مستقیم برای ادمین ارسال کنم:",
        "admin_msg_sent": "✅ پیامت با موفقیت برای ادمین ارسال شد.",
        "under_construction": "🚧 این بخش هنوز در حال تکمیل است. به‌زودی فعال می‌شود.",
        "stats": "📊 آمار تو:

👤 نام: {name}
🏆 امتیاز: {score}",
        "about": "این ربات توسط کانون قرآن و عترت دانشگاه علوم پزشکی شیراز طراحی شده است. ❤️",
        "menu": [
            "📖 جستجوی قرآن",
            "🤖 هوش مصنوعی",
            "🌐 جستجوی وب",
            "📚 مقالات علمی",
            "🕊️ حدیث و ذکر روز",
            "✨ قرآن در لحظه",
            "📢 رویدادها و مسابقات",
            "📨 ارسال پیام به ادمین",
            "📊 آمار و امتیاز من",
            "🏆 لیگ قرآنی",
            "📋 کارنامه و رتبه",
            "🌍 تغییر زبان"
        ],
        "search_quran_prompt": "📖 کلمه یا عبارت قرآنی موردنظرت رو بفرست تا جستجو کنیم.",
        "web_search_prompt": "🌐 عبارت موردنظرت رو برای جستجوی وب بفرست.",
        "article_prompt": "📚 موضوع مقاله یا کلیدواژه‌ات رو بفرست.",
        "league_text": "🏆 لیگ قرآنی به‌زودی فعال می‌شود. فعلاً در حال گرم‌کردن موتوریم 😄",
        "scorecard_text": "📋 کارنامه و رتبه تو به‌زودی اینجا نمایش داده می‌شود.",
        "events_text": "📢 رویدادها و مسابقات کانون خیلی زود اینجا قرار می‌گیرند.",
        "unknown_error": "⚠️ یک خطای کوچک رخ داد. دوباره امتحان کن.",
        "back_to_menu": "🏠 بازگشت به منوی اصلی"
    },
    "en": {
        "select_lang": "🌍 Please choose your language:",
        "welcome": "Hello {name}! 😍
Welcome to the Quran & Etrat bot of SUMS.
Please choose an option:",
        "force_join": "🌸 To use the bot services, please join our channel first, then click Confirm ✅:
{channel}",
        "joined_success": "✅ Membership confirmed. Welcome!",
        "not_joined_yet": "🥲 Your membership is not confirmed yet. Please join first and try again.",
        "ai_prompt": "🤖 Ask your question, dear!",
        "ai_wait": "⏳ Please wait... thinking smart!",
        "admin_msg_prompt": "📩 Send your message and I’ll forward it to admin:",
        "admin_msg_sent": "✅ Your message was sent to admin.",
        "under_construction": "🚧 This section is under construction.",
        "stats": "📊 Your stats:

👤 Name: {name}
🏆 Score: {score}",
        "about": "This bot is designed by the Quran & Etrat Center of Shiraz University of Medical Sciences. ❤️",
        "menu": [
            "📖 Quran Search",
            "🤖 AI Assistant",
            "🌐 Web Search",
            "📚 Scientific Articles",
            "🕊️ Hadith & Daily Dhikr",
            "✨ Instant Quran",
            "📢 Events & Contests",
            "📨 Message Admin",
            "📊 My Stats",
            "🏆 Quran League",
            "📋 Scorecard & Rank",
            "🌍 Change Language"
        ],
        "search_quran_prompt": "📖 Send a Quranic word or phrase to search.",
        "web_search_prompt": "🌐 Send your web search query.",
        "article_prompt": "📚 Send your article topic or keyword.",
        "league_text": "🏆 Quran League will be available soon.",
        "scorecard_text": "📋 Your scorecard and rank will appear here soon.",
        "events_text": "📢 Events and contests will be announced here soon.",
        "unknown_error": "⚠️ A small error occurred. Please try again.",
        "back_to_menu": "🏠 Back to main menu"
    },
    "ar": {
        "select_lang": "🌍 يرجى اختيار اللغة:",
        "welcome": "مرحباً {name} 😍
أهلاً بك في بوت كانون القرآن والعترة.
اختر أحد الخيارات:",
        "force_join": "🌸 لاستخدام خدمات البوت، يرجى الانضمام أولاً إلى القناة ثم الضغط على تأكيد ✅:
{channel}",
        "joined_success": "✅ تم تأكيد العضوية. أهلاً بك!",
        "not_joined_yet": "🥲 لم يتم تأكيد العضوية بعد. انضم أولاً ثم حاول مرة أخرى.",
        "ai_prompt": "🤖 اكتب سؤالك، أنا جاهز!",
        "ai_wait": "⏳ انتظر قليلاً... أفكر الآن!",
        "admin_msg_prompt": "📩 اكتب رسالتك ليتم إرسالها إلى المشرف:",
        "admin_msg_sent": "✅ تم إرسال رسالتك إلى المشرف.",
        "under_construction": "🚧 هذا القسم قيد التطوير.",
        "stats": "📊 إحصاءاتك:

👤 الاسم: {name}
🏆 النقاط: {score}",
        "about": "تم تصميم هذا البوت بواسطة كانون القرآن والعترة بجامعة شيراز للعلوم الطبية. ❤️",
        "menu": [
            "📖 البحث في القرآن",
            "🤖 الذكاء الاصطناعي",
            "🌐 البحث في الويب",
            "📚 مقالات علمية",
            "🕊️ حديث وذكر اليوم",
            "✨ قرآن الآن",
            "📢 الفعاليات والمسابقات",
            "📨 إرسال رسالة للمشرف",
            "📊 إحصاءاتي",
            "🏆 الدوري القرآني",
            "📋 كشف الدرجات والترتيب",
            "🌍 تغيير اللغة"
        ],
        "search_quran_prompt": "📖 أرسل كلمة أو عبارة للبحث في القرآن.",
        "web_search_prompt": "🌐 أرسل عبارة البحث.",
        "article_prompt": "📚 أرسل موضوع المقال أو الكلمة المفتاحية.",
        "league_text": "🏆 الدوري القرآني سيتوفر قريباً.",
        "scorecard_text": "📋 سيظهر كشف الدرجات والترتيب هنا قريباً.",
        "events_text": "📢 ستظهر الفعاليات والمسابقات هنا قريباً.",
        "unknown_error": "⚠️ حدث خطأ صغير. حاول مرة أخرى.",
        "back_to_menu": "🏠 العودة إلى القائمة الرئيسية"
    },
    "tr": {
        "select_lang": "🌍 Lütfen dilinizi seçin:",
        "welcome": "Merhaba {name}! 😍
Kur'an ve Etrat botuna hoş geldin.
Lütfen bir seçenek seç:",
        "force_join": "🌸 Bot hizmetlerini kullanmak için önce kanala katıl, sonra Onayla ✅ düğmesine bas:
{channel}",
        "joined_success": "✅ Üyeliğin doğrulandı. Hoş geldin!",
        "not_joined_yet": "🥲 Üyeliğin henüz doğrulanmadı. Önce katıl, sonra tekrar dene.",
        "ai_prompt": "🤖 Sorunu yaz, hazırım!",
        "ai_wait": "⏳ Biraz bekle... düşünüyorum!",
        "admin_msg_prompt": "📩 Mesajını yaz, yöneticine ileteyim:",
        "admin_msg_sent": "✅ Mesajın yöneticiye gönderildi.",
        "under_construction": "🚧 Bu bölüm yapım aşamasında.",
        "stats": "📊 İstatistiklerin:

👤 Ad: {name}
🏆 Puan: {score}",
        "about": "Bu bot, Şiraz Tıp Bilimleri Üniversitesi Kur'an ve Etrat Merkezi tarafından hazırlanmıştır. ❤️",
        "menu": [
            "📖 Kur'an Arama",
            "🤖 Yapay Zeka",
            "🌐 Web Arama",
            "📚 Bilimsel Makaleler",
            "🕊️ Hadis ve Günlük Zikir",
            "✨ Anlık Kur'an",
            "📢 Etkinlikler ve Yarışmalar",
            "📨 Yöneticiye Mesaj",
            "📊 İstatistiklerim",
            "🏆 Kur'an Ligi",
            "📋 Karne ve Sıralama",
            "🌍 Dili Değiştir"
        ],
        "search_quran_prompt": "📖 Aramak için bir kelime veya ifade gönder.",
        "web_search_prompt": "🌐 Web arama sorgunu gönder.",
        "article_prompt": "📚 Makale konusu veya anahtar kelime gönder.",
        "league_text": "🏆 Kur'an Ligi yakında aktif olacak.",
        "scorecard_text": "📋 Karnen ve sıralaman yakında burada görünecek.",
        "events_text": "📢 Etkinlikler ve yarışmalar yakında burada olacak.",
        "unknown_error": "⚠️ Küçük bir hata oluştu. Tekrar dene.",
        "back_to_menu": "🏠 Ana menüye dön"
    }
}

HADITHS = [
    "پیامبر اکرم (ص): بهترین شما کسی است که قرآن را بیاموزد و به دیگران یاد دهد. 🌸",
    "امام علی (ع): در قرآن بیندیشید که بهار دل‌هاست. ✨",
    "امام صادق (ع): قرآن عهد الهی با بندگان است؛ شایسته است هر روز در آن نظر شود. 📖",
    "خانه‌هایتان را با تلاوت قرآن نورانی کنید. 🕯️"
]

INSTANT_QURAN = [
    "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ ❤️",
    "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا ✨",
    "لَا تَقْنَطُوا مِنْ رَحْمَةِ اللَّهِ 🌿",
    "وَهُوَ مَعَكُمْ أَيْنَ مَا كُنتُمْ 🤍"
]

def safe_lang_dict(lang_code):
    return LANGS.get(lang_code, LANGS["fa"])

def safe_text(lang_code, key, default=None):
    lang_dict = safe_lang_dict(lang_code)
    if key in lang_dict:
        return lang_dict[key]
    return default if default is not None else LANGS["fa"].get(key, key)

# =========================================================
# ۷. کیبوردهای اینلاین (۱۲ دکمه‌ای هوشمند)
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
            [
                {"text": "📢 ورود به کانال", "url": f"https://ble.ir/{channel_username}"}
            ],
            [
                {"text": "✅ تایید عضویت", "callback_data": "check_join"}
            ]
        ]
    }

def back_menu_keyboard(lang):
    text = safe_text(lang, "back_to_menu")
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": "back_main"}]
        ]
    }

def main_menu(chat_id, lang):
    menu_items = safe_lang_dict(lang)["menu"]
    buttons = []
    row = []
    
    # چیدمان ۲ دکمه در هر سطر برای ساخت منوی ۱۲ دکمه‌ای منظم
    for i, item in enumerate(menu_items):
        row.append({"text": item, "callback_data": f"menu_{i}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)

    # اتصال پنل مدیریت در صورت بودن کاربر به عنوان ادمین
    if chat_id == ADMIN_ID:
        buttons.append([
            {"text": "🛠️ پنل ادمین", "callback_data": "admin_panel"}
        ])

    return {"inline_keyboard": buttons}

# =========================================================
# ۸. عضویت اجباری کانال بله
# =========================================================
def check_membership(chat_id):
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
# ۹. اتصال هوش مصنوعی DeepSeek
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
                "content": f"You are a warm, respectful, accurate assistant for a Quranic student bot. Reply in {language_name}. Keep the answer useful and friendly."
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
# ۱۰. سیستم جستجوی چندگانه متنی در کل کتابخانه
# =========================================================
def search_library(q):
    q = q.strip().lower()
    results = []

    # جستجو در قرآن
    for item in QURAN_DATA:
        if q in item["text"].lower() or q in item["trans"].lower():
            results.append(f"📘 قرآن ({item['surah']} - آیه {item['verse']}):
{item['text']}
🔹 ترجمه:
{item['trans']}")

    # جستجو در نهج‌البلاغه
    for item in NAHJ_DATA:
        if q in item["text"].lower() or q in item["trans"].lower():
            results.append(f"📙 نهج‌البلاغه ({item['type']} {item['number']}):
{item['text']}
🔹 ترجمه:
{item['trans']}")

    # جستجو در صحیفه سجادیه
    for item in SAHIFEH_DATA:
        if q in item["text"].lower() or q in item["trans"].lower():
            results.append(f"📗 صحیفه سجادیه ({item['title']}):
{item['text']}
🔹 ترجمه:
{item['trans']}")

    return results

# =========================================================
# ۱۱. مدیریت پردازش وضعیت‌های خاص کاربر (State System)
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
            f"📩 پیام جدید از کاربر:

"
            f"👤 نام: {name}
"
            f"🆔 chat_id: {chat_id}
"
            f"💬 متن:
{text}"
        )
        send_message(chat_id, safe_text(lang, "admin_msg_sent"), main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=1)
        return True

    if state == "waiting_quran_search":
        res = search_library(text)
        if not res:
            send_message(chat_id, "نتیجه‌ای یافت نشد. 😔", main_menu(chat_id, lang))
        else:
            # ارسال حداکثر ۵ نتیجه برای پرهیز از طولانی شدن اسپم‌وار چت
            for r in res[:5]:
                send_message(chat_id, r)
            send_message(chat_id, "جستجو به پایان رسید. 🌿", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=1)
        return True

    if state == "waiting_web_search":
        send_message(
            chat_id,
            f"🌐 جستجوی وب برای عبارت «{text}» به زودی پیاده‌سازی و نهایی می‌گردد.",
            main_menu(chat_id, lang)
        )
        update_user(chat_id, state="none")
        return True

    if state == "waiting_article":
        send_message(
            chat_id,
            f"📚 مقالات مرتبط با «{text}» به زودی متصل خواهند شد.",
            main_menu(chat_id, lang)
        )
        update_user(chat_id, state="none")
        return True

    return False

# =========================================================
# ۱۲. سیستم توزیع روزانه پست‌های کانال (daily scheduler)
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
            f"📘 آیه منتخب روز

"
            f"سوره {item['surah']} - آیه {item['verse']}

"
            f"{item['text']}

"
            f"🔹 ترجمه:
{item['trans']}"
        )

    if book_name == "nahj":
        return (
            f"📜 فراز روز از نهج‌البلاغه

"
            f"{item['type']} {item['number']}

"
            f"{item['text']}

"
            f"🔹 ترجمه:
{item['trans']}"
        )

    if book_name == "sahifeh":
        return (
            f"🤲 فراز روز از صحیفه سجادیه

"
            f"{item['title']} (دعای {item['dua']})

"
            f"{item['text']}

"
            f"🔹 ترجمه:
{item['trans']}"
        )

    return None

def send_daily_posts():
    try:
        # ۱. پست روزانه قرآن
        q_item, _ = next_item("quran", QURAN_DATA)
        q_msg = format_daily_message("quran", q_item)
        if q_msg:
            send_message(CHANNEL_ID, q_msg)

        time.sleep(5)

        # ۲. پست روزانه نهج‌البلاغه
        n_item, _ = next_item("nahj", NAHJ_DATA)
        n_msg = format_daily_message("nahj", n_item)
        if n_msg:
            send_message(CHANNEL_ID, n_msg)

        time.sleep(5)

        # ۳. پست روزانه صحیفه سجادیه
        s_item, _ = next_item("sahifeh", SAHIFEH_DATA)
        s_msg = format_daily_message("sahifeh", s_item)
        if s_msg:
            send_message(CHANNEL_ID, s_msg)

        print("✅ ارسال موفقیت‌آمیز پست‌های دوره‌ای روزانه در کانال انجام شد.")
    except Exception as e:
        print("❌ خطا در روند ارسال خودکار روزانه:", e)

def daily_scheduler():
    # خوابیدن اولیه برای لود بهتر وب‌سرور
    time.sleep(30)
    while True:
        try:
            send_daily_posts()
        except Exception as e:
            print("Scheduler Thread Exception:", e)

        # وقفه خواب ۲۴ ساعته
        time.sleep(24 * 60 * 60)

# =========================================================
# ۱۳. وب هوک و مدیریت یکپارچه درخواست‌ها
# =========================================================
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True) or {}

        # -------------------------
        # پردازش پیام‌های عادی متنی
        # -------------------------
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

            # استارت ربات
            if text == "/start" or text == "شروع":
                update_user(chat_id, state="none")
                send_message(
                    chat_id,
                    safe_text(lang, "select_lang", "لطفاً زبان خود را انتخاب کنید:"),
                    lang_keyboard()
                )
                return "OK", 200

            # بررسی عضویت اجباری (جز برای ادمین کل)
            if chat_id != ADMIN_ID:
                if not check_membership(chat_id):
                    send_message(
                        chat_id,
                        safe_text(lang, "force_join").format(channel=CHANNEL_ID),
                        join_keyboard()
                    )
                    return "OK", 200

            # اگر کاربر در وضعیت انتظار ورودی خاص (stateful) باشد
            handled = handle_state_message(chat_id, text, user)
            if handled:
                return "OK", 200

            # ارسال منوی اصلی همراه خوش‌آمدگویی
            send_message(
                chat_id,
                safe_text(lang, "welcome").format(name=first_name),
                main_menu(chat_id, lang)
            )
            return "OK", 200

        # -------------------------
        # کلیک بر دکمه‌های شیشه‌ای (Callback Query)
        # -------------------------
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

            # عملیات تغییر زبان کاربری
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

            # تایید عضویت در کانال
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

            # دکمه بازگشت به منوی اصلی
            if cb_data == "back_main":
                update_user(chat_id, state="none")
                send_message(
                    chat_id,
                    safe_text(lang, "welcome").format(name=first_name),
                    main_menu(chat_id, lang)
                )
                return "OK", 200

            # جلوگیری از اجرای عملیات زیر در صورت عدم جوین کاربر
            if chat_id != ADMIN_ID and not check_membership(chat_id):
                send_message(
                    chat_id,
                    safe_text(lang, "force_join").format(channel=CHANNEL_ID),
                    join_keyboard()
                )
                return "OK", 200

            # ورود ادمین به پنل مدیریت
            if cb_data == "admin_panel":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200

                send_message(
                    chat_id,
                    "🛠️ پنل ادمین قرآنی

"
                    f"کل آمار متون در حافظه:
"
                    f"📖 آیات قرآن لود شده: {len(QURAN_DATA)}
"
                    f"📙 فرازهای نهج‌البلاغه: {len(NAHJ_DATA)}
"
                    f"📗 ادعیه صحیفه سجادیه: {len(SAHIFEH_DATA)}

"
                    "این پنل به زودی دارای قابلیت‌های وسیع آماری و ارسال همگانی خواهد شد.",
                    main_menu(chat_id, lang)
                )
                return "OK", 200

            # پردازش کلیک روی دکمه‌های ۱۲گانه منوی اینلاین اصلی
            if cb_data.startswith("menu_"):
                try:
                    idx = int(cb_data.split("_")[1])
                except:
                    idx = -1

                if idx == 0:  # جستجوی قرآن
                    update_user(chat_id, state="waiting_quran_search")
                    send_message(chat_id, safe_text(lang, "search_quran_prompt"), back_menu_keyboard(lang))

                elif idx == 1:  # هوش مصنوعی
                    update_user(chat_id, state="waiting_ai")
                    send_message(chat_id, safe_text(lang, "ai_prompt"), back_menu_keyboard(lang))

                elif idx == 2:  # جستجوی وب
                    update_user(chat_id, state="waiting_web_search")
                    send_message(chat_id, safe_text(lang, "web_search_prompt"), back_menu_keyboard(lang))

                elif idx == 3:  # مقالات علمی
                    update_user(chat_id, state="waiting_article")
                    send_message(chat_id, safe_text(lang, "article_prompt"), back_menu_keyboard(lang))

                elif idx == 4:  # حدیث روز
                    item = random.choice(HADITHS)
                    send_message(chat_id, f"🕊️ {item}", main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)

                elif idx == 5:  # قرآن در لحظه
                    if QURAN_DATA:
                        item = random.choice(QURAN_DATA)
                        msg = f"✨ قرآن در لحظه

📖 {item['text']}

🔹 ترجمه:
{item['trans']}"
                        send_message(chat_id, msg, main_menu(chat_id, lang))
                    else:
                        item = random.choice(INSTANT_QURAN)
                        send_message(chat_id, f"✨ {item}", main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)

                elif idx == 6:  # رویدادها
                    send_message(chat_id, safe_text(lang, "events_text"), main_menu(chat_id, lang))

                elif idx == 7:  # پیام به ادمین
                    update_user(chat_id, state="waiting_admin_msg")
                    send_message(chat_id, safe_text(lang, "admin_msg_prompt"), back_menu_keyboard(lang))

                elif idx == 8:  # آمار و امتیاز
                    latest_user = get_user(chat_id)
                    send_message(
                        chat_id,
                        safe_text(lang, "stats").format(
                            name=first_name,
                            score=latest_user["score"]
                        ),
                        main_menu(chat_id, lang)
                    )

                elif idx == 9:  # لیگ قرآنی
                    send_message(chat_id, safe_text(lang, "league_text"), main_menu(chat_id, lang))

                elif idx == 10:  # کارنامه و رتبه
                    send_message(chat_id, safe_text(lang, "scorecard_text"), main_menu(chat_id, lang))

                elif idx == 11:  # تغییر زبان
                    send_message(
                        chat_id,
                        safe_text(lang, "select_lang"),
                        lang_keyboard()
                    )

                else:
                    send_message(chat_id, safe_text(lang, "under_construction"), main_menu(chat_id, lang))

            return "OK", 200

        return "OK", 200

    except Exception as e:
        print("WEBHOOK MAIN PROCESS EXCEPTION:", e)
        return "OK", 200

# =========================================================
# ۱۴. مسیرهای تست و بررسی صحت عملکرد (health check)
# =========================================================
@app.route("/", methods=["GET", "HEAD"])
def health():
    return jsonify({
        "status": "ok",
        "service": "labbayk_quranbot",
        "port": os.getenv("PORT", "10000"),
        "quran_records": len(QURAN_DATA),
        "nahj_records": len(NAHJ_DATA),
        "sahifeh_records": len(SAHIFEH_DATA)
    }), 200

# =========================================================
# ۱۵. اجرای استارتاپ و سرور وب
# =========================================================
def startup():
    init_db()
    load_library()
    
    # راه‌اندازی نخ پس‌زمینه (Thread) اسکژولر خودکار روزانه
    sched_thread = threading.Thread(target=daily_scheduler, daemon=True)
    sched_thread.start()
    priPORT", 10000))
    app.run(host="0.0.0.0", port=port)
```.")

# اجرای مقداردهی اولیه سیستم
startup()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
