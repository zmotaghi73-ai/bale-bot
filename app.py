import os
import sqlite3
import random
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# =========================================================
# تنظیمات اصلی
# =========================================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BALE_BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "YOUR_DEEPSEEK_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "722283092"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@sums_quran")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = "bot_data.db"

# =========================================================
# متون چندزبانه
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
        "stats": "📊 آمار تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}",
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
        "welcome": "Hello {name}! 😍\nWelcome to the Quran & Etrat bot of SUMS.\nPlease choose an option:",
        "force_join": "🌸 To use the bot services, please join our channel first, then click Confirm ✅:\n{channel}",
        "joined_success": "✅ Membership confirmed. Welcome!",
        "not_joined_yet": "🥲 Your membership is not confirmed yet. Please join first and try again.",
        "ai_prompt": "🤖 Ask your question, dear!",
        "ai_wait": "⏳ Please wait... thinking smart!",
        "admin_msg_prompt": "📩 Send your message and I’ll forward it to admin:",
        "admin_msg_sent": "✅ Your message was sent to admin.",
        "under_construction": "🚧 This section is under construction.",
        "stats": "📊 Your stats:\n\n👤 Name: {name}\n🏆 Score: {score}",
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
        "welcome": "مرحباً {name} 😍\nأهلاً بك في بوت كانون القرآن والعترة.\nاختر أحد الخيارات:",
        "force_join": "🌸 لاستخدام خدمات البوت، يرجى الانضمام أولاً إلى القناة ثم الضغط على تأكيد ✅:\n{channel}",
        "joined_success": "✅ تم تأكيد العضوية. أهلاً بك!",
        "not_joined_yet": "🥲 لم يتم تأكيد العضوية بعد. انضم أولاً ثم حاول مرة أخرى.",
        "ai_prompt": "🤖 اكتب سؤالك، أنا جاهز!",
        "ai_wait": "⏳ انتظر قليلاً... أفكر الآن!",
        "admin_msg_prompt": "📩 اكتب رسالتك ليتم إرسالها إلى المشرف:",
        "admin_msg_sent": "✅ تم إرسال رسالتك إلى المشرف.",
        "under_construction": "🚧 هذا القسم قيد التطوير.",
        "stats": "📊 إحصاءاتك:\n\n👤 الاسم: {name}\n🏆 النقاط: {score}",
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
        "welcome": "Merhaba {name}! 😍\nKur'an ve Etrat botuna hoş geldin.\nLütfen bir seçenek seç:",
        "force_join": "🌸 Bot hizmetlerini kullanmak için önce kanala katıl, sonra Onayla ✅ düğmesine bas:\n{channel}",
        "joined_success": "✅ Üyeliğin doğrulandı. Hoş geldin!",
        "not_joined_yet": "🥲 Üyeliğin henüz doğrulanmadı. Önce katıl, sonra tekrar dene.",
        "ai_prompt": "🤖 Sorunu yaz, hazırım!",
        "ai_wait": "⏳ Biraz bekle... düşünüyorum!",
        "admin_msg_prompt": "📩 Mesajını yaz, yöneticine ileteyim:",
        "admin_msg_sent": "✅ Mesajın yöneticiye gönderildi.",
        "under_construction": "🚧 Bu bölüm yapım aşamasında.",
        "stats": "📊 İstatistiklerin:\n\n👤 Ad: {name}\n🏆 Puan: {score}",
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

# =========================================================
# دیتابیس
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
            state TEXT DEFAULT 'none'
        )
    """)

    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, lang, score, state FROM users WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "name": row[0] or "",
            "lang": row[1] if row[1] in LANGS else "fa",
            "score": row[2] or 0,
            "state": row[3] or "none"
        }

    return {
        "name": "",
        "lang": "fa",
        "score": 0,
        "state": "none"
    }

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
        safe_lang = lang if lang in LANGS else "fa"
        cur.execute("UPDATE users SET lang=? WHERE chat_id=?", (safe_lang, chat_id))

    if score is not None:
        cur.execute("UPDATE users SET score=? WHERE chat_id=?", (score, chat_id))

    if score_add is not None:
        cur.execute("UPDATE users SET score=score+? WHERE chat_id=?", (score_add, chat_id))

    if state is not None:
        cur.execute("UPDATE users SET state=? WHERE chat_id=?", (state, chat_id))

    conn.commit()
    conn.close()

# =========================================================
# ابزارهای بله
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
# کیبوردها
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
                {
                    "text": "📢 ورود به کانال",
                    "url": f"https://ble.ir/{channel_username}"
                }
            ],
            [
                {
                    "text": "✅ تایید عضویت",
                    "callback_data": "check_join"
                }
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
    for i, item in enumerate(menu_items):
        row.append({"text": item, "callback_data": f"menu_{i}"})
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    if chat_id == ADMIN_ID:
        buttons.append([
            {"text": "🛠️ پنل ادمین", "callback_data": "admin_panel"}
        ])

    return {"inline_keyboard": buttons}

# =========================================================
# ایمنی زبان
# =========================================================
def safe_lang_dict(lang_code):
    return LANGS.get(lang_code, LANGS["fa"])

def safe_text(lang_code, key, default=None):
    lang_dict = safe_lang_dict(lang_code)
    if key in lang_dict:
        return lang_dict[key]
    return default if default is not None else LANGS["fa"].get(key, key)

# =========================================================
# عضویت اجباری
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
# هوش مصنوعی DeepSeek
# =========================================================
def ask_deepseek(question, lang):
    if not DEEPSEEK_KEY or DEEPSEEK_KEY == "YOUR_DEEPSEEK_API_KEY":
        return "کلید DeepSeek تنظیم نشده است."

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
        return "فعلاً نتونستم پاسخ بگیرم. دوباره امتحان کن."
    except Exception as e:
        print("DeepSeek error:", e)
        return "ارتباط با هوش مصنوعی موقتاً دچار مشکل شده."

# =========================================================
# پردازش وضعیت کاربر
# =========================================================
def handle_state_message(chat_id, text, user):
    lang = user["lang"]
    state = user["state"]
    name = user["name"] or "کاربر"

    if state == "waiting_ai":
        send_message(chat_id, safe_text(lang, "ai_wait"))
        answer = ask_deepseek(text, lang)
        send_message(chat_id, f"🤖 {answer}", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=2)
        return True

    if state == "waiting_admin_msg":
        send_message(
            ADMIN_ID,
            f"📩 پیام جدید از کاربر:\n\n"
            f"👤 نام: {name}\n"
            f"🆔 chat_id: {chat_id}\n"
            f"💬 متن:\n{text}"
        )
        send_message(chat_id, safe_text(lang, "admin_msg_sent"), main_menu(chat_id, lang))
        update_user(chat_id, state="none", score_add=1)
        return True

    if state == "waiting_quran_search":
        # فعلاً نمایشی
        send_message(
            chat_id,
            f"📖 نتیجه جستجوی نمایشی برای:\n\n{text}\n\n"
            f"این بخش آماده اتصال به دیتابیس آیات است.",
            main_menu(chat_id, lang)
        )
        update_user(chat_id, state="none", score_add=1)
        return True

    if state == "waiting_web_search":
        send_message(
            chat_id,
            f"🌐 جستجوی وب برای «{text}» به‌زودی فعال می‌شود.",
            main_menu(chat_id, lang)
        )
        update_user(chat_id, state="none")
        return True

    if state == "waiting_article":
        send_message(
            chat_id,
            f"📚 جستجوی مقاله برای «{text}» به‌زودی فعال می‌شود.",
            main_menu(chat_id, lang)
        )
        update_user(chat_id, state="none")
        return True

    return False

# =========================================================
# مسیر اصلی وب‌هوک
# =========================================================
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True) or {}

        # -------------------------
        # پیام عادی
        # -------------------------
        if "message" in data:
            msg = data["message"]
            chat = msg.get("chat", {})
            sender = msg.get("from", {})

            chat_id = chat.get("id")
            text = msg.get("text", "")
            first_name = sender.get("first_name", "دوست من")

            if not chat_id:
                return "OK", 200

            chat_id = int(chat_id)
            ensure_user(chat_id, first_name)
            update_user(chat_id, name=first_name)

            user = get_user(chat_id)
            lang = user["lang"]

            # استارت
            if text == "/start":
                send_message(
                    chat_id,
                    safe_text(lang, "select_lang", "لطفاً زبان را انتخاب کنید:"),
                    lang_keyboard()
                )
                return "OK", 200

            # قبل از همه چیز عضویت اجباری
            if not check_membership(chat_id):
                send_message(
                    chat_id,
                    safe_text(lang, "force_join").format(channel=CHANNEL_ID),
                    join_keyboard()
                )
                return "OK", 200

            # اگر کاربر در یک state باشد
            handled = handle_state_message(chat_id, text, user)
            if handled:
                return "OK", 200

            # اگر پیام آزاد فرستاد
            send_message(
                chat_id,
                safe_text(lang, "welcome").format(name=first_name),
                main_menu(chat_id, lang)
            )
            return "OK", 200

        # -------------------------
        # کلیک روی دکمه‌ها
        # -------------------------
        elif "callback_query" in data:
            cb = data["callback_query"]
            cb_id = cb.get("id")
            cb_data = cb.get("data", "")
            cb_message = cb.get("message", {})
            chat = cb_message.get("chat", {})
            sender = cb.get("from", {})

            chat_id = chat.get("id")
            first_name = sender.get("first_name", "دوست من")

            if not chat_id:
                return "OK", 200

            chat_id = int(chat_id)
            ensure_user(chat_id, first_name)
            update_user(chat_id, name=first_name)

            user = get_user(chat_id)
            lang = user["lang"]
            score = user["score"]

            if cb_id:
                answer_callback(cb_id)

            # تغییر زبان
            if cb_data.startswith("setlang_"):
                new_lang = cb_data.replace("setlang_", "").strip()
                if new_lang not in LANGS:
                    new_lang = "fa"

                update_user(chat_id, lang=new_lang, state="none")
                user = get_user(chat_id)
                lang = user["lang"]

                if not check_membership(chat_id):
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

            # تایید عضویت
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

            # بازگشت به منو
            if cb_data == "back_main":
                send_message(
                    chat_id,
                    safe_text(lang, "welcome").format(name=first_name),
                    main_menu(chat_id, lang)
                )
                return "OK", 200

            # اگر عضو نیست، اجازه ادامه نده
            if not check_membership(chat_id):
                send_message(
                    chat_id,
                    safe_text(lang, "force_join").format(channel=CHANNEL_ID),
                    join_keyboard()
                )
                return "OK", 200

            # پنل ادمین
            if cb_data == "admin_panel":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200

                send_message(
                    chat_id,
                    "🛠️ پنل ادمین\n\n"
                    "فعلاً نسخه اولیه فعاله.\n"
                    "بعداً می‌تونیم این بخش‌ها رو اضافه کنیم:\n"
                    "- آمار کاربران\n"
                    "- پیام همگانی\n"
                    "- مدیریت لیگ\n"
                    "- مشاهده تیکت‌ها",
                    main_menu(chat_id, lang)
                )
                return "OK", 200

            # منوی اصلی
            if cb_data.startswith("menu_"):
                try:
                    idx = int(cb_data.split("_")[1])
                except:
                    idx = -1

                if idx == 0:
                    update_user(chat_id, state="waiting_quran_search")
                    send_message(chat_id, safe_text(lang, "search_quran_prompt"), back_menu_keyboard(lang))

                elif idx == 1:
                    update_user(chat_id, state="waiting_ai")
                    send_message(chat_id, safe_text(lang, "ai_prompt"), back_menu_keyboard(lang))

                elif idx == 2:
                    update_user(chat_id, state="waiting_web_search")
                    send_message(chat_id, safe_text(lang, "web_search_prompt"), back_menu_keyboard(lang))

                elif idx == 3:
                    update_user(chat_id, state="waiting_article")
                    send_message(chat_id, safe_text(lang, "article_prompt"), back_menu_keyboard(lang))

                elif idx == 4:
                    item = random.choice(HADITHS)
                    send_message(chat_id, f"🕊️ {item}", main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)

                elif idx == 5:
                    item = random.choice(INSTANT_QURAN)
                    send_message(chat_id, f"✨ {item}", main_menu(chat_id, lang))
                    update_user(chat_id, score_add=1)

                elif idx == 6:
                    send_message(chat_id, safe_text(lang, "events_text"), main_menu(chat_id, lang))

                elif idx == 7:
                    update_user(chat_id, state="waiting_admin_msg")
                    send_message(chat_id, safe_text(lang, "admin_msg_prompt"), back_menu_keyboard(lang))

                elif idx == 8:
                    latest_user = get_user(chat_id)
                    send_message(
                        chat_id,
                        safe_text(lang, "stats").format(
                            name=first_name,
                            score=latest_user["score"]
                        ),
                        main_menu(chat_id, lang)
                    )

                elif idx == 9:
                    send_message(chat_id, safe_text(lang, "league_text"), main_menu(chat_id, lang))

                elif idx == 10:
                    send_message(chat_id, safe_text(lang, "scorecard_text"), main_menu(chat_id, lang))

                elif idx == 11:
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
        print("WEBHOOK ERROR:", e)
        return "OK", 200

# =========================================================
# مسیر تست سلامت
# =========================================================
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "labbayk_quran_bot",
        "port": os.getenv("PORT", "10000")
    }), 200

# =========================================================
# اجرای برنامه
# =========================================================
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
