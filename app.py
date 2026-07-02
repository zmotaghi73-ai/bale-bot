import os
import random
import logging
from datetime import datetime

import requests
from flask import Flask, request, jsonify


# ============================================================
# Basic Config
# ============================================================

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # اختیاری

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set.")

BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ============================================================
# In-memory user state
# توجه: روی Render با ری‌استارت شدن سرویس پاک می‌شود.
# برای نسخه حرفه‌ای‌تر بهتر است دیتابیس اضافه شود.
# ============================================================

user_states = {}
user_stats = {}


# ============================================================
# Static Data
# ============================================================

DAILY_VERSES = [
    {
        "arabic": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ",
        "translation": "آگاه باشید که دل‌ها تنها با یاد خدا آرام می‌گیرد.",
        "source": "سوره رعد، آیه ۲۸"
    },
    {
        "arabic": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "translation": "بی‌تردید همراه هر سختی، آسانی است.",
        "source": "سوره شرح، آیه ۶"
    },
    {
        "arabic": "فَاذْكُرُونِي أَذْكُرْكُمْ",
        "translation": "پس مرا یاد کنید تا شما را یاد کنم.",
        "source": "سوره بقره، آیه ۱۵۲"
    },
    {
        "arabic": "وَهُوَ مَعَكُمْ أَيْنَ مَا كُنتُمْ",
        "translation": "و او هر کجا باشید با شماست.",
        "source": "سوره حدید، آیه ۴"
    },
]

HADITHS = [
    {
        "arabic": "إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ",
        "translation": "ارزش اعمال به نیت‌هاست.",
        "source": "پیامبر اکرم ﷺ"
    },
    {
        "arabic": "خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ",
        "translation": "بهترین شما کسی است که قرآن را بیاموزد و به دیگران آموزش دهد.",
        "source": "پیامبر اکرم ﷺ"
    },
    {
        "arabic": "زَكَاةُ الْعِلْمِ نَشْرُهُ",
        "translation": "زکات علم، نشر دادن آن است.",
        "source": "امام علی علیه‌السلام"
    },
]

HELP_TEXT = """
🕌 راهنمای ربات کانون قرآن و عترت

از دکمه‌های زیر می‌تونی استفاده کنی:

🌙 آیه روز
نمایش یک آیه منتخب همراه با ترجمه فارسی.

📜 حدیث تصادفی
نمایش یک حدیث کوتاه و کاربردی.

🔎 جستجوی قرآن
فعلاً به صورت آزمایشی عبارت شما را دریافت می‌کند.
در نسخه بعدی می‌توانیم جستجوی واقعی در متن قرآن اضافه کنیم.

🤖 هوش مصنوعی
بخش آزمایشی برای اتصال به هوش مصنوعی.

📊 وضعیت من
نمایش وضعیت و آمار استفاده شما از ربات.

👤 ارتباط با ادمین
نمایش راه ارتباطی یا ارسال پیام به مدیر.

🏠 منوی اصلی
بازگشت به منوی اصلی ربات.

دستورات قابل استفاده:
/start
/help
/my_states
/search
"""


# ============================================================
# Keyboards
# ============================================================

def main_keyboard():
    return {
        "keyboard": [
            [
                {"text": "🌙 آیه روز"},
                {"text": "📜 حدیث تصادفی"}
            ],
            [
                {"text": "🔎 جستجوی قرآن"},
                {"text": "🤖 هوش مصنوعی"}
            ],
            [
                {"text": "🕌 راهنمای ربات"},
                {"text": "📊 وضعیت من"}
            ],
            [
                {"text": "👤 ارتباط با ادمین"},
                {"text": "🏠 منوی اصلی"}
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


def cancel_keyboard():
    return {
        "keyboard": [
            [
                {"text": "❌ لغو"},
                {"text": "🏠 منوی اصلی"}
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


# ============================================================
# Bale API Helpers
# ============================================================

def bale_request(method, payload):
    """
    ارسال درخواست به API بله
    """
    url = f"{BASE_URL}/{method}"

    try:
        logging.info("Sending request to Bale API: %s | payload=%s", method, payload)

        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        logging.info(
            "Bale API response | status=%s | body=%s",
            response.status_code,
            response.text[:1000]
        )

        return response

    except requests.exceptions.Timeout:
        logging.exception("Timeout while calling Bale API.")
        return None

    except requests.exceptions.RequestException:
        logging.exception("Request error while calling Bale API.")
        return None


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    return bale_request("sendMessage", payload)


def send_main_menu(chat_id):
    text = """
🌿 به ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.

از منوی زیر می‌تونی از امکانات مختلف استفاده کنی:
"""
    return send_message(chat_id, text, main_keyboard())


# ============================================================
# User Helpers
# ============================================================

def get_user_id(message):
    user = message.get("from", {})
    return user.get("id")


def get_chat_id(message):
    chat = message.get("chat", {})
    return chat.get("id")


def get_message_text(message):
    return message.get("text", "").strip()


def increase_user_counter(user_id, key="messages"):
    if not user_id:
        return

    user_id = str(user_id)

    if user_id not in user_stats:
        user_stats[user_id] = {
            "messages": 0,
            "searches": 0,
            "ai_requests": 0,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    user_stats[user_id][key] = user_stats[user_id].get(key, 0) + 1


def set_user_state(user_id, state):
    if user_id:
        user_states[str(user_id)] = state


def get_user_state(user_id):
    if not user_id:
        return None
    return user_states.get(str(user_id))


def clear_user_state(user_id):
    if user_id:
        user_states.pop(str(user_id), None)


def get_user_display_name(message):
    user = message.get("from", {})
    first_name = user.get("first_name") or ""
    last_name = user.get("last_name") or ""
    username = user.get("username")

    full_name = f"{first_name} {last_name}".strip()

    if full_name:
        return full_name

    if username:
        return f"@{username}"

    return "کاربر عزیز"


# ============================================================
# Feature Handlers
# ============================================================

def handle_start(chat_id, message):
    user_name = get_user_display_name(message)

    text = f"""
سلام {user_name} جان 🌿

به ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.

اینجا می‌تونی از امکانات مختلف استفاده کنی:
🌙 آیه روز
📜 حدیث تصادفی
🔎 جستجوی قرآن
🤖 هوش مصنوعی
🕌 راهنمای ربات

از منوی پایین انتخاب کن.
"""
    send_message(chat_id, text, main_keyboard())


def handle_help(chat_id):
    send_message(chat_id, HELP_TEXT, main_keyboard())


def handle_daily_verse(chat_id):
    verse = random.choice(DAILY_VERSES)

    text = f"""
🌙 آیه روز

﴿ {verse["arabic"]} ﴾

📝 ترجمه:
{verse["translation"]}

📖 منبع:
{verse["source"]}
"""
    send_message(chat_id, text, main_keyboard())


def handle_random_hadith(chat_id):
    hadith = random.choice(HADITHS)

    text = f"""
📜 حدیث تصادفی

«{hadith["arabic"]}»

📝 ترجمه:
{hadith["translation"]}

📚 منبع:
{hadith["source"]}
"""
    send_message(chat_id, text, main_keyboard())


def handle_my_states(chat_id, user_id):
    user_id_str = str(user_id)

    stats = user_stats.get(user_id_str, {
        "messages": 0,
        "searches": 0,
        "ai_requests": 0,
        "started_at": "ثبت نشده"
    })

    current_state = user_states.get(user_id_str, "حالت عادی")

    text = f"""
📊 وضعیت شما در ربات

🧾 تعداد پیام‌ها:
{stats.get("messages", 0)}

🔎 تعداد جستجوها:
{stats.get("searches", 0)}

🤖 درخواست‌های هوش مصنوعی:
{stats.get("ai_requests", 0)}

🧭 وضعیت فعلی:
{current_state}

⏰ زمان شروع ثبت آمار:
{stats.get("started_at", "ثبت نشده")}

نکته کوچولو:
این آمار فعلاً در حافظه موقت ذخیره می‌شود و با ری‌استارت Render ممکن است صفر شود.
"""
    send_message(chat_id, text, main_keyboard())


def handle_search_start(chat_id, user_id):
    set_user_state(user_id, "awaiting_quran_search")

    text = """
🔎 جستجوی قرآن

لطفاً کلمه یا عبارت موردنظرت را ارسال کن.

مثلاً:
صبر
رحمت
نماز
اطمئنان قلب

برای خروج از جستجو، روی «❌ لغو» بزن.
"""
    send_message(chat_id, text, cancel_keyboard())


def handle_quran_search(chat_id, user_id, query):
    increase_user_counter(user_id, "searches")
    clear_user_state(user_id)

    # فعلاً جستجوی نمایشی است.
    # اگر فایل دیتای قرآن اضافه شود، اینجا می‌توانیم جستجوی واقعی انجام بدهیم.

    text = f"""
🔎 نتیجه جستجوی قرآن

عبارت جستجو شده:
«{query}»

در نسخه فعلی، جستجوی واقعی در متن قرآن هنوز متصل نشده است.
اما مسیر آماده است ✅

مرحله بعدی این است که یک دیتاست قرآن به پروژه اضافه کنیم و همین بخش را به جستجوی واقعی وصل کنیم.

فعلاً مثل یک آسانسور بدون طبقه‌بندی است؛ دکمه دارد، حرکت هم می‌کند، ولی باید مقصدها را اضافه کنیم 😄
"""
    send_message(chat_id, text, main_keyboard())


def handle_ai_start(chat_id, user_id):
    set_user_state(user_id, "awaiting_ai_prompt")

    text = """
🤖 بخش هوش مصنوعی

فعلاً این بخش در حالت آزمایشی است.

لطفاً سؤال یا درخواستت را بنویس.
برای خروج، روی «❌ لغو» بزن.
"""
    send_message(chat_id, text, cancel_keyboard())


def handle_ai_prompt(chat_id, user_id, prompt):
    increase_user_counter(user_id, "ai_requests")
    clear_user_state(user_id)

    text = f"""
🤖 پاسخ هوش مصنوعی

درخواست شما:
«{prompt}»

فعلاً اتصال واقعی به مدل هوش مصنوعی انجام نشده است.
اما هندلر آماده است و پیام شما درست دریافت شد ✅

برای فعال‌سازی واقعی، باید یک API هوش مصنوعی به این قسمت وصل کنیم.
"""
    send_message(chat_id, text, main_keyboard())


def handle_admin_contact(chat_id):
    if ADMIN_ID:
        text = f"""
👤 ارتباط با ادمین

برای ارتباط با مدیر ربات، می‌توانید پیام خود را برای ادمین ارسال کنید.

شناسه ادمین:
{ADMIN_ID}
"""
    else:
        text = """
👤 ارتباط با ادمین

راه ارتباط با ادمین هنوز تنظیم نشده است.

برای فعال‌سازی، در Render یک Environment Variable با نام زیر اضافه کن:

ADMIN_ID

مثلاً:
ADMIN_ID=123456789
"""

    send_message(chat_id, text, main_keyboard())


def handle_cancel(chat_id, user_id):
    clear_user_state(user_id)

    text = """
❌ عملیات لغو شد.

به منوی اصلی برگشتی.
"""
    send_message(chat_id, text, main_keyboard())


def handle_unknown(chat_id, text):
    response = f"""
متوجه منظورت نشدم 🤔

پیام دریافت‌شده:
{text}

لطفاً از منوی زیر یکی از گزینه‌ها را انتخاب کن.
"""
    send_message(chat_id, response, main_keyboard())


# ============================================================
# Main Router
# ============================================================

def handle_message(message):
    chat_id = get_chat_id(message)
    user_id = get_user_id(message)
    text = get_message_text(message)

    logging.info(
        "Received message | chat_id=%s | user_id=%s | text=%s",
        chat_id,
        user_id,
        text
    )

    if not chat_id:
        logging.warning("No chat_id found in message.")
        return

    if not text:
        send_message(chat_id, "فعلاً فقط پیام متنی را می‌توانم پردازش کنم 🌿", main_keyboard())
        return

    increase_user_counter(user_id, "messages")

    normalized_text = text.strip()
    state = get_user_state(user_id)

    # ------------------------------
    # Global cancel / main menu
    # ------------------------------
    if normalized_text in ["❌ لغو", "لغو", "/cancel"]:
        handle_cancel(chat_id, user_id)
        return

    if normalized_text in ["🏠 منوی اصلی", "منوی اصلی", "/menu"]:
        clear_user_state(user_id)
        send_main_menu(chat_id)
        return

    # ------------------------------
    # State-based handling
    # ------------------------------
    if state == "awaiting_quran_search":
        handle_quran_search(chat_id, user_id, normalized_text)
        return

    if state == "awaiting_ai_prompt":
        handle_ai_prompt(chat_id, user_id, normalized_text)
        return

    # ------------------------------
    # Commands and buttons
    # ------------------------------
    if normalized_text in ["/start", "start"]:
        clear_user_state(user_id)
        handle_start(chat_id, message)
        return

    if normalized_text in ["/help", "help", "🕌 راهنمای ربات", "راهنمای ربات 🕌", "راهنمای ربات"]:
        clear_user_state(user_id)
        handle_help(chat_id)
        return

    if normalized_text in ["/my_states", "/my_state", "/states", "📊 وضعیت من", "وضعیت من"]:
        clear_user_state(user_id)
        handle_my_states(chat_id, user_id)
        return

    if normalized_text in ["/search", "🔎 جستجوی قرآن", "جستجوی قرآن"]:
        handle_search_start(chat_id, user_id)
        return

    if normalized_text in ["🌙 آیه روز", "آیه روز 🌙", "آیه روز", "/verse"]:
        clear_user_state(user_id)
        handle_daily_verse(chat_id)
        return

    if normalized_text in ["📜 حدیث تصادفی", "حدیث تصادفی", "/hadith"]:
        clear_user_state(user_id)
        handle_random_hadith(chat_id)
        return

    if normalized_text in ["🤖 هوش مصنوعی", "هوش مصنوعی", "/ai"]:
        handle_ai_start(chat_id, user_id)
        return

    if normalized_text in ["👤 ارتباط با ادمین", "ارتباط با ادمین", "/admin"]:
        clear_user_state(user_id)
        handle_admin_contact(chat_id)
        return

    # ------------------------------
    # Fallback
    # ------------------------------
    handle_unknown(chat_id, normalized_text)


# ============================================================
# Flask Routes
# ============================================================

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "message": "Quran bot is running.",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True, silent=True)

        logging.info("Incoming update: %s", update)

        if not update:
            logging.warning("Empty update received.")
            return jsonify({"ok": True, "message": "empty update"}), 200

        # حالت رایج Bot API:
        # {
        #   "update_id": ...,
        #   "message": {...}
        # }
        if "message" in update:
            handle_message(update["message"])

        # اگر بله ساختار متفاوتی بدهد و message داخل کل آبجکت باشد
        elif "chat" in update and "text" in update:
            handle_message(update)

        else:
            logging.warning("Unsupported update format: %s", update)

        return jsonify({"ok": True}), 200

    except Exception as e:
        logging.exception("Error in webhook: %s", e)

        # مهم:
        # حتی اگر خطا رخ داد، 200 برمی‌گردانیم تا پلتفرم مدام webhook را تکرار نکند.
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 200


# ============================================================
# Local Run
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
