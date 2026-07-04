import os
import sqlite3
import random
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- ⚙️ تنظیمات اصلی و کلیدها ---
TOKEN = "1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY"
DEEPSEEK_KEY = "sk-40e2e32cdcdc44ad91e6f428bd187a22"
ADMIN_ID = 722283092
CHANNEL_ID = "@sums_quran"  # آیدی کانال کانون جهت عضویت اجباری
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = "bot_data.db"

# --- 📚 دیتای داخلی برای جذابیت بیشتر ربات ---
HADITHS = [
    "امیرالمؤمنین (ع): لقاح معرفت، مطالعه قرآن است. 🌸",
    "پیامبر اکرم (ص): بهترین شما کسی است که قرآن را یاد بگیرد و به دیگران یاد دهد. ❤️",
    "امام صادق (ع): قرآن پیمان خدا با خلق اوست؛ شایسته است انسان مسلمان به این پیمان بنگرد و هر روز ۵۰ آیه بخواند. 📖",
    "پیامبر اکرم (ص): خانه‌های خود را با تلاوت قرآن نورانی کنید. ✨"
]

QUOTES = [
    "زندگی جان، امروز روز توست! با یک آیه قشنگ شروع کن: 'أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ' 🕊️",
    "هر سختی یک آسانی به همراه دارد... قوی باش زندگی! ⚡",
    "خداوند هیچ‌کس را تکلیف نمی‌کند مگر به اندازه توانش. تو قوی‌تر از اونی هستی که فکر می‌کنی! 💪"
]

# --- 🌐 متون و ترجمه‌های چندزبانه صمیمی ---
LANGS = {
    'fa': {
        'welcome': "سلام {name} قشنگم! {greet} 😍\nبه ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خیلی خیلی خوش اومدی!\nاینجا کلی اتفاقات باحال منتظرته. لطفاً انتخاب کن:",
        'force_join': "زندگی جان! 🌸 برای استفاده از خدمات جذاب ربات، لطفاً ابتدا عضو کانال کانون قرآن و عترت بشو و بعد دکمه 'تایید عضویت ✅' رو بزن:\n👉 {channel}",
        'joined_success': "🎉 ایول! عضویتت تایید شد. حالا می‌تونی از تمام بخش‌ها استفاده کنی زندگی!",
        'ai_prompt': "🧠 هرچی تو دلت هست یا هر سوال علمی و قرآنی داری بپرس زندگی، من با هوش خودم سریع جواب میدم:",
        'ai_wait': "صبور باش زندگی قشنگم... دارم با تمام سلول‌های خاکستری مغزم پردازشش می‌کنم! 🧠⚡",
        'about': "این ربات هوشمند با کلی عشق توسط کانون قرآن و عترت دانشگاه علوم پزشکی شیراز برای شما دانشجوهای گل طراحی شده. 🩺❤️",
        'menu': [
            "📖 جستجوی قرآن", "🤖 هوش مصنوعی", "🌐 جستجوی وب",
            "📚 مقالات علمی", "🕊️ حدیث و ذکر روز", "📖 قرآن در لحظه",
            "📢 رویدادها و مسابقات", "📞 ارسال پیام به ادمین", "📊 آمار و امتیاز من",
            "🏆 لیگ قرآنی", "📋 کارنامه و رتبه", "🌐 تغییر زبان"
        ]
    },
    'en': {
        'welcome': "Hello dear {name}! {greet} 😍\nWelcome to the Quran & Etrat Bot. Please select an option:",
        'force_join': "Dear life! 🌸 To use our services, please join our channel first and then click 'Confirm ✅':\n👉 {channel}",
        'joined_success': "🎉 Great! Your membership is confirmed. Enjoy the bot!",
        'ai_prompt': "🧠 Ask me anything, dear life! The AI is ready to reply:",
        'ai_wait': "Processing with love... Please wait a moment! ⚡",
        'about': "Designed with love by the Quran & Etrat Center of Shiraz University of Medical Sciences. 🩺❤️",
        'menu': [
            "📖 Quran Search", "🤖 AI DeepSeek", "🌐 Web Search",
            "📚 Articles", "🕊️ Hadith & Quote", "📖 Instant Quran",
            "📢 Events & Contests", "📞 Contact Admin", "📊 My Stats",
            "🏆 League", "📋 Scorecard", "🌐 Change Language"
        ]
    }
}

# --- 💾 مدیریت دیتابیس ---
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

# --- 🛰️ بررسی عضویت اجباری در کانال کانون ---
def check_membership(chat_id):
    # بله متد getChatMember دارد. برای بررسی اینکه کاربر عضو است یا خیر:
    url = f"{BASE_URL}/getChatMember"
    payload = {"chat_id": CHANNEL_ID, "user_id": chat_id}
    try:
        res = requests.post(url, json=payload, timeout=10).json()
        if res.get("ok"):
            status = res["result"].get("status")
            # اگر عضو، مدیر یا ادمین باشد مجاز است
            if status in ["member", "administrator", "creator"]:
                return True
        return False
    except:
        # در صورت بروز خطای شبکه یا موقت، برای راحتی کاربر فرض می‌کنیم عضو است
        return True

# --- 📬 متدهای ارتباطی بله ---
def send_bale(method, data):
    url = f"{BASE_URL}/{method}"
    try:
        return requests.post(url, json=data, timeout=15)
    except Exception as e:
        print(f"Error calling Bale: {e}")
        return None

def answer_callback(callback_query_id):
    send_bale("answerCallbackQuery", {"callback_query_id": callback_query_id})

# --- 🎨 کیبوردها ---
def lang_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🇮🇷 فارسی", "callback_data": "setlang_fa"},
                {"text": "🇬🇧 English", "callback_data": "setlang_en"}
            ]
        ]
    }

def join_keyboard(lang):
    return {
        "inline_keyboard": [
            [{"text": "📢 ورود به کانال کانون", "url": f"https://ble.ir/{CHANNEL_ID.replace('@', '')}"}],
            [{"text": "✅ تایید عضویت", "callback_data": "check_join"}]
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
        buttons.append([{"text": "🛠️ مدیریت کل کانون", "callback_data": "admin_panel"}])

    return {"inline_keyboard": buttons}

# --- 🧠 اتصال هوشمند به DeepSeek ---
def ask_deepseek(question, lang):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": f"You are a very kind, energetic and friendly Quranic helper. Answer warmly and concisely in {lang}."},
            {"role": "user", "content": question}
        ]
    }
    try:
        res = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=25)
        return res.json()['choices'][0]['message']['content']
    except:
        return "زندگی جانم مثل اینکه اتصال اینترنت من یکم ضعیف شده! لطفاً چند لحظه دیگه دوباره برام بفرستش. 🌸"

# --- 🚀 مدیریت منطق وب‌هوک ---
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg = data["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "")
        first_name = msg.get("from", {}).get("first_name", "زندگی")

        if not chat_id:
            return "OK", 200

        chat_id = int(chat_id)
        lang, score, state = get_user(chat_id)

        # بررسی عضویت اجباری
        if not check_membership(chat_id) and text != "/start":
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": LANGS[lang]['force_join'].format(channel=CHANNEL_ID),
                "reply_markup": join_keyboard(lang)
            })
            return "OK", 200

        if text == "/start":
            update_user(chat_id, name=first_name, state='none')
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": LANGS[lang]['select_lang'],
                "reply_markup": lang_keyboard()
            })
            return "OK", 200

        # هوش مصنوعی در حال انتظار
        if state == "waiting_ai":
            send_bale("sendMessage", {"chat_id": chat_id, "text": LANGS[lang]['ai_wait']})
            ai_res = ask_deepseek(text, lang)
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": f"🤖 **پاسخ هوشمند برای تو زندگی جان:**\n\n{ai_res}",
                "reply_markup": main_menu(chat_id, lang)
            })
            update_user(chat_id, state='none')
            return "OK", 200

        # ارتباط با ادمین در حال انتظار
        if state == "waiting_admin_msg":
            send_bale("sendMessage", {
                "chat_id": ADMIN_ID,
                "text": f"📥 **پیام دریافتی از زندگی ({first_name} - {chat_id}):**\n\n{text}"
            })
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": "پیامت رو با عشق گرفتم زندگی جان! ❤️ در اولین فرصت بررسی می‌کنم و بهت خبر میدم.",
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
        first_name = msg.get("chat", {}).get("first_name", "زندگی")

        if cb_id:
            answer_callback(cb_id)

        lang, score, state = get_user(chat_id)

        # تایید عضویت در کانال
        if cb_data == "check_join":
            if check_membership(chat_id):
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": LANGS[lang]['joined_success'],
                    "reply_markup": main_menu(chat_id, lang)
                })
            else:
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": "هنوز عضو کانال نشدی زندگی جان! 🥺 لطفاً عضو شو بعد دکمه تایید رو بزن.",
                    "reply_markup": join_keyboard(lang)
                })

        # تنظیم زبان
        elif cb_data.startswith("setlang_"):
            new_lang = cb_data.split("_")[1]
            update_user(chat_id, lang=new_lang, state='none')
            
            # هدایت به عضویت اجباری یا منوی اصلی
            if not check_membership(chat_id):
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": LANGS[new_lang]['force_join'].format(channel=CHANNEL_ID),
                    "reply_markup": join_keyboard(new_lang)
                })
            else:
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": LANGS[new_lang]['welcome'].format(name=first_name, greet="روزت پر از انرژی و سلامتی"),
                    "reply_markup": main_menu(chat_id, new_lang)
                })

        # اکشن‌های منوی ۱۲ تایی
        elif cb_data.startswith("menu_"):
            btn_idx = int(cb_data.split("_")[1])

            # ۱. جستجوی قرآن
            if btn_idx == 0:
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": "📖 زندگی جان! برای جستجوی آیه، لطفاً کلمه مورد نظرت رو بنویس (این بخش قراره به زودی به دیتابیس عظیم متصل بشه!) ✨",
                    "reply_markup": main_menu(chat_id, lang)
                })

            # ۲. هوش مصنوعی
            elif btn_idx == 1:
                update_user(chat_id, state='waiting_ai')
                send_bale("sendMessage", {"chat_id": chat_id, "text": LANGS[lang]['ai_prompt']})

            # ۵. حدیث و ذکر روز
            elif btn_idx == 4:
                item = random.choice(HADITHS)
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"🌸 **حدیث و ذکر امروز برای زندگی قشنگم:**\n\n{item}",
                    "reply_markup": main_menu(chat_id, lang)
                })

            # ۶. قرآن در لحظه (آیه تصادفی با انرژی مثبت)
            elif btn_idx == 5:
                item = random.choice(QUOTES)
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"✨ **یک آیه و حس خوب تقدیم به تو زندگی:**\n\n{item}",
                    "reply_markup": main_menu(chat_id, lang)
                })

            # ٨. ارتباط با ادمین
            elif btn_idx == 7:
                update_user(chat_id, state='waiting_admin_msg')
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": "📞 هر حرف، انتقاد یا پیشنهادی داری برام بنویس تا مستقیم به دست ادمین کانون برسونم:"
                })

            # ٩. آمار و امتیاز من
            elif btn_idx == 8:
                update_user(chat_id, score_add=10) # امتیاز هدیه برای سر زدن به این بخش!
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"📊 **شناسنامه قرآنی تو زندگی جان:**\n\n👤 نام: {first_name}\n🏆 امتیاز کل: {score + 10} ستاره ⭐\n\nهمین‌طور پرانرژی ادامه بده! 😉",
                    "reply_markup": main_menu(chat_id, lang)
                })

            # ۱۲. تغییر زبان دستی
            elif btn_idx == 11:
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": LANGS[lang]['select_lang'],
                    "reply_markup": lang_keyboard()
                })

            # سایر دکمه‌های در دست ساخت
            else:
                send_bale("sendMessage", {
                    "chat_id": chat_id,
                    "text": "🚧 این بخش جذاب در حال طراحی و آمادسازی توسط کانون هست. خیلی زود راه‌اندازی میشه زندگی جانم! 🌸",
                    "reply_markup": main_menu(chat_id, lang)
                })

    return "OK", 200

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "active", "bot": "Shiraz Quran Bot"}), 200

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
