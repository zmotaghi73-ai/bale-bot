# -*- coding: utf-8 -*-
"""
ربات حرفه‌ای کانون قرآن و عترت - نسخه ۲۲.۱ (نسخه نهایی و جامع - رفع دکمه‌های خراب)
ویژه دانشگاه علوم پزشکی شیراز
با موتور جستجوی هوشمند یکپارچه (AI + Islamic Search) با OpenRouter
با سیستم ارسال روزانه سه‌گانه (قرآن + صحیفه سجادیه + نهج‌البلاغه)
با منوی زیرشاخه‌ای حرفه‌ای و دانشجوپسند
تمامی دستورات نسخه‌های قبلی حفظ شده است
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
import hashlib
import string
import shutil
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from functools import wraps
import traceback
from thefuzz import fuzz

# =========================================================
# تنظیمات لاگ‌گیری پیشرفته
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================================================
# پشتیبانی از تاریخ شمسی
# =========================================================
try:
    import jdatetime
    HAS_JDATETIME = True
    logger.info("✅ کتابخانه jdatetime با موفقیت بارگذاری شد.")
except ImportError:
    HAS_JDATETIME = False
    logger.warning("⚠️ کتابخانه jdatetime نصب نیست. از تاریخ میلادی استفاده می‌شود.")

app = Flask(__name__)

# =========================================================
# ۱. تنظیمات و متغیرهای محیطی اصلی
# =========================================================
TOKEN = os.getenv("BOT_TOKEN", "")
if not TOKEN:
    logger.error("⚠️ BOT_TOKEN تنظیم نشده است!")
    raise ValueError("BOT_TOKEN is required")

# کلیدهای API
OPENROUTER_KEY = "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"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# کلید Serper.dev برای جستجوی اینترنتی
SERPER_API_KEY = "e7a36e000e2e9f0ece80bd5b634836cd4017f011"
SERPER_URL = "https://google.serper.dev/search"

# کلید قدیمی DeepSeek (برای سازگاری)
DEEPSEEK_KEY = "sk-090c2a86847c4583944621a5113d0382"

ADMIN_ID = int(os.getenv("ADMIN_ID", "722283092"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@quran_sums")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = os.getenv("DATABASE_PATH", "bot_data.db")
BOT_USERNAME = os.getenv("BOT_USERNAME", "labbayk_quranbot")
PORT = int(os.environ.get("PORT", 10000))

# فایل‌های کتابخانه
QURAN_FILE = "quran.json"
NAHJ_FILE = "nahj.json"
SAHIFEH_FILE = "sahifeh.json"
ARTICLES_FILE = "articles_cache.json"
TOPICS_FILE = "topics.json"
BACKUP_DIR = "backups"
FAVORITES_FILE = "favorites.json"
SURVEYS_FILE = "surveys.json"
MAHDI_FILE = "mahdi.json"

# متغیرهای سراسری
QURAN_DATA = []
NAHJ_DATA = []
SAHIFEH_DATA = []
ARTICLE_CACHE = {}
TOPICS_DATA = {}
USER_SESSIONS = {}
SEARCH_CACHE = {}
RATE_LIMIT_COUNTER = {}
RATE_LIMIT_TIME = {}
FAVORITES_DATA = {}
SURVEYS_DATA = {}
CONVERSATION_HISTORY = {}
MAHDI_MESSAGES = []

# کلیدهای API دیگر
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CX_ID = os.getenv("GOOGLE_CX_ID", "")
SERP_API_KEY_OLD = os.getenv("SERP_API_KEY", "")

# =========================================================
# ۲. Feature Flags
# =========================================================
FEATURES = {
    "quran_search": True,
    "deepseek_ai": True,
    "daily_posts": True,
    "hadith_dhikr": True,
    "instant_quran": True,
    "feedback_system": True,
    "leaderboard": True,
    "daily_receive": True,
    "force_join": True,
    "broadcast": True,
    "admin_panel": True,
    "smart_rewards": True,
    "user_titles": True,
    "achievement_system": True,
    "reminder_system": True,
    "statistics_advanced": True,
    "best_user_daily": True,
    "best_user_weekly": True,
    "referral_system": True,
    "arabic_language": True,
    "islamic_knowledge_engine": True,
    "internet_search": True,
    "favorites": True,
    "surveys": True,
    "weekly_report": True,
    "auto_backup": True,
    "profile_edit": True,
    "motivational_messages": True,
    "religious_reminders": True,
    "faq_system": True,
    "mahdi_section": True
}

# =========================================================
# ۳. سیستم چندزبانه کامل
# =========================================================
LANGS = {
    "fa": {
        "select_lang": "🌍 لطفاً زبان موردنظرت را انتخاب کن:",
        "welcome": "سلام {name} عزیز! 😍\nبه ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.\n\n🌟 همراه همیشگی تو در مسیر نور و معرفت.\n\nاز منوی زیر انتخاب کن:",
        "force_join": "🌸 سلام {name} جان!\n\nبرای استفاده از ربات، لطفاً ابتدا عضو کانال کانون قرآن شو:\n{channel}\n\nپس از عضویت، دوباره /start را بزن.",
        "joined_success": "✅ عضویتت تایید شد. خوش اومدی زندگی! 🌸",
        "not_joined_yet": "🥲 هنوز عضویتت تایید نشده. اول عضو کانال شو، بعد دوباره روی دکمه تأیید بزن.",
        "ai_prompt": "🧠 سوالت رو بپرس زندگی! من با عشق و علم جواب می‌دم.",
        "ai_wait": "⏳ یک لحظه صبر کن... دارم با تمام وجود فکر می‌کنم!",
        "admin_msg_prompt": "📩 با خیال راحت پیامت رو بنویس. من می‌رسونم به ادمین.",
        "admin_msg_sent": "✅ پیامت با عشق برای ادمین ارسال شد. 🙏",
        "under_construction": "🚧 این بخش در حال زیباتر شدن است. به‌زودی می‌آید.",
        "stats": "📊 آمار تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}\n⭐ امتیاز پیشنهادات: {feedback_score}\n📅 تاریخ عضویت: {join_date}\n👑 عنوان: {title}\n🎯 بازدیدها: {visits}\n✅ کوئست‌های انجام شده: {quests}\n🤝 دعوت‌ها: {referrals}\n💰 امتیاز دعوت: {referral_earned}",
        "about": "🌸 این ربات با عشق توسط کانون قرآن و عترت دانشگاه علوم پزشکی شیراز طراحی شده است.\n\n📚 امکانات:\n• جستجوی هوشمند اسلامی با AI 🧠\n• حدیث و ذکر روزانه 🕊️\n• قرآن در لحظه ✨\n• کارنامه و لیگ قرآنی 🏆\n• ارسال روزانه 🔔\n• پیشنهاد و انتقاد ⭐\n• کوئست‌های روزانه 🎯\n• بهترین کاربران 🏅\n• سیستم دعوت 🤝\n• ذخیره آیات مورد علاقه ❤️\n• نظرسنجی 📝\n• یادآوری مناسبت‌ها 🕌\n• گزارش هفتگی 📊\n• پشتیبانی از زبان عربی 🇸🇦\n• بخش مهدویت 🕊️\n\n💚 همراه همیشگی تو در مسیر نور",
        "daily_enable": "✅ دریافت روزانه فعال شد. هر روز با عشق محتوای جدید می‌فرستم.",
        "daily_disable": "❌ دریافت روزانه غیرفعال شد. هر وقت خواستی فعالش کن.",
        "daily_toggle": "🔔 دریافت روزانه",
        "back_to_menu": "🏠 برگشت به منوی اصلی",
        "search_quran_prompt": "🧠 کلمه یا موضوع مورد نظرت رو بفرست تا با هوش مصنوعی جستجو کنم.",
        "article_prompt": "📚 موضوع مقاله یا کلیدواژه‌ات رو بفرست.",
        "league_text": "🏆 لیگ قرآنی:\n\n{leaderboard}\n\n💡 برای کسب امتیاز:\n• جستجوی هوشمند 🧠\n• ارسال پیشنهاد 📝\n• بازدید روزانه 🌅\n• مطالعه حدیث 🕊️\n• دعوت از دوستان 🤝",
        "scorecard_text": "📋 کارنامه و رتبه تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n🎯 رتبه: {rank}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}\n⭐ امتیاز پیشنهادات: {feedback_score}\n👑 عنوان: {title}\n✅ کوئست‌ها: {quests}\n🤝 دعوت‌ها: {referrals}\n💰 امتیاز دعوت: {referral_earned}",
        "events_text": "📢 رویدادها و مسابقات کانون:\n\n🔹 جشنواره قرآن و عترت\n🔹 مسابقات حفظ و مفاهیم قرآن\n🔹 کارگاه‌های تفسیر و تدبر\n🔹 برنامه‌های ماه رمضان\n🔹 جلسات هفتگی قرآن\n🔹 مسابقات مقاله‌نویسی قرآنی\n\n📌 برای اطلاعات بیشتر به کانال مراجعه کن.",
        "unknown_error": "⚠️ یه خطای کوچک رخ داد. دوباره امتحان کن، مطمئنم موفق می‌شی.",
        "article_result": "📚 نتایج جستجوی مقالات علمی برای «{query}»:\n\n{results}\n\n💡 اگر نتیجه‌ای نیافتی، می‌تونی از مقالات پیشنهادی ما استفاده کنی.",
        "feedback_score_msg": "✅ پیشنهاد ارزشمند شما ثبت شد. {score} امتیاز به شما تعلق گرفت! 🌸",
        "feedback_no_score": "✅ پیشنهاد شما ثبت شد. برای دریافت امتیاز بیشتر، پیشنهاد خود را دقیق‌تر بنویسید. 💪",
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
        "admin_system": "💻 وضعیت سیستم",
        "admin_achievements": "🏅 مدیریت دستاوردها",
        "admin_best_users": "🏆 بهترین کاربران",
        "admin_referrals": "🤝 آمار دعوت‌ها",
        "admin_weekly_report": "📊 گزارش هفتگی",
        "admin_surveys": "📝 نظرسنجی‌ها",
        "daily_quran_title": "📘 آیه منتخب روز - قرآن کریم",
        "daily_sahifeh_title": "🤲 دعای منتخب روز - صحیفه سجادیه",
        "daily_nahj_title": "📜 فراز منتخب روز - نهج‌البلاغه",
        "menu_labels": {
            "smart_search": "🧠 جستجوی هوشمند",
            "hadith": "🕊️ حدیث و ذکر روز",
            "instant_quran": "✨ قرآن در لحظه",
            "events": "📢 رویدادها",
            "feedback": "📝 پیشنهاد/انتقاد",
            "admin_msg": "📨 پیام به ادمین",
            "stats": "📊 آمار من",
            "league": "🏆 لیگ قرآنی",
            "scorecard": "📋 کارنامه من",
            "change_lang": "🌍 تغییر زبان",
            "daily_toggle": "🔔 دریافت روزانه",
            "about": "ℹ️ درباره ربات",
            "help": "❓ راهنما",
            "share": "📤 اشتراک‌گذاری",
            "reminder": "⏰ یادآوری",
            "quests": "🎯 کوئست‌های روزانه",
            "best_users": "🏅 بهترین کاربران",
            "referral": "🤝 دعوت از دوستان",
            "favorites": "❤️ آیات مورد علاقه",
            "faq": "❓ سوالات متداول",
            "profile": "✏️ ویرایش پروفایل",
            "mahdi": "🕊️ مهدویت"
        }
    },
    "en": {
        "select_lang": "🌍 Please choose your language:",
        "welcome": "Hello {name}! 😍\nWelcome to the Quran & Etrat bot of SUMS.\nPlease choose an option:",
        "force_join": "🌸 To use the bot services, please join our channel first:\n{channel}\n\nThen press /start again.",
        "joined_success": "✅ Membership confirmed. Welcome!",
        "not_joined_yet": "🥲 Your membership is not confirmed yet. Please join first.",
        "ai_prompt": "🧠 Ask your question, dear! I'll answer with love and knowledge.",
        "ai_wait": "⏳ Please wait... thinking smart!",
        "admin_msg_prompt": "📩 Send your message and I'll forward it to admin:",
        "admin_msg_sent": "✅ Your message was sent to admin.",
        "under_construction": "🚧 This section is under construction.",
        "stats": "📊 Your stats:\n\n👤 Name: {name}\n🏆 Score: {score}\n📖 Searches: {search_count}\n🔥 Streak: {streak}\n⭐ Feedback Score: {feedback_score}\n📅 Join Date: {join_date}\n👑 Title: {title}\n🎯 Visits: {visits}\n✅ Quests completed: {quests}\n🤝 Referrals: {referrals}\n💰 Referral earned: {referral_earned}",
        "about": "🌸 This bot is designed with love by the Quran & Etrat Center of Shiraz University of Medical Sciences.\n\n📚 Features:\n• Smart Islamic Search with AI 🧠\n• Hadith & Dhikr 🕊️\n• Instant Quran ✨\n• Scorecard & Quran League 🏆\n• Daily Receive 🔔\n• Suggestion & Critique ⭐\n• Daily Quests 🎯\n• Best Users 🏅\n• Referral System 🤝\n• Favorite Verses ❤️\n• Surveys 📝\n• Religious Reminders 🕌\n• Weekly Report 📊\n• Arabic Support 🇸🇦\n• Mahdi Section 🕊️",
        "daily_enable": "✅ Daily receive enabled.",
        "daily_disable": "❌ Daily receive disabled.",
        "daily_toggle": "🔔 Daily Receive",
        "back_to_menu": "🏠 Back to main menu",
        "search_quran_prompt": "🧠 Send a word or topic to search with AI.",
        "article_prompt": "📚 Send your article topic or keyword.",
        "league_text": "🏆 Quran League:\n\n{leaderboard}\n\n💡 To earn points:\n• Smart Search 🧠\n• Send feedback 📝\n• Daily visit 🌅\n• Read Hadith 🕊️\n• Invite friends 🤝",
        "scorecard_text": "📋 Your scorecard and rank:\n\n👤 Name: {name}\n🏆 Score: {score}\n🎯 Rank: {rank}\n📖 Searches: {search_count}\n🔥 Streak: {streak}\n⭐ Feedback Score: {feedback_score}\n👑 Title: {title}\n✅ Quests: {quests}\n🤝 Referrals: {referrals}\n💰 Referral earned: {referral_earned}",
        "events_text": "📢 Events and contests:\n\n🔹 Quran and Etrat Festival\n🔹 Memorization contests\n🔹 Interpretation workshops\n🔹 Ramadan programs\n🔹 Weekly Quran sessions\n🔹 Quranic writing contests",
        "unknown_error": "⚠️ A small error occurred. Please try again.",
        "article_result": "📚 Scientific article results for «{query}»:\n\n{results}\n\n💡 If no results found, try our suggested articles.",
        "feedback_score_msg": "✅ Your valuable suggestion was recorded. You earned {score} points! 🌸",
        "feedback_no_score": "✅ Your suggestion was recorded. To earn more points, write a more detailed suggestion. 💪",
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
        "admin_system": "💻 System Status",
        "admin_achievements": "🏅 Manage Achievements",
        "admin_best_users": "🏆 Best Users",
        "admin_referrals": "🤝 Referral Stats",
        "admin_weekly_report": "📊 Weekly Report",
        "admin_surveys": "📝 Surveys",
        "daily_quran_title": "📘 Daily Quran Verse",
        "daily_sahifeh_title": "🤲 Daily Sahifeh Supplication",
        "daily_nahj_title": "📜 Daily Nahjul Balagha",
        "menu_labels": {
            "smart_search": "🧠 Smart Search",
            "hadith": "🕊️ Hadith & Dhikr",
            "instant_quran": "✨ Instant Quran",
            "events": "📢 Events",
            "feedback": "📝 Suggestion/Critique",
            "admin_msg": "📨 Message Admin",
            "stats": "📊 My Stats",
            "league": "🏆 Quran League",
            "scorecard": "📋 My Scorecard",
            "change_lang": "🌍 Change Language",
            "daily_toggle": "🔔 Daily Receive",
            "about": "ℹ️ About Bot",
            "help": "❓ Help",
            "share": "📤 Share",
            "reminder": "⏰ Reminder",
            "quests": "🎯 Daily Quests",
            "best_users": "🏅 Best Users",
            "referral": "🤝 Invite Friends",
            "favorites": "❤️ Favorite Verses",
            "faq": "❓ FAQ",
            "profile": "✏️ Edit Profile",
            "mahdi": "🕊️ Mahdi"
        }
    },
    "ar": {
        "select_lang": "🌍 الرجاء اختيار لغتك:",
        "welcome": "مرحباً {name}! 😍\nمرحباً بك في بوت القرآن والعترة بجامعة علوم الطب شيراز.\nالرجاء اختيار خيار:",
        "force_join": "🌸 للاستفادة من خدمات البوت، الرجاء الانضمام إلى قناتنا أولاً:\n{channel}\n\nثم اضغط /start مرة أخرى.",
        "joined_success": "✅ تم تأكيد العضوية. مرحباً بك!",
        "not_joined_yet": "🥲 لم يتم تأكيد عضويتك بعد. الرجاء الانضمام أولاً.",
        "ai_prompt": "🧠 اسأل سؤالك، عزيزي! سأجيب بالحب والمعرفة.",
        "ai_wait": "⏳ الرجاء الانتظار... جاري التفكير!",
        "admin_msg_prompt": "📩 أرسل رسالتك وسأقوم بإرسالها إلى المشرف:",
        "admin_msg_sent": "✅ تم إرسال رسالتك إلى المشرف.",
        "under_construction": "🚧 هذا القسم قيد الإنشاء.",
        "stats": "📊 إحصائياتك:\n\n👤 الاسم: {name}\n🏆 النقاط: {score}\n📖 عمليات البحث: {search_count}\n🔥 الأيام المتتالية: {streak}\n⭐ نقاط الاقتراحات: {feedback_score}\n📅 تاريخ الانضمام: {join_date}\n👑 اللقب: {title}\n🎯 الزيارات: {visits}\n✅ المهام المنجزة: {quests}\n🤝 الدعوات: {referrals}\n💰 نقاط الدعوة: {referral_earned}",
        "about": "🌸 تم تصميم هذا البوت بحب من قبل مركز القرآن والعترة بجامعة علوم الطب شيراز.\n\n📚 الميزات:\n• البحث الإسلامي الذكي مع الذكاء الاصطناعي 🧠\n• الحديث والذكر اليومي 🕊️\n• القرآن في لحظة ✨\n• بطاقة النتائج والدوري القرآني 🏆\n• الاستلام اليومي 🔔\n• الاقتراحات والنقد ⭐\n• المهام اليومية 🎯\n• أفضل المستخدمين 🏅\n• نظام الدعوة 🤝\n• الآيات المفضلة ❤️\n• الاستطلاعات 📝\n• تذكير المناسبات 🕌\n• التقرير الأسبوعي 📊\n• دعم اللغة العربية 🇸🇦\n• قسم المهدي 🕊️",
        "daily_enable": "✅ تم تفعيل الاستلام اليومي.",
        "daily_disable": "❌ تم تعطيل الاستلام اليومي.",
        "daily_toggle": "🔔 الاستلام اليومي",
        "back_to_menu": "🏠 العودة إلى القائمة الرئيسية",
        "search_quran_prompt": "🧠 أرسل كلمة أو موضوع للبحث بالذكاء الاصطناعي.",
        "article_prompt": "📚 أرسل موضوع المقال أو الكلمة المفتاحية.",
        "league_text": "🏆 الدوري القرآني:\n\n{leaderboard}\n\n💡 لكسب النقاط:\n• البحث الذكي 🧠\n• إرسال اقتراح 📝\n• الزيارة اليومية 🌅\n• قراءة الحديث 🕊️\n• دعوة الأصدقاء 🤝",
        "scorecard_text": "📋 بطاقة نتائجك وترتيبك:\n\n👤 الاسم: {name}\n🏆 النقاط: {score}\n🎯 الترتيب: {rank}\n📖 عمليات البحث: {search_count}\n🔥 الأيام المتتالية: {streak}\n⭐ نقاط الاقتراحات: {feedback_score}\n👑 اللقب: {title}\n✅ المهام: {quests}\n🤝 الدعوات: {referrals}\n💰 نقاط الدعوة: {referral_earned}",
        "events_text": "📢 الفعاليات والمسابقات:\n\n🔹 مهرجان القرآن والعترة\n🔹 مسابقات حفظ وتفسير القرآن\n🔹 ورش التفسير والتدبر\n🔹 برامج شهر رمضان\n🔹 جلسات القرآن الأسبوعية\n🔹 مسابقات الكتابة القرآنية",
        "unknown_error": "⚠️ حدث خطأ بسيط. الرجاء المحاولة مرة أخرى.",
        "article_result": "📚 نتائج البحث عن المقالات العلمية لـ «{query}»:\n\n{results}\n\n💡 إذا لم تجد نتائج، جرب مقالاتنا المقترحة.",
        "feedback_score_msg": "✅ تم تسجيل اقتراحك القيم. حصلت على {score} نقاط! 🌸",
        "feedback_no_score": "✅ تم تسجيل اقتراحك. للحصول على نقاط أكثر، اكتب اقتراحاً أكثر تفصيلاً. 💪",
        "broadcast_prompt": "📢 الرجاء إرسال نص الإعلان العام:",
        "broadcast_success": "✅ تم إرسال الإعلان بنجاح إلى {count} مستخدم. 🌸",
        "broadcast_error": "⚠️ لا يوجد نص للإرسال.",
        "admin_panel": "🛠️ لوحة المشرف",
        "admin_stats": "📊 إحصائيات البوت",
        "admin_feedbacks": "📩 قائمة الاقتراحات",
        "admin_broadcast": "📢 إعلان عام",
        "admin_users": "👥 قائمة المستخدمين",
        "admin_schedule": "⏰ إعدادات الجدولة",
        "admin_features": "⚙️ التحكم في الميزات",
        "admin_logs": "📋 سجل الأخطاء",
        "admin_back": "🔄 العودة",
        "admin_system": "💻 حالة النظام",
        "admin_achievements": "🏅 إدارة الإنجازات",
        "admin_best_users": "🏆 أفضل المستخدمين",
        "admin_referrals": "🤝 إحصائيات الدعوات",
        "admin_weekly_report": "📊 التقرير الأسبوعي",
        "admin_surveys": "📝 الاستطلاعات",
        "daily_quran_title": "📘 آية مختارة من القرآن الكريم",
        "daily_sahifeh_title": "🤲 دعاء مختار من الصحيفة السجادية",
        "daily_nahj_title": "📜 نص مختار من نهج البلاغة",
        "menu_labels": {
            "smart_search": "🧠 البحث الذكي",
            "hadith": "🕊️ الحديث والذكر اليومي",
            "instant_quran": "✨ القرآن في لحظة",
            "events": "📢 الفعاليات",
            "feedback": "📝 اقتراح/نقد",
            "admin_msg": "📨 رسالة إلى المشرف",
            "stats": "📊 إحصائياتي",
            "league": "🏆 الدوري القرآني",
            "scorecard": "📋 بطاقة نتائجي",
            "change_lang": "🌍 تغيير اللغة",
            "daily_toggle": "🔔 الاستلام اليومي",
            "about": "ℹ️ عن البوت",
            "help": "❓ المساعدة",
            "share": "📤 مشاركة",
            "reminder": "⏰ تذكير",
            "quests": "🎯 المهام اليومية",
            "best_users": "🏅 أفضل المستخدمين",
            "referral": "🤝 دعوة الأصدقاء",
            "favorites": "❤️ الآيات المفضلة",
            "faq": "❓ الأسئلة الشائعة",
            "profile": "✏️ تعديل الملف الشخصي",
            "mahdi": "🕊️ المهدي"
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
# ۴. داده‌های مهدویت
# =========================================================
MAHDI_MESSAGES_DATA = [
    {"id": "mahdi_salawat_5", "title": "🕊️ ۵ صلوات برای امام زمان", "desc": "۵ صلوات هدیه به امام زمان (عج)", "points": 3, "message": "🌟 امروز ۵ صلوات برای ظهور امام زمان (عج) هدیه بفرست!\nاللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَآلِ مُحَمَّدٍ وَعَجِّلْ فَرَجَهُمْ 🌸"},
    {"id": "mahdi_salawat_14", "title": "🕊️ ۱۴ صلوات برای امام زمان", "desc": "۱۴ صلوات هدیه به امام زمان (عج)", "points": 5, "message": "🌟 ۱۴ صلوات نذر ظهور!\n🌹 هر صلوات، یک قدم به ظهور نزدیک‌تر!\nاللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَآلِ مُحَمَّدٍ وَعَجِّلْ فَرَجَهُمْ 💚"},
    {"id": "mahdi_salawat_72", "title": "🕊️ ۷۲ صلوات برای امام زمان", "desc": "۷۲ صلوات هدیه به امام زمان (عج)", "points": 10, "message": "🌟 ۷۲ صلوات به نیت ظهور!\n✨ هر صلوات، نوری بر دل امام زمان (عج)\nاللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَآلِ مُحَمَّدٍ وَعَجِّلْ فَرَجَهُمْ 🕊️"},
    {"id": "mahdi_gift", "title": "🎁 هدیه به امام زمان", "desc": "یک هدیه معنوی به امام زمان (عج)", "points": 3, "message": "🎁 امروز چه هدیه‌ای به امام زمان (عج) دادی؟\n💚 یک کار خوب، یک دعا، یک کمک به دیگران...\n🌹 همه اینها هدیه‌ای برای ظهور است!"},
    {"id": "mahdi_help", "title": "🤝 کمک به دیگران", "desc": "کمک به دیگران به نیت امام زمان", "points": 5, "message": "🤝 امروز به کسی کمک کردی؟\n💚 هر کمک به دیگران، کمک به ظهور است!\n🌟 امام زمان (عج) منتظر این کارهای خوب توست!"},
    {"id": "mahdi_dua", "title": "🤲 دعا برای ظهور", "desc": "دعا برای تعجیل در فرج", "points": 3, "message": "🤲 امروز برای ظهور امام زمان (عج) دعا کن!\n🌹 اللَّهُمَّ كُنْ لِوَلِيِّكَ الْحُجَّةِ بْنِ الْحَسَنِ...\n💚 هر دعا، امیدی تازه برای ظهور است!"},
    {"id": "mahdi_thought", "title": "💭 تفکر درباره ظهور", "desc": "تفکر درباره ظهور و آمادگی", "points": 2, "message": "💭 امروز به ظهور امام زمان (عج) فکر کن!\n🌟 اگر امروز ظهور کند، آیا آماده‌ای؟\n🌹 با خودت عهد کن که بهترین نسخه خودت باشی!"},
]

# =========================================================
# ۵. داده‌های اولیه و نمونه
# =========================================================
DEFAULT_QURAN_SEED = [
    {"index": 1, "surah": "حمد", "verse": 1, "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "trans": "به نام خداوند بخشنده مهربان", "interpretation": "شروع هر کار با نام خدا، نشانه توکل و ایمان است.", "topics": ["ایمان", "توکل", "شروع", "بسم الله"]},
    {"index": 2, "surah": "حمد", "verse": 2, "text": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "trans": "ستایش مخصوص خداوندی است که پروردگار جهانیان است", "interpretation": "تمام هستی نشانه‌های پروردگار جهانیان است.", "topics": ["حمد", "ستایش", "خداوند", "جهانیان"]},
    {"index": 3, "surah": "حمد", "verse": 3, "text": "الرَّحْمَٰنِ الرَّحِيمِ", "trans": "بخشنده و مهربان است", "interpretation": "رحمانیت خدا، الگوی پزشکان در مهربانی با بیماران است.", "topics": ["رحمت", "مهربانی", "بخشش"]},
    {"index": 4, "surah": "حمد", "verse": 4, "text": "مَالِكِ يَوْمِ الدِّينِ", "trans": "مالک روز جزاست", "interpretation": "روز جزا یادآور مسئولیت پزشکان در قبال جان انسان‌هاست.", "topics": ["جزا", "مسئولیت", "حسابرسی"]},
    {"index": 5, "surah": "حمد", "verse": 5, "text": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "trans": "تنها تو را می‌پرستیم و تنها از تو یاری می‌جوییم", "interpretation": "پزشکان در درمان بیماران، به خداوند توکل کنند.", "topics": ["عبادت", "توکل", "یاری"]},
    {"index": 6, "surah": "بقره", "verse": 1, "text": "الم", "trans": "الف، لام، میم", "interpretation": "حروف مقطعه، رمز عظمت قرآن.", "topics": ["قرآن", "عظمت"]},
    {"index": 7, "surah": "بقره", "verse": 2, "text": "ذَٰلِكَ الْكِتَابُ لَا رَيْبَ ۛ فِيهِ ۛ هُدًى لِّلْمُتَّقِينَ", "trans": "این کتابی است که هیچ شکی در آن نیست و مایه هدایت برای پرهیزگاران است", "interpretation": "قرآن کتاب هدایت برای متقین است.", "topics": ["هدایت", "تقوا", "قرآن"]},
    {"index": 8, "surah": "بقره", "verse": 3, "text": "الَّذِينَ يُؤْمِنُونَ بِالْغَيْبِ وَيُقِيمُونَ الصَّلَاةَ وَمِمَّا رَزَقْنَاهُمْ يُنفِقُونَ", "trans": "کسانی که به غیب ایمان دارند و نماز را برپا می‌دارند و از آنچه روزی‌شان داده‌ایم انفاق می‌کنند", "interpretation": "مؤمنان واقعی، اهل ایمان، نماز و انفاق هستند.", "topics": ["ایمان", "نماز", "انفاق"]},
    {"index": 9, "surah": "بقره", "verse": 4, "text": "وَالَّذِينَ يُؤْمِنُونَ بِمَا أُنزِلَ إِلَيْكَ وَمَا أُنزِلَ مِن قَبْلِكَ وَبِالْآخِرَةِ هُمْ يُوقِنُونَ", "trans": "و به آنچه بر تو و پیش از تو نازل شده ایمان دارند و به آخرت یقین دارند", "interpretation": "ایمان به همه کتب آسمانی و روز قیامت.", "topics": ["ایمان", "آخرت", "کتب آسمانی"]},
    {"index": 10, "surah": "بقره", "verse": 5, "text": "أُولَٰئِكَ عَلَىٰ هُدًى مِّن رَّبِّهِمْ ۖ وَأُولَٰئِكَ هُمُ الْمُفْلِحُونَ", "trans": "ایشان از جانب پروردگارشان بر هدایتند و ایشان رستگارانند", "interpretation": "رستگاری در گرو هدایت الهی است.", "topics": ["رستگاری", "هدایت"]},
]

DEFAULT_NAHJ_SEED = [
    {"index": 1, "type": "خطبه", "number": 1, "text": "الْحَمْدُ لِلَّهِ الَّذِی لَا یَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ", "trans": "ستایش خدایی را که سخنوران در ستودن او فرومانند", "interpretation": "عظمت خداوند فراتر از توصیف است.", "topics": ["عظمت خدا", "ستایش"]},
    {"index": 2, "type": "حکمت", "number": 1, "text": "كُنْ فِي الْفِتْنَةِ كَابْنِ اللَّبُونِ", "trans": "در فتنه‌ها چونان شتر دو ساله باش", "interpretation": "در بحران‌های پزشکی، متواضع باش.", "topics": ["فتنه", "تواضع", "بحران"]},
    {"index": 3, "type": "خطبه", "number": 2, "text": "مَا زَالَ اللَّهُ يُرِيدُ بِكُمُ الْخَيْرَ", "trans": "خداوند همواره خیر شما را می‌خواهد", "interpretation": "خداوند برای بندگانش خیر می‌خواهد.", "topics": ["خیر", "رحمت"]},
    {"index": 4, "type": "نامه", "number": 1, "text": "إِلَى مَالِكٍ الْأَشْتَرِ", "trans": "نامه به مالک اشتر", "interpretation": "نامه به مالک اشتر، فرمان حکومتی.", "topics": ["حکومت", "عدالت"]},
    {"index": 5, "type": "حکمت", "number": 2, "text": "مَنْ أَبْطَأَ بِهِ عَمَلُهُ لَمْ يُسْرِعْ بِهِ نَسَبُهُ", "trans": "هر که را عملش کند کند، نسبش تندش نمی‌کند", "interpretation": "ارزش انسان به عمل اوست، نه به نسب.", "topics": ["عمل", "ارزش"]},
    {"index": 6, "type": "خطبه", "number": 3, "text": "إِنَّ اللَّهَ سُبْحَانَهُ لَمْ يَخْلُقِ الْخَلْقَ عَبَثًا", "trans": "خداوند متعال، خلقت را بیهوده نیافریده است", "interpretation": "هستی هدفمند است.", "topics": ["هدفمندی", "خلقت"]},
    {"index": 7, "type": "حکمت", "number": 3, "text": "الصَّبْرُ صَبْرَانِ: صَبْرٌ عَلَى مَا تَكْرَهُ، وَصَبْرٌ عَمَّا تُحِبُّ", "trans": "صبر دو گونه است: صبر بر ناخوشایندها و صبر بر خوشایندها", "interpretation": "صبر در همه حال لازم است.", "topics": ["صبر", "تحمل"]},
]

DEFAULT_SAHIFEH_SEED = [
    {"index": 1, "dua": 1, "title": "در ستایش پروردگار", "text": "الْحَمْدُ لِلَّهِ الْأَوَّلِ بلا أَوَّلٍ كَانَ قَبْلَهُ", "trans": "ستایش خدای را که نخستین است", "interpretation": "خداوند آغاز همه چیز است.", "topics": ["ستایش", "خدا", "آغاز"]},
    {"index": 2, "dua": 2, "title": "دعا برای طلب رحمت", "text": "إِلَٰهِى أَنْتَ الَّذِى وَسِعْتَ كُلَّ شَىْءٍ رَحْمَةً وَعِلْمًا", "trans": "خدایا تو کسی هستی که رحمت و علمت همه چیز را فراگرفته", "interpretation": "رحمت خداوند گسترده است.", "topics": ["رحمت", "علم"]},
    {"index": 3, "dua": 3, "title": "دعا برای طلب مغفرت", "text": "اللَّهُمَّ اغْفِرْ لَنَا ذُنُوبَنَا وَإِسْرَافَنَا فِي أَمْرِنَا", "trans": "خدایا گناهان و زیاده‌روی‌های ما را ببخش", "interpretation": "طلب مغفرت از خداوند.", "topics": ["مغفرت", "بخشش"]},
    {"index": 4, "dua": 4, "title": "دعا برای روزی و برکت", "text": "اللَّهُمَّ ارْزُقْنَا رِزْقًا حَلَالًا طَيِّبًا", "trans": "خدایا روزی حلال و پاک به ما عطا کن", "interpretation": "طلب روزی حلال.", "topics": ["روزی", "حلال"]},
    {"index": 5, "dua": 5, "title": "دعا برای توفیق در عبادت", "text": "اللَّهُمَّ أَعِنَّا عَلَى ذِكْرِكَ وَشُكْرِكَ وَحُسْنِ عِبَادَتِكَ", "trans": "خدایا ما را بر یاد و شکر و عبادت خود یاری ده", "interpretation": "طلب توفیق عبادت.", "topics": ["عبادت", "یاد خدا"]},
    {"index": 6, "dua": 6, "title": "دعا برای سلامتی", "text": "اللَّهُمَّ عَافِنَا فِي أَبْدَانِنَا وَأَجْسَادِنَا", "trans": "خدایا به بدن‌ها و جسم‌های ما عافیت عطا کن", "interpretation": "طلب سلامتی و عافیت.", "topics": ["سلامتی", "عافیت"]},
    {"index": 7, "dua": 7, "title": "دعا برای اهل ایمان", "text": "اللَّهُمَّ اغْفِرْ لِلْمُؤْمِنِينَ وَالْمُؤْمِنَاتِ", "trans": "خدایا مردان و زنان مؤمن را بیامرز", "interpretation": "طلب مغفرت برای مؤمنان.", "topics": ["مغفرت", "ایمان"]},
]

# =========================================================
# ۶. داده‌های موضوعات قرآن
# =========================================================
DEFAULT_TOPICS = {
    "صبر": {"synonyms": ["صبر", "شکیبایی", "استقامت", "تحمل"], "keywords": ["صبر", "شکیبایی", "استقامت"]},
    "امید": {"synonyms": ["امید", "امیدواری", "نشاط", "شادی"], "keywords": ["امید", "امیدواری", "نشاط"]},
    "غم": {"synonyms": ["غم", "اندوه", "ناراحتی", "غمگینی", "یأس"], "keywords": ["غم", "اندوه", "ناراحتی", "یأس"]},
    "استرس": {"synonyms": ["استرس", "اضطراب", "نگرانی", "دلهره", "فشار"], "keywords": ["استرس", "اضطراب", "نگرانی"]},
    "نماز": {"synonyms": ["نماز", "صلات", "عابد"], "keywords": ["نماز", "صلات"]},
    "توکل": {"synonyms": ["توکل", "اعتماد", "تکیه"], "keywords": ["توکل", "اعتماد"]},
    "رحمت": {"synonyms": ["رحمت", "مهربانی", "بخشش", "رحم"], "keywords": ["رحمت", "مهربانی", "بخشش"]},
    "ایمان": {"synonyms": ["ایمان", "باور", "یقین", "اعتقاد"], "keywords": ["ایمان", "باور", "یقین"]},
    "عدالت": {"synonyms": ["عدالت", "انصاف", "برابری"], "keywords": ["عدالت", "انصاف"]},
    "آرامش": {"synonyms": ["آرامش", "سکون", "طمأنینه", "آسایش"], "keywords": ["آرامش", "طمأنینه"]},
}

# =========================================================
# ۷. احادیث و ذکر روزانه
# =========================================================
HADITHS_WITH_DHIKR = [
    {"hadith": "بهترین شما کسی است که قرآن را بیاموزد و به دیگران یاد دهد. 🌸", "arabic": "خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ", "source": "📚 صحیح بخاری، جلد ۶، صفحه ۵۰۲", "source2": "📚 اصول کافی، جلد ۲، صفحه ۶۰۵", "dhikr": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ (۱۰۰ بار)", "category": "آموزش", "topics": ["آموزش", "علم", "یادگیری"]},
    {"hadith": "در قرآن بیندیشید که بهار دل‌هاست. ✨", "arabic": "تَدَبَّرُوا الْقُرْآنَ فَإِنَّهُ رَبِيعُ الْقُلُوبِ", "source": "📚 نهج‌البلاغه، خطبه ۱۷۶", "source2": "📚 بحارالانوار، جلد ۸۹، صفحه ۱۹۸", "dhikr": "لَا إِلَٰهَ إِلَّا اللَّهُ (۱۰۰ بار)", "category": "تفکر", "topics": ["تفکر", "آرامش", "قرآن"]},
    {"hadith": "قرآن عهد الهی با بندگان است. 📖", "arabic": "الْقُرْآنُ عَهْدُ اللَّهِ إِلَى خَلْقِهِ", "source": "📚 بحارالانوار، جلد ۸۹، صفحه ۲۰۳", "source2": "📚 تفسیر الصافی، جلد ۱، صفحه ۴۵", "dhikr": "اللَّهُ أَكْبَرُ (۱۰۰ بار)", "category": "تلاوت", "topics": ["تلاوت", "قرآن"]},
    {"hadith": "خانه‌هایتان را با تلاوت قرآن نورانی کنید. 🕯️", "arabic": "نَوِّرُوا بُيُوتَكُمْ بِتِلَاوَةِ الْقُرْآنِ", "source": "📚 اصول کافی، جلد ۲، صفحه ۶۱۰", "source2": "📚 مستدرک الوسائل، جلد ۴، صفحه ۲۴۲", "dhikr": "أَسْتَغْفِرُ اللَّهَ (۱۰۰ بار)", "category": "نورانی‌سازی", "topics": ["نور", "قرآن"]},
    {"hadith": "هر کس قرآن را با صدای بلند بخواند، اجر شهید دارد. 🌹", "arabic": "مَنْ قَرَأَ الْقُرْآنَ بِجَهْرٍ فَلَهُ أَجْرُ الشَّهِيدِ", "source": "📚 ثواب الاعمال، صفحه ۱۵۸", "source2": "📚 وسائل الشیعه، جلد ۶، صفحه ۱۹۹", "dhikr": "سُبْحَانَ اللَّهِ وَالْحَمْدُ لِلَّهِ (۱۰۰ بار)", "category": "تلاوت", "topics": ["اجر", "شهادت"]},
    {"hadith": "مؤمنان در محبت مانند یک پیکرند. 💚", "arabic": "الْمُؤْمِنُونَ كَجَسَدٍ وَاحِدٍ", "source": "📚 صحیح مسلم، جلد ۴، صفحه ۶۵۴", "source2": "📚 صحیح بخاری، جلد ۳، صفحه ۴۸", "dhikr": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ (۱۰۰ بار)", "category": "اخوت", "topics": ["مهربانی", "اخوت"]},
]

INSTANT_QURAN_FULL = [
    {"surah": "الرحمن", "verse": 60, "arabic": "هَلْ جَزَاءُ الْإِحْسَانِ إِلَّا الْإِحْسَانُ", "trans": "آیا پاداش نیکی جز نیکی است؟"},
    {"surah": "الضحی", "verse": 1, "arabic": "وَالضُّحَىٰ", "trans": "سوگند به روشنایی روز"},
    {"surah": "الشرح", "verse": 5, "arabic": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا", "trans": "پس یقیناً با دشواری آسانی است"},
]

# =========================================================
# ۸. جوایز و عناوین کاربران
# =========================================================
USER_TITLES = {
    0: "🌱 تازه‌کار قرآنی",
    10: "📖 قرآن‌خوان مبتدی",
    30: "🌟 نورانی",
    60: "💎 حافظ قرآن",
    100: "🕊️ عاشق قرآن",
    150: "🔥 مجتهد قرآنی",
    250: "👑 سلطان قرآن",
    500: "🌹 پیشوای قرآنی"
}

USER_TITLE_DESCRIPTIONS = {
    "🌱 تازه‌کار قرآنی": "شروع راه نورانی!",
    "📖 قرآن‌خوان مبتدی": "قدم اول رو برداشتی!",
    "🌟 نورانی": "نور قرآن در دلت روشن شده!",
    "💎 حافظ قرآن": "به جمع حافظان پیوستی!",
    "🕊️ عاشق قرآن": "عشق به قرآن در دلت جای گرفته!",
    "🔥 مجتهد قرآنی": "تلاش تو ستودنی است!",
    "👑 سلطان قرآن": "تو یک سلطان در دنیای قرآنی!",
    "🌹 پیشوای قرآنی": "تو الگوی دیگران هستی!"
}

ACHIEVEMENTS = {
    "first_search": {"name": "🔍 اولین جستجو", "points": 10},
    "daily_visitor": {"name": "🌅 بازدید روزانه", "points": 5},
    "feedback_master": {"name": "📝 منتقد برتر", "points": 20},
    "quran_lover": {"name": "❤️ عاشق قرآن", "points": 15},
    "hadith_reader": {"name": "🕊️ حدیث‌خوان", "points": 10},
    "streak_7": {"name": "🔥 هفت روز پیاپی", "points": 25},
    "streak_30": {"name": "⭐ سی روز پیاپی", "points": 50},
    "score_100": {"name": "💎 صد امتیازی", "points": 30},
    "score_500": {"name": "👑 پانصد امتیازی", "points": 60},
    "referrer_bronze": {"name": "🥉 دعوت‌کننده برنزی", "points": 20},
    "referrer_silver": {"name": "🥈 دعوت‌کننده نقره‌ای", "points": 50},
    "referrer_gold": {"name": "🥇 دعوت‌کننده طلایی", "points": 100},
    "mahdi_salawat_5": {"name": "🕊️ ۵ صلوات برای ظهور", "points": 3},
    "mahdi_salawat_14": {"name": "🕊️ ۱۴ صلوات برای ظهور", "points": 5},
    "mahdi_salawat_72": {"name": "🕊️ ۷۲ صلوات برای ظهور", "points": 10},
    "mahdi_gift": {"name": "🎁 هدیه به امام زمان", "points": 3},
    "mahdi_help": {"name": "🤝 کمک به نیت ظهور", "points": 5},
    "mahdi_dua": {"name": "🤲 دعای ظهور", "points": 3},
    "mahdi_thought": {"name": "💭 تفکر درباره ظهور", "points": 2}
}

# =========================================================
# ۹. دکمه‌های جذاب برای کسب امتیاز
# =========================================================
QUEST_ACTIONS = [
    {"id": "smart_search", "label": "🧠 جستجوی هوشمند", "points": 5, "desc": "هر بار جستجوی هوشمند"},
    {"id": "daily_visit", "label": "🌅 بازدید روزانه", "points": 5, "desc": "هر روز از ربات بازدید کن"},
    {"id": "feedback", "label": "📝 ارسال پیشنهاد", "points": 5, "desc": "پیشنهاد سازنده بده"},
    {"id": "hadith_read", "label": "🕊️ مطالعه حدیث", "points": 2, "desc": "حدیث روزانه را بخوان"},
    {"id": "instant_quran", "label": "✨ قرآن در لحظه", "points": 2, "desc": "آیه لحظه را دریافت کن"},
    {"id": "streak_7", "label": "🔥 ۷ روز پیاپی", "points": 15, "desc": "هفت روز متوالی بازدید کن"},
    {"id": "streak_30", "label": "⭐ ۳۰ روز پیاپی", "points": 30, "desc": "سی روز متوالی بازدید کن"},
    {"id": "referral", "label": "🤝 دعوت از دوستان", "points": 10, "desc": "هر دعوت ۱۰ امتیاز"},
]

# =========================================================
# ۱۰. توابع راه‌اندازی و مدیریت فایل‌های JSON
# =========================================================
def ensure_library_files():
    files_to_create = [
        (QURAN_FILE, DEFAULT_QURAN_SEED),
        (NAHJ_FILE, DEFAULT_NAHJ_SEED),
        (SAHIFEH_FILE, DEFAULT_SAHIFEH_SEED),
        (ARTICLES_FILE, {}),
        (TOPICS_FILE, DEFAULT_TOPICS),
        (FAVORITES_FILE, {}),
        (SURVEYS_FILE, {}),
        (MAHDI_FILE, MAHDI_MESSAGES_DATA)
    ]
    for file_path, default_data in files_to_create:
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
                logger.info(f"📁 فایل {file_path} ایجاد شد.")
            except Exception as e:
                logger.error(f"خطا در ایجاد فایل {file_path}: {e}")
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def load_library():
    global QURAN_DATA, NAHJ_DATA, SAHIFEH_DATA, ARTICLE_CACHE, TOPICS_DATA, FAVORITES_DATA, SURVEYS_DATA, MAHDI_MESSAGES
    try:
        ensure_library_files()
        with open(QURAN_FILE, "r", encoding="utf-8") as f:
            QURAN_DATA = json.load(f)
        with open(NAHJ_FILE, "r", encoding="utf-8") as f:
            NAHJ_DATA = json.load(f)
        with open(SAHIFEH_FILE, "r", encoding="utf-8") as f:
            SAHIFEH_DATA = json.load(f)
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            ARTICLE_CACHE = json.load(f)
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            TOPICS_DATA = json.load(f)
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            FAVORITES_DATA = json.load(f)
        with open(SURVEYS_FILE, "r", encoding="utf-8") as f:
            SURVEYS_DATA = json.load(f)
        with open(MAHDI_FILE, "r", encoding="utf-8") as f:
            MAHDI_MESSAGES = json.load(f)
        logger.info(f"📚 کتابخانه بارگذاری شد: قرآن={len(QURAN_DATA)}, نهج‌البلاغه={len(NAHJ_DATA)}, صحیفه={len(SAHIFEH_DATA)}")
        if not QURAN_DATA:
            QURAN_DATA = DEFAULT_QURAN_SEED
            save_library_file(QURAN_FILE, QURAN_DATA)
        if not NAHJ_DATA:
            NAHJ_DATA = DEFAULT_NAHJ_SEED
            save_library_file(NAHJ_FILE, NAHJ_DATA)
        if not SAHIFEH_DATA:
            SAHIFEH_DATA = DEFAULT_SAHIFEH_SEED
            save_library_file(SAHIFEH_FILE, SAHIFEH_DATA)
        if not TOPICS_DATA:
            TOPICS_DATA = DEFAULT_TOPICS
            save_library_file(TOPICS_FILE, TOPICS_DATA)
        if not FAVORITES_DATA:
            FAVORITES_DATA = {}
            save_library_file(FAVORITES_FILE, FAVORITES_DATA)
        if not SURVEYS_DATA:
            SURVEYS_DATA = {}
            save_library_file(SURVEYS_FILE, SURVEYS_DATA)
        if not MAHDI_MESSAGES:
            MAHDI_MESSAGES = MAHDI_MESSAGES_DATA
            save_library_file(MAHDI_FILE, MAHDI_MESSAGES)
    except Exception as e:
        logger.error(f"خطا در بارگذاری: {e}")
        QURAN_DATA = DEFAULT_QURAN_SEED
        NAHJ_DATA = DEFAULT_NAHJ_SEED
        SAHIFEH_DATA = DEFAULT_SAHIFEH_SEED
        TOPICS_DATA = DEFAULT_TOPICS

def save_library_file(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"خطا در ذخیره {file_path}: {e}")
        return False

# =========================================================
# ۱۱. سیستم بک‌آپ خودکار
# =========================================================
def auto_backup():
    if not FEATURES["auto_backup"]:
        return
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
        os.makedirs(backup_folder, exist_ok=True)
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, os.path.join(backup_folder, "bot_data.db"))
        json_files = [QURAN_FILE, NAHJ_FILE, SAHIFEH_FILE, ARTICLES_FILE, TOPICS_FILE, FAVORITES_FILE, SURVEYS_FILE, MAHDI_FILE]
        for file in json_files:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(backup_folder, file))
        if os.path.exists("bot.log"):
            shutil.copy2("bot.log", os.path.join(backup_folder, "bot.log"))
        backups = sorted([d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))])
        for backup in backups[:-7]:
            shutil.rmtree(os.path.join(BACKUP_DIR, backup))
        logger.info(f"✅ بک‌آپ خودکار در {backup_folder} انجام شد.")
    except Exception as e:
        logger.error(f"خطا در بک‌آپ: {e}")

def backup_scheduler():
    while True:
        try:
            now = datetime.now()
            if now.hour == 3 and now.minute == 0:
                auto_backup()
                time.sleep(60)
            time.sleep(30)
        except Exception as e:
            logger.error(f"خطا در اسکجولر بک‌آپ: {e}")
            time.sleep(60)

# =========================================================
# ۱۲. سیستم نظرسنجی و رای‌گیری
# =========================================================
def create_survey(question, options, created_by):
    survey_id = hashlib.md5(f"{question}_{time.time()}".encode()).hexdigest()[:8]
    SURVEYS_DATA[survey_id] = {
        "question": question,
        "options": options,
        "votes": {opt: [] for opt in options},
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    save_library_file(SURVEYS_FILE, SURVEYS_DATA)
    return survey_id

def vote_survey(survey_id, user_id, option):
    if survey_id not in SURVEYS_DATA:
        return False, "نظرسنجی وجود ندارد."
    survey = SURVEYS_DATA[survey_id]
    if not survey["active"]:
        return False, "این نظرسنجی به پایان رسیده است."
    if option not in survey["options"]:
        return False, "گزینه نامعتبر است."
    for opt, voters in survey["votes"].items():
        if user_id in voters:
            return False, "شما قبلاً رأی داده‌اید."
    survey["votes"][option].append(user_id)
    save_library_file(SURVEYS_FILE, SURVEYS_DATA)
    return True, "رأی شما با موفقیت ثبت شد."

def get_survey_results(survey_id):
    if survey_id not in SURVEYS_DATA:
        return None
    survey = SURVEYS_DATA[survey_id]
    total_votes = sum(len(voters) for voters in survey["votes"].values())
    results = []
    for option, voters in survey["votes"].items():
        percentage = (len(voters) / total_votes * 100) if total_votes > 0 else 0
        results.append({"option": option, "votes": len(voters), "percentage": round(percentage, 1)})
    return {"question": survey["question"], "total_votes": total_votes, "results": results, "active": survey["active"]}

# =========================================================
# ۱۳. سیستم ذخیره آیات مورد علاقه
# =========================================================
def add_favorite(user_id, verse_data):
    user_id = str(user_id)
    if user_id not in FAVORITES_DATA:
        FAVORITES_DATA[user_id] = []
    for item in FAVORITES_DATA[user_id]:
        if item.get("index") == verse_data.get("index"):
            return False, "📌 این آیه قبلاً در علاقه‌مندی‌های شما ذخیره شده است! ❤️"
    verse_info = {
        "index": verse_data.get("index"),
        "surah": verse_data.get("surah", "نامشخص"),
        "verse": verse_data.get("verse", "نامشخص"),
        "text": verse_data.get("text", ""),
        "trans": verse_data.get("trans", ""),
        "interpretation": verse_data.get("interpretation", ""),
        "topics": verse_data.get("topics", []),
        "saved_at": datetime.now().isoformat()
    }
    FAVORITES_DATA[user_id].append(verse_info)
    save_library_file(FAVORITES_FILE, FAVORITES_DATA)
    return True, "✅ آیه با موفقیت به علاقه‌مندی‌های شما اضافه شد! ❤️\n\n📖 می‌توانید از طریق دکمه «آیات مورد علاقه» در منوی اصلی به آن دسترسی داشته باشید."

def get_favorites(user_id):
    user_id = str(user_id)
    return FAVORITES_DATA.get(user_id, [])

def remove_favorite(user_id, index):
    user_id = str(user_id)
    if user_id not in FAVORITES_DATA:
        return False, "هیچ آیه‌ای در علاقه‌مندی‌های شما وجود ندارد."
    original_len = len(FAVORITES_DATA[user_id])
    FAVORITES_DATA[user_id] = [item for item in FAVORITES_DATA[user_id] if item.get("index") != index]
    if len(FAVORITES_DATA[user_id]) == original_len:
        return False, "این آیه در علاقه‌مندی‌های شما وجود ندارد."
    save_library_file(FAVORITES_FILE, FAVORITES_DATA)
    return True, "🗑️ آیه با موفقیت از علاقه‌مندی‌های شما حذف شد."

def format_favorites_message(favorites, lang="fa"):
    if not favorites:
        return "❤️ شما هنوز هیچ آیه‌ای ذخیره نکرده‌اید.\n\n💡 برای ذخیره آیه، پس از جستجوی هوشمند، روی دکمه «ذخیره این آیه» کلیک کنید."
    msg = "❤️ <b>آیات مورد علاقه شما</b>\n\n"
    msg += "═" * 30 + "\n\n"
    for i, fav in enumerate(favorites, 1):
        msg += f"📖 {i}. <b>{fav.get('surah', '')} (آیه {fav.get('verse', '')})</b>\n"
        msg += f"   {fav.get('text', '')[:60]}...\n"
        msg += f"   ✨ {fav.get('trans', '')[:40]}...\n"
        if fav.get('topics'):
            msg += f"   🏷️ {', '.join(fav.get('topics', [])[:3])}\n"
        msg += f"   📅 ذخیره شده: {fav.get('saved_at', '').split('T')[0] if fav.get('saved_at') else 'نامشخص'}\n"
        msg += "\n"
    msg += "═" * 30 + "\n"
    msg += f"📊 مجموع: {len(favorites)} آیه ذخیره شده"
    return msg

# =========================================================
# ۱۴. توابع تاریخ شمسی
# =========================================================
def get_persian_date():
    if HAS_JDATETIME:
        try:
            now = jdatetime.datetime.now()
            months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", 
                      "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
            return f"{now.day} {months[now.month-1]} {now.year}"
        except:
            pass
    now = datetime.now()
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    return f"{now.day} {months[now.month-1]} {now.year}"

def get_persian_greeting():
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        greeting = "صبح بخیر"
    elif 12 <= hour < 17:
        greeting = "ظهر بخیر"
    elif 17 <= hour < 21:
        greeting = "عصر بخیر"
    else:
        greeting = "شب بخیر"
    date = get_persian_date()
    return f"{greeting} 🌸\n📅 {date}"

def get_greeting(lang):
    now = datetime.now()
    hour = now.hour
    if lang == "fa":
        if 5 <= hour < 12:
            greeting = "صبح بخیر 🌅"
        elif 12 <= hour < 17:
            greeting = "ظهر بخیر ☀️"
        elif 17 <= hour < 21:
            greeting = "عصر بخیر 🌇"
        else:
            greeting = "شب بخیر 🌙"
        date = get_persian_date()
        return f"{greeting}\n📅 {date}"
    elif lang == "ar":
        if 5 <= hour < 12:
            return "صباح الخير 🌅"
        elif 12 <= hour < 17:
            return "مساء الخير ☀️"
        elif 17 <= hour < 21:
            return "مساء الخير 🌇"
        else:
            return "ليلة سعيدة 🌙"
    else:
        if 5 <= hour < 12:
            return "Good Morning 🌅"
        elif 12 <= hour < 17:
            return "Good Afternoon ☀️"
        elif 17 <= hour < 21:
            return "Good Evening 🌇"
        else:
            return "Good Night 🌙"

# =========================================================
# ۱۵. جستجوی اینترنتی با Serper.dev
# =========================================================
def internet_search(query, lang="fa"):
    if not FEATURES["internet_search"]:
        return []
    
    results = []
    
    # استفاده از Serper.dev (جستجوی گوگل)
    if SERPER_API_KEY and len(SERPER_API_KEY) > 10:
        try:
            headers = {
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "num": 10,
                "gl": "ir" if lang == "fa" else "us",
                "hl": "fa" if lang == "fa" else "en"
            }
            
            response = requests.post(
                SERPER_URL,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get("organic", [])[:10]:
                    results.append({
                        "title": item.get("title", "بدون عنوان"),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", ""),
                        "source": "Google (Serper.dev)",
                        "category": "اینترنت"
                    })
                
                # نتایج دانشنامه
                if data.get("knowledgeGraph"):
                    kg = data.get("knowledgeGraph")
                    if kg.get("description"):
                        results.append({
                            "title": kg.get("title", "دانشنامه"),
                            "snippet": kg.get("description", ""),
                            "link": kg.get("website", ""),
                            "source": "Knowledge Graph",
                            "category": "دانشنامه"
                        })
                
                # نتایج پرسش‌های مرتبط
                for item in data.get("peopleAlsoAsk", [])[:3]:
                    if item.get("snippet"):
                        results.append({
                            "title": item.get("question", "سوال مرتبط"),
                            "snippet": item.get("snippet", ""),
                            "link": "",
                            "source": "People Also Ask",
                            "category": "پرسش و پاسخ"
                        })
                
                logger.info(f"✅ جستجوی Serper.dev: {len(results)} نتیجه برای '{query}'")
                return results
                
            elif response.status_code == 401:
                logger.error("❌ کلید Serper.dev نامعتبر است!")
            elif response.status_code == 429:
                logger.warning("⚠️ محدودیت درخواست Serper.dev")
                
        except Exception as e:
            logger.error(f"خطا در جستجوی Serper.dev: {e}")
    
    # پشتیبان: Google Custom Search
    if GOOGLE_API_KEY and GOOGLE_CX_ID and not results:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CX_ID, "q": query, "num": 5}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", [])[:5]:
                    results.append({"title": item.get("title", "بدون عنوان"), "snippet": item.get("snippet", ""), "link": item.get("link", ""), "source": "Google"})
        except Exception as e:
            logger.error(f"خطا در جستجوی گوگل: {e}")
    
    # پشتیبان: OpenAlex
    if not results:
        try:
            url = f"https://api.openalex.org/works?search={query.replace(' ', '+')}&per-page=5"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for work in data.get("results", [])[:5]:
                    title = work.get("title", "بدون عنوان")
                    doi = work.get("doi", "")
                    if doi:
                        if doi.startswith("https://doi.org/"):
                            link = doi
                        elif doi.startswith("http://doi.org/"):
                            link = doi.replace("http://", "https://")
                        else:
                            link = f"https://doi.org/{doi}"
                    else:
                        link = ""
                    results.append({
                        "title": title,
                        "snippet": work.get("abstract", "")[:200] if work.get("abstract") else "",
                        "link": link,
                        "source": "OpenAlex"
                    })
        except Exception as e:
            logger.error(f"خطا در جستجوی OpenAlex: {e}")
    
    return results

# =========================================================
# ۱۶. موتور جستجوی هوشمند یکپارچه
# =========================================================
def expand_topic(query):
    query_lower = query.lower()
    expanded_terms = [query_lower]
    for topic, data in TOPICS_DATA.items():
        if query_lower in data.get("synonyms", []):
            expanded_terms.extend(data.get("keywords", []))
            expanded_terms.extend(data.get("synonyms", []))
            break
    for topic, data in TOPICS_DATA.items():
        for syn in data.get("synonyms", []):
            if fuzz.ratio(query_lower, syn) > 80:
                expanded_terms.extend(data.get("keywords", []))
                expanded_terms.extend(data.get("synonyms", []))
                break
    return list(set(expanded_terms))

def smart_search(query, lang="fa", use_ai=True):
    if not FEATURES["islamic_knowledge_engine"]:
        return None
    cache_key = hashlib.md5(f"{query}_{lang}_{use_ai}".encode()).hexdigest()
    if cache_key in SEARCH_CACHE:
        logger.info(f"جستجو از کش: {query}")
        return SEARCH_CACHE[cache_key]
    
    expanded_terms = expand_topic(query)
    results = {"quran": [], "nahj": [], "sahifeh": [], "hadith": [], "articles": [], "ai_response": "", "sources_count": 0}
    
    for item in QURAN_DATA:
        search_text = " ".join([str(item.get("text", "")), str(item.get("trans", "")), str(item.get("surah", "")), str(item.get("interpretation", "")), " ".join(item.get("topics", []))]).lower()
        for term in expanded_terms:
            if term in search_text:
                results["quran"].append(item)
                break
    
    for item in NAHJ_DATA:
        search_text = " ".join([str(item.get("text", "")), str(item.get("trans", "")), str(item.get("type", "")), str(item.get("interpretation", "")), " ".join(item.get("topics", []))]).lower()
        for term in expanded_terms:
            if term in search_text:
                results["nahj"].append(item)
                break
    
    for item in SAHIFEH_DATA:
        search_text = " ".join([str(item.get("text", "")), str(item.get("trans", "")), str(item.get("title", "")), str(item.get("interpretation", "")), " ".join(item.get("topics", []))]).lower()
        for term in expanded_terms:
            if term in search_text:
                results["sahifeh"].append(item)
                break
    
    for item in HADITHS_WITH_DHIKR:
        search_text = " ".join([str(item.get("hadith", "")), str(item.get("arabic", "")), " ".join(item.get("topics", []))]).lower()
        for term in expanded_terms:
            if term in search_text:
                results["hadith"].append(item)
                break
    
    if FEATURES["internet_search"]:
        internet_results = internet_search(query, lang)
        for item in internet_results:
            results["articles"].append({"title": item.get("title", ""), "summary": item.get("snippet", ""), "link": item.get("link", ""), "source": item.get("source", ""), "category": "اینترنتی"})
    
    results["sources_count"] = len(results["quran"]) + len(results["nahj"]) + len(results["sahifeh"]) + len(results["hadith"]) + len(results["articles"])
    
    if use_ai and FEATURES["deepseek_ai"]:
        try:
            quran_texts = [f"{r.get('surah', '')} آیه {r.get('verse', '')}: {r.get('text', '')}" for r in results["quran"][:3]]
            hadith_texts = [r.get('hadith', '') for r in results["hadith"][:2]]
            internet_texts = [f"{r.get('title', '')}: {r.get('summary', '')[:100]}" for r in results["articles"][:3]]
            
            ai_prompt = f"""Based on the following search results for "{query}", provide a comprehensive and thoughtful response:

Quran Results: {quran_texts}
Hadith Results: {hadith_texts}
Internet Results: {internet_texts}

Please provide a complete, warm, and insightful answer that combines these sources with your knowledge. 
Explain the spiritual and practical significance. Keep the tone friendly and inspiring. 
Include relevant links from the internet results when appropriate."""
            
            ai_response = ask_ai(ai_prompt, lang)
            if not ai_response.startswith(("⚠️", "🔑", "⏳", "💳", "🔧")):
                results["ai_response"] = ai_response
            else:
                results["ai_response"] = ""
        except Exception as e:
            logger.error(f"خطا در پاسخ AI: {e}")
            results["ai_response"] = ""
    
    results["quran"] = results["quran"][:5]
    results["nahj"] = results["nahj"][:3]
    results["sahifeh"] = results["sahifeh"][:3]
    results["hadith"] = results["hadith"][:3]
    results["articles"] = results["articles"][:10]
    
    SEARCH_CACHE[cache_key] = results
    return results

def format_smart_results(results, query, lang="fa"):
    if not results or results["sources_count"] == 0:
        return f"🔍 نتیجه‌ای برای «{query}» یافت نشد.\n\n💡 پیشنهاد: از کلمات کلیدی ساده‌تر استفاده کنید یا از بخش «هوش مصنوعی» سوال خود را بپرسید."
    
    output = f"🧠 <b>موتور جستجوی هوشمند - «{query}»</b>\n"
    output += f"📊 <b>{results['sources_count']} نتیجه</b> از {len(results['quran'])} قرآن + {len(results['hadith'])} حدیث + {len(results['articles'])} اینترنت\n"
    output += "="*60 + "\n\n"
    
    if results.get("ai_response"):
        output += "🤖 <b>تحلیل هوش مصنوعی:</b>\n"
        output += f"{results['ai_response']}\n\n"
        output += "─" * 40 + "\n\n"
    
    if results.get("articles"):
        output += "🌐 <b>نتایج جستجوی اینترنتی:</b>\n\n"
        for i, item in enumerate(results["articles"][:10], 1):
            output += f"{i}. <b>{item.get('title', 'بدون عنوان')}</b>\n"
            if item.get('summary'):
                output += f"   📝 {item.get('summary', '')[:200]}...\n"
            if item.get('link'):
                output += f"   🔗 <a href='{item['link']}'>لینک</a>\n"
            if item.get('source'):
                output += f"   📌 منبع: {item['source']}\n"
            output += "\n"
        output += "─" * 40 + "\n\n"
    
    if results.get("quran"):
        output += "📖 <b>آیات مرتبط در قرآن:</b>\n\n"
        for i, item in enumerate(results["quran"][:5], 1):
            output += f"{i}. <b>{item['surah']} (آیه {item['verse']})</b>\n"
            output += f"   {item['text']}\n"
            output += f"   ✨ {item['trans']}\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation'][:80]}...\n"
            output += "\n"
    
    if results.get("nahj"):
        output += "📜 <b>فرازهایی از نهج‌البلاغه:</b>\n\n"
        for i, item in enumerate(results["nahj"][:3], 1):
            output += f"{i}. <b>{item['type']} {item['number']}</b>\n"
            output += f"   {item['text']}\n"
            output += f"   ✨ {item['trans']}\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation'][:80]}...\n"
            output += "\n"
    
    if results.get("sahifeh"):
        output += "🤲 <b>دعاهایی از صحیفه سجادیه:</b>\n\n"
        for i, item in enumerate(results["sahifeh"][:3], 1):
            output += f"{i}. <b>{item['title']}</b>\n"
            output += f"   {item['text']}\n"
            output += f"   ✨ {item['trans']}\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation'][:80]}...\n"
            output += "\n"
    
    if results.get("hadith"):
        output += "🕊️ <b>احادیث مرتبط:</b>\n\n"
        for i, item in enumerate(results["hadith"][:3], 1):
            output += f"{i}. {item['hadith']}\n"
            if item.get('arabic'):
                output += f"   📝 {item['arabic']}\n"
            if item.get('source'):
                output += f"   📚 {item['source']}\n"
            output += "\n"
    
    output += "─" * 40 + "\n"
    output += "💡 برای سوالات بیشتر، از بخش «هوش مصنوعی» استفاده کنید."
    
    return output

# =========================================================
# ۱۷. جستجوی ساده قرآن (پشتیبان)
# =========================================================
def search_quran_only(q):
    if not FEATURES["quran_search"]:
        return []
    q = q.strip().lower()
    if not q or len(q) < 2:
        return []
    results = []
    for item in QURAN_DATA:
        search_text = " ".join([str(item.get("text", "")), str(item.get("trans", "")), str(item.get("surah", "")), str(item.get("interpretation", "")), " ".join(item.get("topics", []))]).lower()
        if q in search_text:
            results.append(item)
    seen = set()
    unique_results = []
    for item in results:
        item_key = f"{item.get('index', '')}_{item.get('text', '')}"
        if item_key not in seen:
            seen.add(item_key)
            unique_results.append(item)
    return unique_results[:10]

def search_other_books(q):
    q = q.strip().lower()
    if not q or len(q) < 2:
        return []
    results = []
    for item in NAHJ_DATA:
        search_text = " ".join([str(item.get("text", "")), str(item.get("trans", "")), str(item.get("type", "")), str(item.get("interpretation", "")), " ".join(item.get("topics", []))]).lower()
        if q in search_text:
            item["book_type"] = "نهج‌البلاغه"
            results.append(item)
    for item in SAHIFEH_DATA:
        search_text = " ".join([str(item.get("text", "")), str(item.get("trans", "")), str(item.get("title", "")), str(item.get("interpretation", "")), " ".join(item.get("topics", []))]).lower()
        if q in search_text:
            item["book_type"] = "صحیفه سجادیه"
            results.append(item)
    seen = set()
    unique_results = []
    for item in results:
        item_key = f"{item.get('index', '')}_{item.get('text', '')}"
        if item_key not in seen:
            seen.add(item_key)
            unique_results.append(item)
    return unique_results[:5]

def format_search_result(item, book_name="قرآن"):
    if book_name == "قرآن":
        return f"""📖 <b>{item['surah']} (آیه {item['verse']})</b>\n{item['text']}\n✨ {item['trans']}\n💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}\n🏷️ <b>موضوعات:</b> {', '.join(item.get('topics', ['عمومی']))}"""
    elif book_name == "نهج‌البلاغه":
        return f"""📜 <b>{item['type']} {item['number']}</b>\n{item['text']}\n✨ {item['trans']}\n💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}\n🏷️ <b>موضوعات:</b> {', '.join(item.get('topics', ['عمومی']))}"""
    elif book_name == "صحیفه سجادیه":
        return f"""🤲 <b>{item['title']} (دعای {item['dua']})</b>\n{item['text']}\n✨ {item['trans']}\n💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}\n🏷️ <b>موضوعات:</b> {', '.join(item.get('topics', ['عمومی']))}"""
    return f"📚 <b>{item.get('title', '')}</b>\n{item['text']}\n✨ {item['trans']}\n💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}"

# =========================================================
# ۱۸. سیستم پاداش و امتیازدهی هوشمند
# =========================================================
def calculate_reward(action, user_data):
    if not FEATURES["smart_rewards"]:
        return 0, "🌱"
    rewards = {
        "smart_search": {"points": 5, "emoji": "🧠"},
        "daily_visit": {"points": 5, "emoji": "🌅"},
        "feedback": {"points": 5, "emoji": "⭐"},
        "hadith_read": {"points": 2, "emoji": "🕊️"},
        "instant_quran": {"points": 2, "emoji": "✨"},
        "streak_bonus": {"points": 15, "emoji": "🔥"},
        "feedback_high_score": {"points": 10, "emoji": "💎"},
        "quest_complete": {"points": 5, "emoji": "🎯"},
        "referral_bonus": {"points": 10, "emoji": "🤝"},
        "mahdi_salawat_5": {"points": 3, "emoji": "🕊️"},
        "mahdi_salawat_14": {"points": 5, "emoji": "🕊️"},
        "mahdi_salawat_72": {"points": 10, "emoji": "🕊️"},
        "mahdi_gift": {"points": 3, "emoji": "🎁"},
        "mahdi_help": {"points": 5, "emoji": "🤝"},
        "mahdi_dua": {"points": 3, "emoji": "🤲"},
        "mahdi_thought": {"points": 2, "emoji": "💭"}
    }
    reward = rewards.get(action, {"points": 1, "emoji": "🌸"})
    points = reward["points"]
    emoji = reward["emoji"]
    if user_data.get("streak", 0) >= 7:
        points += 5
        emoji = "🔥"
    return points, emoji

def update_user_score(chat_id, action, user_data):
    points, emoji = calculate_reward(action, user_data)
    if points > 0:
        update_user(chat_id, score=points)
        today = datetime.now().date().isoformat()
        last_visit = user_data.get("last_visit_date", "")
        if last_visit != today:
            if last_visit and (datetime.now().date() - datetime.strptime(last_visit, "%Y-%m-%d").date()).days == 1:
                update_user(chat_id, streak=1)
            else:
                update_user(chat_id, streak_set=0)
            update_user(chat_id, daily_visit_count=1, total_visits=1)
            update_user(chat_id, last_visit_date=today)
        else:
            update_user(chat_id, daily_visit_count=1)
    check_achievements(chat_id, action, user_data)
    return points, emoji

def get_user_title(score):
    if not FEATURES["user_titles"]:
        return "🌱 کاربر قرآنی"
    titles = sorted(USER_TITLES.items(), reverse=True)
    for threshold, title in titles:
        if score >= threshold:
            return title
    return "🌱 کاربر قرآنی"

def get_user_title_description(title):
    return USER_TITLE_DESCRIPTIONS.get(title, "در مسیر رشد قرآنی قدم بردار!")

def check_achievements(chat_id, action, user_data):
    if not FEATURES["achievement_system"]:
        return
    achievements = []
    score = user_data.get("score", 0)
    streak = user_data.get("streak", 0)
    feedback_score = user_data.get("feedback_score", 0)
    search_count = user_data.get("search_count", 0)
    referral_count = user_data.get("referral_count", 0)
    
    if action in ["quran_search", "smart_search"] and search_count >= 1:
        achievements.append("first_search")
    if action == "daily_visit" and user_data.get("daily_visit_count", 0) >= 1:
        achievements.append("daily_visitor")
    if action == "feedback" and feedback_score >= 10:
        achievements.append("feedback_master")
    if action in ["quran_search", "smart_search"] and score >= 50:
        achievements.append("quran_lover")
    if action == "hadith_read":
        achievements.append("hadith_reader")
    if streak >= 7:
        achievements.append("streak_7")
    if streak >= 30:
        achievements.append("streak_30")
    if score >= 100:
        achievements.append("score_100")
    if score >= 500:
        achievements.append("score_500")
    if referral_count >= 5:
        achievements.append("referrer_bronze")
    if referral_count >= 10:
        achievements.append("referrer_silver")
    if referral_count >= 20:
        achievements.append("referrer_gold")
    if action == "smart_search":
        achievements.append("knowledge_seeker")
    
    if action.startswith("mahdi_"):
        achievements.append(action)
    
    for achievement_key in achievements:
        try:
            conn = db_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_key, unlocked_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (chat_id, achievement_key))
            conn.commit()
            conn.close()
            logger.info(f"دستاورد جدید: {achievement_key}")
        except Exception as e:
            logger.error(f"خطا در ثبت دستاورد: {e}")

def get_user_achievements(chat_id):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT achievement_key, unlocked_at FROM user_achievements WHERE user_id = ? ORDER BY unlocked_at DESC", (chat_id,))
        rows = cur.fetchall()
        conn.close()
        results = []
        for row in rows:
            achievement = ACHIEVEMENTS.get(row[0])
            if achievement:
                results.append({"name": achievement["name"], "points": achievement["points"], "unlocked_at": row[1]})
        return results
    except Exception as e:
        logger.error(f"خطا در دریافت دستاوردها: {e}")
        return []

# =========================================================
# ۱۹. سیستم کوئست‌های روزانه
# =========================================================
def complete_quest(chat_id, quest_id, user_data):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM user_quests WHERE user_id = ? AND quest_id = ? AND completed_at > datetime('now', '-1 day')", (chat_id, quest_id))
        existing = cur.fetchone()
        if existing:
            conn.close()
            return False, "قبلاً این کوئست را امروز انجام داده‌اید! 🌸"
        cur.execute("INSERT INTO user_quests (user_id, quest_id, completed_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (chat_id, quest_id))
        conn.commit()
        conn.close()
        quest = next((q for q in QUEST_ACTIONS if q["id"] == quest_id), None)
        if quest:
            update_user(chat_id, score=quest["points"], total_quests_completed=1)
            update_user(chat_id, last_quest_date=datetime.now().date().isoformat())
            return True, f"🎯 کوئست «{quest['label']}» انجام شد!\n🌟 {quest['points']} امتیاز دریافت کردی!"
        return True, "🎯 کوئست انجام شد! 🌟"
    except Exception as e:
        logger.error(f"خطا در انجام کوئست: {e}")
        return False, "⚠️ خطا در انجام کوئست."

def get_quests_status(chat_id):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT quest_id FROM user_quests WHERE user_id = ? AND completed_at > datetime('now', '-1 day')", (chat_id,))
        completed = [row[0] for row in cur.fetchall()]
        conn.close()
        status = []
        for quest in QUEST_ACTIONS:
            is_completed = quest["id"] in completed
            status.append({"id": quest["id"], "label": quest["label"], "points": quest["points"], "desc": quest["desc"], "completed": is_completed})
        return status
    except Exception as e:
        logger.error(f"خطا در دریافت وضعیت کوئست‌ها: {e}")
        return []

# =========================================================
# ۲۰. سیستم بهترین کاربر روز و هفته
# =========================================================
def get_best_user_real(period_type):
    try:
        conn = db_conn()
        cur = conn.cursor()
        if period_type == "daily":
            cur.execute("SELECT chat_id, name, score FROM users WHERE last_active > datetime('now', '-1 day') ORDER BY score DESC LIMIT 1")
        else:
            cur.execute("SELECT chat_id, name, score FROM users WHERE last_active > datetime('now', '-7 days') ORDER BY score DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            return {"user_id": row[0], "user_name": row[1] or "کاربر ناشناس", "score": row[2] or 0, "date": datetime.now().date().isoformat()}
        return None
    except Exception as e:
        logger.error(f"خطا در دریافت بهترین کاربر: {e}")
        return None

def save_best_user_real(period_type):
    try:
        conn = db_conn()
        cur = conn.cursor()
        if period_type == "daily":
            cur.execute("SELECT chat_id, name, score FROM users WHERE last_active > datetime('now', '-1 day') ORDER BY score DESC LIMIT 1")
        else:
            cur.execute("SELECT chat_id, name, score FROM users WHERE last_active > datetime('now', '-7 days') ORDER BY score DESC LIMIT 1")
        user = cur.fetchone()
        if user:
            chat_id, name, score = user
            period_date = datetime.now().date().isoformat()
            cur.execute("INSERT INTO best_users (user_id, user_name, score, period_type, period_date, created_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (chat_id, name, score, period_type, period_date))
            conn.commit()
            if period_type == "daily":
                message = f"""🏅 <b>بهترین کاربر روز</b>\n🌟 کاربر: {name}\n🏆 امتیاز: {score}\n📅 تاریخ: {period_date}\n💚 تبریک به این عزیز! 🌸"""
            else:
                message = f"""🏆 <b>بهترین کاربر هفته</b>\n🌟 کاربر: {name}\n🏆 امتیاز: {score}\n📅 هفته: {period_date}\n💚 تبریک ویژه به این عزیز! 🌸"""
            send_message(CHANNEL_ID, message)
            logger.info(f"بهترین کاربر {period_type} ذخیره شد: {name}")
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره بهترین کاربر: {e}")

def schedule_best_users():
    while True:
        try:
            now = datetime.now()
            if now.hour == 23 and now.minute == 59 and FEATURES["best_user_daily"]:
                save_best_user_real("daily")
                time.sleep(60)
            if now.weekday() == 4 and now.hour == 23 and now.minute == 59 and FEATURES["best_user_weekly"]:
                save_best_user_real("weekly")
                time.sleep(60)
            time.sleep(30)
        except Exception as e:
            logger.error(f"خطا در برنامه‌ریزی بهترین کاربران: {e}")
            time.sleep(60)

# =========================================================
# ۲۱. سیستم ارسال روزانه سه‌گانه (قرآن + صحیفه + نهج‌البلاغه)
# =========================================================
def get_next_item(book_name, data_list):
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

def format_daily_message(item, book_type, lang="fa"):
    if book_type == "quran":
        title = safe_text(lang, "daily_quran_title")
        text = f"""📘 <b>{title}</b>
        
<b>{item['surah']} (آیه {item['verse']})</b>
📝 {item['text']}

✨ <b>ترجمه:</b>
{item['trans']}

💡 <b>تفسیر:</b>
{item.get('interpretation', 'تفسیر ثبت نشده')}

🏷️ <b>موضوعات:</b>
{', '.join(item.get('topics', ['عمومی']))}
"""
        if lang != "fa":
            en_text = f"""
━━━━━━━━━━━━━━━━━━━
📖 <b>English Translation:</b>
{item.get('trans', '')}
"""
            text += en_text
        return text
    
    elif book_type == "sahifeh":
        title = safe_text(lang, "daily_sahifeh_title")
        text = f"""🤲 <b>{title}</b>

<b>{item['title']} (دعای {item['dua']})</b>
📝 {item['text']}

✨ <b>ترجمه:</b>
{item['trans']}

💡 <b>تفسیر:</b>
{item.get('interpretation', 'تفسیر ثبت نشده')}

🏷️ <b>موضوعات:</b>
{', '.join(item.get('topics', ['عمومی']))}
"""
        if lang != "fa":
            en_text = f"""
━━━━━━━━━━━━━━━━━━━
📖 <b>English Translation:</b>
{item.get('trans', '')}
"""
            text += en_text
        return text
    
    elif book_type == "nahj":
        title = safe_text(lang, "daily_nahj_title")
        text = f"""📜 <b>{title}</b>

<b>{item['type']} {item['number']}</b>
📝 {item['text']}

✨ <b>ترجمه:</b>
{item['trans']}

💡 <b>تفسیر:</b>
{item.get('interpretation', 'تفسیر ثبت نشده')}

🏷️ <b>موضوعات:</b>
{', '.join(item.get('topics', ['عمومی']))}
"""
        if lang != "fa":
            en_text = f"""
━━━━━━━━━━━━━━━━━━━
📖 <b>English Translation:</b>
{item.get('trans', '')}
"""
            text += en_text
        return text
    
    return "⚠️ خطا در فرمت‌سازی پیام."

def send_daily_posts():
    try:
        if not FEATURES["daily_posts"]:
            return
        now = datetime.now()
        scheduled_times = [(8, 0, "صبح 🌅"), (12, 0, "ظهر ☀️"), (18, 0, "عصر 🌇")]
        
        for hour, minute, time_name in scheduled_times:
            if now.hour == hour and 0 <= now.minute <= 2:
                if now.minute != 0:
                    time.sleep(1)
                    continue
                
                if hour == 8:
                    book_type = "quran"
                    data_list = QURAN_DATA
                    book_name = "quran"
                elif hour == 12:
                    book_type = "sahifeh"
                    data_list = SAHIFEH_DATA
                    book_name = "sahifeh"
                else:
                    book_type = "nahj"
                    data_list = NAHJ_DATA
                    book_name = "nahj"
                
                item, new_idx = get_next_item(book_name, data_list)
                if not item:
                    logger.warning(f"⚠️ داده‌ای برای {book_name} یافت نشد.")
                    break
                
                msg = format_daily_message(item, book_type, "fa")
                persian_date = get_persian_date()
                msg = f"🌟 <b>کانون قرآن و عترت</b>\n📅 {persian_date}\n\n{msg}"
                
                send_message(CHANNEL_ID, msg)
                set_publish_index(book_name, new_idx)
                save_sent_message(f"daily_{book_name}", msg[:500], CHANNEL_ID)
                logger.info(f"✅ پیام {book_name} در {time_name} ارسال شد. ایندکس جدید: {new_idx}")
                
                try:
                    conn = db_conn()
                    cur = conn.cursor()
                    cur.execute("SELECT chat_id, name, lang FROM users WHERE receive_daily = 1")
                    users = cur.fetchall()
                    conn.close()
                    
                    sent_count = 0
                    for user in users:
                        try:
                            user_lang = user[2] if user[2] in ["fa", "en", "ar"] else "fa"
                            user_msg = format_daily_message(item, book_type, user_lang)
                            user_msg = f"🌟 <b>کانون قرآن و عترت</b>\n📅 {get_persian_date() if user_lang == 'fa' else datetime.now().strftime('%Y-%m-%d')}\n\n{user_msg}"
                            send_message(user[0], user_msg)
                            sent_count += 1
                            time.sleep(0.1)
                            if sent_count % 10 == 0:
                                time.sleep(0.5)
                        except Exception as e:
                            logger.error(f"خطا در ارسال به {user[0]}: {e}")
                    logger.info(f"📨 پیام {book_name} به {sent_count} کاربر ارسال شد - {time_name}")
                except Exception as e:
                    logger.error(f"خطا در دریافت کاربران: {e}")
                
                time.sleep(60)
                break
                
        time.sleep(10)
    except Exception as e:
        logger.error(f"خطا در ارسال روزانه: {e}")

def next_item(book_name, data_list):
    return get_next_item(book_name, data_list)

# =========================================================
# ۲۲. گزارش هفتگی
# =========================================================
def send_weekly_report():
    if not FEATURES["weekly_report"]:
        return
    try:
        now = datetime.now()
        if now.weekday() != 6:
            return
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-7 days')")
        active_users = cur.fetchone()[0]
        cur.execute("SELECT SUM(search_count) FROM users WHERE last_active > datetime('now', '-7 days')")
        searches = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM feedbacks WHERE created_at > datetime('now', '-7 days')")
        feedbacks = cur.fetchone()[0]
        cur.execute("SELECT name, score FROM users ORDER BY score DESC LIMIT 1")
        best_user = cur.fetchone()
        quran_idx, _ = get_publish_index("quran")
        sahifeh_idx, _ = get_publish_index("sahifeh")
        nahj_idx, _ = get_publish_index("nahj")
        conn.close()
        report = f"""📊 <b>گزارش هفتگی ربات</b>\n{'='*50}\n📅 {get_persian_date()}\n👥 <b>آمار کاربران:</b>\n• کل کاربران: {total_users}\n• کاربران فعال این هفته: {active_users}\n📊 <b>آمار فعالیت:</b>\n• جستجوها: {searches}\n• بازخوردها: {feedbacks}\n📚 <b>وضعیت کتاب‌ها:</b>\n• قرآن: {quran_idx}/{len(QURAN_DATA)}\n• صحیفه: {sahifeh_idx}/{len(SAHIFEH_DATA)}\n• نهج‌البلاغه: {nahj_idx}/{len(NAHJ_DATA)}\n🏆 <b>بهترین کاربر هفته:</b>\n• {best_user[0] if best_user else 'نامشخص'} با {best_user[1] if best_user else 0} امتیاز\n💪 به راه خود ادامه دهید! 🚀"""
        send_message(ADMIN_ID, report)
        logger.info("📊 گزارش هفتگی ارسال شد.")
    except Exception as e:
        logger.error(f"خطا در گزارش هفتگی: {e}")

def weekly_report_scheduler():
    while True:
        try:
            time.sleep(3600)
            send_weekly_report()
        except Exception as e:
            logger.error(f"خطا در اسکجولر گزارش: {e}")
            time.sleep(3600)

# =========================================================
# ۲۳. سیستم پیام‌های انگیزشی
# =========================================================
def send_motivational_messages():
    if not FEATURES["motivational_messages"]:
        return
    try:
        now = datetime.now()
        if now.hour == 7 and now.minute == 0:
            motivational_messages = [
                "🌸 هر روز با قرآن، هر روز با نور!",
                "💚 با یاد خدا، دلها آرام می‌گیرد.",
                "🌟 تو می‌توانی! به خدا توکل کن.",
                "🌺 قرآن را بخوان، که بهار دل‌هاست.",
                "🍃 صبر کن، که خداوند با صابران است.",
                "🕊️ در سختی‌ها، یاد خدا باش.",
                "🌙 ماه رمضان، فرصت طلایی برای خودسازی.",
                "💪 با ایمان و تلاش، به قله‌های موفقیت برسی.",
                "🌹 هر روز یک شروع جدید است.",
                "✨ به امید خدا، همه چیز ممکن است.",
            ]
            msg = random.choice(motivational_messages)
            send_message(CHANNEL_ID, f"🌅 {msg}\n\n🌟 روزت پر از نور و آرامش! 🌸")
            logger.info("پیام انگیزشی صبحگاهی ارسال شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال پیام انگیزشی: {e}")

def motivational_scheduler():
    while True:
        try:
            send_motivational_messages()
            time.sleep(60)
        except Exception as e:
            logger.error(f"خطا در اسکجولر پیام‌های انگیزشی: {e}")
            time.sleep(60)

# =========================================================
# ۲۴. سیستم یادآوری مناسبت‌های مذهبی
# =========================================================
RELIGIOUS_OCCASIONS = {
    "نیمه شعبان": {"month": 8, "day": 15, "title": "🎉 ولادت امام زمان (عج)", "message": "🌹 ولادت با سعادت منجی عالم بشریت، امام زمان (عج) مبارک باد!"},
    "ماه رمضان": {"month": 9, "day": 1, "title": "🌙 حلول ماه رمضان", "message": "🌙 ماه رمضان، ماه رحمت و مغفرت مبارک باد!"},
    "عید فطر": {"month": 10, "day": 1, "title": "🎊 عید سعید فطر", "message": "🎊 عید سعید فطر، روز پاداش روزه‌داران مبارک باد!"},
    "عید قربان": {"month": 12, "day": 10, "title": "🎊 عید سعید قربان", "message": "🎊 عید سعید قربان، روز بندگی و ایثار مبارک باد!"},
    "محرم": {"month": 1, "day": 1, "title": "🖤 ماه محرم", "message": "🖤 ماه محرم، ماه عزاداری سالار شهیدان بر شما تسلیت باد."},
    "عاشورا": {"month": 1, "day": 10, "title": "🖤 تاسوعا و عاشورا", "message": "🖤 تاسوعا و عاشورا، یادآور حماسه کربلا بر شما تسلیت باد."},
}

def check_religious_occasions():
    if not FEATURES["religious_reminders"]:
        return
    try:
        now = datetime.now()
        today = (now.month, now.day)
        for name, data in RELIGIOUS_OCCASIONS.items():
            if (data["month"], data["day"]) == today:
                message = f"""🕌 <b>{data['title']}</b>\n{data['message']}\n💚 این مناسبت را گرامی بداریم."""
                send_message(CHANNEL_ID, message)
                send_message(ADMIN_ID, f"📢 مناسبت مذهبی امروز:\n{data['title']}\n{data['message']}")
                logger.info(f"یادآوری مناسبت مذهبی ارسال شد: {name}")
                break
    except Exception as e:
        logger.error(f"خطا در بررسی مناسبت‌های مذهبی: {e}")

def religious_reminder_scheduler():
    while True:
        try:
            check_religious_occasions()
            time.sleep(3600)
        except Exception as e:
            logger.error(f"خطا در اسکجولر مناسبت‌های مذهبی: {e}")
            time.sleep(3600)

# =========================================================
# ۲۵. مدیریت دیتابیس
# =========================================================
def db_conn():
    try:
        return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    except Exception as e:
        logger.error(f"خطا در اتصال به دیتابیس: {e}")
        raise

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
            state TEXT DEFAULT 'none',
            total_visits INTEGER DEFAULT 0,
            achievements TEXT DEFAULT '',
            last_visit_date TEXT DEFAULT '',
            daily_visit_count INTEGER DEFAULT 0,
            total_quests_completed INTEGER DEFAULT 0,
            last_quest_date TEXT DEFAULT '',
            referral_code TEXT UNIQUE,
            referred_by INTEGER DEFAULT NULL,
            referral_count INTEGER DEFAULT 0,
            referral_earned INTEGER DEFAULT 0,
            profile_image TEXT DEFAULT '',
            bio TEXT DEFAULT ''
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
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            type TEXT,
            content TEXT,
            score INTEGER DEFAULT 0,
            created_at TEXT,
            status TEXT DEFAULT 'pending',
            category TEXT DEFAULT 'general',
            is_read INTEGER DEFAULT 0
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            achievement_key TEXT,
            unlocked_at TEXT,
            UNIQUE(user_id, achievement_key)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reminder_text TEXT,
            remind_at TEXT,
            is_done INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            total_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            searches_count INTEGER DEFAULT 0,
            feedbacks_count INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS best_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            score INTEGER DEFAULT 0,
            period_type TEXT,
            period_date TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quest_id TEXT,
            completed_at TEXT,
            UNIQUE(user_id, quest_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            referral_code TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            category TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mahdi_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_id TEXT,
            completed_at TEXT,
            UNIQUE(user_id, action_id)
        )
    """)
    for book in ["quran", "nahj", "sahifeh"]:
        cur.execute("INSERT OR IGNORE INTO publish_state (book_name, last_index) VALUES (?, 0)", (book,))
    conn.commit()
    conn.close()
    logger.info("🗄️ دیتابیس راه‌اندازی شد.")

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))

def get_user(chat_id):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT name, lang, score, search_count, streak, feedback_score, 
                   last_active, join_date, receive_daily, state, total_visits, 
                   achievements, last_visit_date, daily_visit_count,
                   total_quests_completed, last_quest_date,
                   referral_code, referred_by, referral_count, referral_earned,
                   profile_image, bio
            FROM users WHERE chat_id = ?
        """, (chat_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "name": row[0] or "",
                "lang": row[1] if row[1] in ["fa", "en", "ar"] else "fa",
                "score": row[2] or 0,
                "search_count": row[3] or 0,
                "streak": row[4] or 0,
                "feedback_score": row[5] or 0,
                "last_active": row[6] or "",
                "join_date": row[7] or "",
                "receive_daily": row[8] or 0,
                "state": row[9] or "none",
                "total_visits": row[10] or 0,
                "achievements": row[11] or "",
                "last_visit_date": row[12] or "",
                "daily_visit_count": row[13] or 0,
                "total_quests_completed": row[14] or 0,
                "last_quest_date": row[15] or "",
                "referral_code": row[16] or "",
                "referred_by": row[17] or 0,
                "referral_count": row[18] or 0,
                "referral_earned": row[19] or 0,
                "profile_image": row[20] or "",
                "bio": row[21] or ""
            }
    except Exception as e:
        logger.error(f"خطا در دریافت کاربر {chat_id}: {e}")
    return {"name": "", "lang": "fa", "score": 0, "search_count": 0, "streak": 0, "feedback_score": 0, "last_active": "", "join_date": "", "receive_daily": 0, "state": "none", "total_visits": 0, "achievements": "", "last_visit_date": "", "daily_visit_count": 0, "total_quests_completed": 0, "last_quest_date": "", "referral_code": "", "referred_by": 0, "referral_count": 0, "referral_earned": 0, "profile_image": "", "bio": ""}

def ensure_user(chat_id, name="", referred_by=None):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        if cur.fetchone():
            conn.close()
            return
        referral_code = generate_referral_code()
        cur.execute("""
            INSERT INTO users (chat_id, name, lang, join_date, last_active, 
                             total_visits, referral_code, referred_by)
            VALUES (?, ?, 'fa', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, ?, ?)
        """, (chat_id, name, referral_code, referred_by or 0))
        if referred_by and FEATURES["referral_system"]:
            cur.execute("UPDATE users SET score = score + 10 WHERE chat_id = ?", (chat_id,))
            cur.execute("""
                UPDATE users 
                SET score = score + 10, referral_count = referral_count + 1,
                    referral_earned = referral_earned + 10
                WHERE chat_id = ?
            """, (referred_by,))
            cur.execute("""
                INSERT INTO referrals (referrer_id, referred_id, referral_code, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (referred_by, chat_id, referral_code))
            try:
                referrer = get_user(referred_by)
                if referrer:
                    send_message_with_retry(referred_by, f"""🎉 <b>تبریک! شما یک دعوت جدید دارید!</b>\n🌸 کاربر جدید با کد دعوت شما عضو شد: {name}\n🌟 ۱۰ امتیاز به حساب شما اضافه شد!""")
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به دعوت‌کننده: {e}")
        conn.commit()
        conn.close()
        logger.info(f"کاربر جدید ثبت شد: {chat_id} ({name})")
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر {chat_id}: {e}")

def update_user(chat_id, **kwargs):
    try:
        conn = db_conn()
        cur = conn.cursor()
        if "lang" in kwargs and kwargs["lang"] not in ["fa", "en", "ar"]:
            kwargs["lang"] = "fa"
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ["name", "lang", "state", "achievements", "last_quest_date", "referral_code", "profile_image", "bio"]:
                fields.append(f"{key} = ?")
                values.append(value)
            elif key in ["score", "search_count", "streak", "feedback_score", "receive_daily", "total_visits", "daily_visit_count", "total_quests_completed", "referral_count", "referral_earned"]:
                fields.append(f"{key} = {key} + ?")
                values.append(value)
            elif key in ["score_set", "search_count_set", "streak_set", "referral_count_set", "referral_earned_set"]:
                actual_key = key.replace("_set", "")
                fields.append(f"{actual_key} = ?")
                values.append(value)
        fields.append("last_active = CURRENT_TIMESTAMP")
        if fields:
            query = f"UPDATE users SET {', '.join(fields)} WHERE chat_id = ?"
            values.append(chat_id)
            cur.execute(query, values)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی کاربر {chat_id}: {e}")

def get_publish_index(book_name):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT last_index, last_publish_date FROM publish_state WHERE book_name = ?", (book_name,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0, row[1] if row and row[1] else ""
    except Exception as e:
        logger.error(f"خطا در دریافت وضعیت انتشار {book_name}: {e}")
        return 0, ""

def set_publish_index(book_name, index_value):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("UPDATE publish_state SET last_index = ?, last_publish_date = CURRENT_TIMESTAMP WHERE book_name = ?", (index_value, book_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در تنظیم وضعیت انتشار {book_name}: {e}")

def get_leaderboard(limit=10):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT name, score, total_visits, streak, referral_count 
            FROM users 
            WHERE score > 0 AND total_visits > 0
            ORDER BY score DESC, total_visits DESC 
            LIMIT ?
        """, (limit,))
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
        logger.error(f"خطا در دریافت رتبه کاربر {chat_id}: {e}")
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

def get_active_users(days=7):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT chat_id) FROM users WHERE last_active > datetime('now', '-{} days')".format(days))
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"خطا در دریافت کاربران فعال: {e}")
        return 0

def log_error(error_type, error_message, traceback_str, user_id=None):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO error_logs (error_type, error_message, traceback, user_id, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)", (error_type, error_message[:500], traceback_str[:500], user_id))
        conn.commit()
        conn.close()
    except:
        pass

def save_sent_message(message_type, content, sent_to):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO sent_messages (message_type, content, sent_to, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (message_type, content[:500], sent_to))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره پیام ارسالی: {e}")

def update_daily_stats():
    try:
        today = datetime.now().date().isoformat()
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO daily_stats (date, total_users, active_users, searches_count, feedbacks_count)
            VALUES (?, 
                (SELECT COUNT(*) FROM users),
                (SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-1 day')),
                (SELECT SUM(search_count) FROM users),
                (SELECT COUNT(*) FROM feedbacks WHERE created_at > datetime('now', '-1 day'))
            )
        """, (today,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی آمار روزانه: {e}")

# =========================================================
# ۲۶. ابزارهای ارسال پیام به بله
# =========================================================
def send_bale(method, data, retry_count=3):
    if not TOKEN:
        return {"ok": False, "error": "TOKEN not set"}
    url = f"{BASE_URL}/{method}"
    for attempt in range(retry_count):
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"BALE API status {response.status_code}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"BALE API ERROR: {e}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
    return {"ok": False, "error": "Max retries exceeded"}

def answer_callback(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    return send_bale("answerCallbackQuery", payload)

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    if not text:
        return None
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            send_message(chat_id, part, reply_markup if i == 0 else None, parse_mode)
        return {"ok": True}
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
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

def send_chat_action(chat_id, action="typing"):
    return send_bale("sendChatAction", {"chat_id": chat_id, "action": action})

# =========================================================
# ۲۷. هوش مصنوعی OpenRouter
# =========================================================
def ask_ai(question, lang):
    if not FEATURES["deepseek_ai"]:
        return "🔧 ویژگی هوش مصنوعی در حال حاضر غیرفعال است."
    
    if not OPENROUTER_KEY or len(OPENROUTER_KEY) < 10:
        logger.error("❌ کلید OpenRouter تنظیم نشده است!")
        return "🔑 کلید API تنظیم نشده است. لطفاً با ادمین تماس بگیرید."
    
    current_time = time.time()
    chat_id = int(time.time()) % 10000
    
    if chat_id in RATE_LIMIT_COUNTER:
        if current_time - RATE_LIMIT_TIME.get(chat_id, 0) < 60:
            RATE_LIMIT_COUNTER[chat_id] = RATE_LIMIT_COUNTER.get(chat_id, 0) + 1
            if RATE_LIMIT_COUNTER[chat_id] > 5:
                return "⏳ تعداد درخواست‌ها زیاد شده است. چند لحظه صبر کنید."
        else:
            RATE_LIMIT_COUNTER[chat_id] = 1
            RATE_LIMIT_TIME[chat_id] = current_time
    else:
        RATE_LIMIT_COUNTER[chat_id] = 1
        RATE_LIMIT_TIME[chat_id] = current_time
    
    language_name = {"fa": "Persian", "en": "English", "ar": "Arabic"}.get(lang, "Persian")
    
    system_prompt = f"""You are a warm, respectful Islamic assistant for a Quranic student bot. 
Reply in {language_name}. Keep answers:
- Useful and practical
- Friendly and encouraging
- Well-formatted with emojis
- Focused on Islamic teachings (Quran, Hadith, Dua)
- Relevant for medical students and professionals
Always mention Quranic verses or Hadith when appropriate."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    conversation_key = f"conv_{chat_id}"
    if conversation_key not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[conversation_key] = []
    for msg in CONVERSATION_HISTORY[conversation_key][-5:]:
        messages.append(msg)
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/labbayk_quranbot",
        "X-Title": "Quran Bot"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
        "stream": False
    }
    
    try:
        res = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=45
        )
        
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and data["choices"]:
                answer = data["choices"][0]["message"]["content"]
                CONVERSATION_HISTORY[conversation_key].append({"role": "user", "content": question})
                CONVERSATION_HISTORY[conversation_key].append({"role": "assistant", "content": answer})
                return answer
        
        elif res.status_code == 401:
            logger.error("❌ خطای احراز هویت OpenRouter: کلید API نامعتبر است")
            return "🔑 کلید API نامعتبر است. لطفاً با ادمین تماس بگیرید."
        
        elif res.status_code == 402:
            logger.error("❌ خطای موجودی OpenRouter: اعتبار کافی نیست")
            return "💳 اعتبار حساب تمام شده است. لطفاً با ادمین تماس بگیرید."
        
        elif res.status_code == 429:
            return "⏳ تعداد درخواست‌ها محدود شده است. چند لحظه دیگر تلاش کنید."
        
        elif res.status_code == 500:
            return "⚠️ سرور هوش مصنوعی با مشکل مواجه شده است. دوباره تلاش کنید."
        
        else:
            logger.error(f"❌ خطای OpenRouter: {res.status_code} - {res.text[:200]}")
            return f"⚠️ خطا در ارتباط با هوش مصنوعی (کد {res.status_code})."
    
    except requests.exceptions.Timeout:
        return "⏳ زمان پاسخ‌دهی هوش مصنوعی به پایان رسید. دوباره تلاش کنید."
    
    except requests.exceptions.ConnectionError:
        return "⚠️ خطا در ارتباط با سرور هوش مصنوعی. اتصال اینترنت را بررسی کنید."
    
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره OpenRouter: {e}")
        return "⚠️ خطا در ارتباط با هوش مصنوعی. لطفاً دوباره تلاش کنید."

def ask_deepseek(question, lang):
    return ask_ai(question, lang)

# =========================================================
# ۲۸. کیبوردهای اینلاین (منوی حرفه‌ای با زیرشاخه)
# =========================================================
def lang_keyboard():
    return {"inline_keyboard": [[{"text": "🇮🇷 فارسی", "callback_data": "setlang_fa"}], [{"text": "🇬🇧 English", "callback_data": "setlang_en"}], [{"text": "🇸🇦 العربية", "callback_data": "setlang_ar"}]]}

def join_keyboard():
    channel_username = CHANNEL_ID.replace("@", "")
    return {"inline_keyboard": [[{"text": "📢 ورود به کانال", "url": f"https://ble.ir/{channel_username}"}], [{"text": "✅ تایید عضویت", "callback_data": "check_join"}]]}

def back_menu_keyboard(lang):
    text = safe_text(lang, "back_to_menu")
    return {"inline_keyboard": [[{"text": text, "callback_data": "back_main"}]]}

# =========================================================
# ۲۸-الف. منوی اصلی جدید (۶ دکمه با زیرشاخه)
# =========================================================
def main_menu(chat_id, lang):
    """منوی اصلی با ۶ دکمه و طراحی حرفه‌ای دانشجوپسند"""
    buttons = [
        [{"text": "📚 کتابخانه قرآن", "callback_data": "menu_library"}],
        [{"text": "🔍 جستجوی هوشمند", "callback_data": "menu_search"}],
        [{"text": "🤖 مشاوره هوش مصنوعی", "callback_data": "menu_ai"}],
        [{"text": "🏆 جام قرآنی", "callback_data": "menu_competitions"}],
        [{"text": "👤 پروفایل من", "callback_data": "menu_account"}],
        [{"text": "⚙️ خدمات بیشتر", "callback_data": "menu_more"}],
    ]
    if chat_id == ADMIN_ID and FEATURES["admin_panel"]:
        buttons.append([{"text": "🛠️ پنل مدیریت", "callback_data": "admin_panel"}])
    return {"inline_keyboard": buttons}

# =========================================================
# ۲۸-ب. زیرمنوها
# =========================================================
def library_submenu(lang):
    """زیرمنو: کتابخانه قرآن"""
    return {"inline_keyboard": [
        [{"text": "📖 قرآن کریم", "callback_data": "menu_quran"},
         {"text": "📜 نهج‌البلاغه", "callback_data": "menu_nahj"},
         {"text": "🤲 صحیفه سجادیه", "callback_data": "menu_sahifeh"}],
        [{"text": "🕊️ احادیث روزانه", "callback_data": "menu_hadith"},
         {"text": "✨ قرآن در لحظه", "callback_data": "menu_instant_quran"},
         {"text": "📚 مقالات علمی", "callback_data": "menu_articles"}],
        [{"text": "🔔 دریافت روزانه", "callback_data": "menu_daily_toggle"},
         {"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

def search_submenu(lang):
    """زیرمنو: جستجوی هوشمند"""
    return {"inline_keyboard": [
        [{"text": "🧠 جستجوی جامع (همه منابع)", "callback_data": "menu_smart_search"}],
        [{"text": "📖 جستجو در قرآن", "callback_data": "menu_quran_search"},
         {"text": "🌐 جستجو در اینترنت", "callback_data": "menu_internet_search"}],
        [{"text": "📜 جستجو در نهج‌البلاغه", "callback_data": "menu_nahj_search"},
         {"text": "🤲 جستجو در صحیفه", "callback_data": "menu_sahifeh_search"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

def ai_submenu(lang):
    """زیرمنو: مشاوره هوش مصنوعی"""
    return {"inline_keyboard": [
        [{"text": "🤖 پرسش از هوش مصنوعی", "callback_data": "menu_ai_ask"}],
        [{"text": "📝 تفسیر موضوعی", "callback_data": "menu_ai_tafsir"}],
        [{"text": "🔮 پیشنهاد موضوعی", "callback_data": "menu_ai_suggest"},
         {"text": "📊 تحلیل آماری", "callback_data": "menu_ai_stats"}],
        [{"text": "🎯 تولید محتوای قرآنی", "callback_data": "menu_ai_content"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

def competitions_submenu(lang):
    """زیرمنو: جام قرآنی"""
    return {"inline_keyboard": [
        [{"text": "📊 لیگ قرآنی", "callback_data": "menu_league"},
         {"text": "🎯 کوئست‌های روزانه", "callback_data": "menu_quests"}],
        [{"text": "🏅 بهترین کاربران", "callback_data": "menu_best_users"},
         {"text": "📋 کارنامه من", "callback_data": "menu_scorecard"}],
        [{"text": "📈 روند پیشرفت", "callback_data": "menu_progress"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

def account_submenu(lang):
    """زیرمنو: پروفایل من"""
    return {"inline_keyboard": [
        [{"text": "📊 آمار پیشرفت", "callback_data": "menu_stats"},
         {"text": "❤️ آیات مورد علاقه", "callback_data": "menu_favorites"}],
        [{"text": "🏅 دستاوردهای من", "callback_data": "menu_achievements"},
         {"text": "✏️ ویرایش پروفایل", "callback_data": "menu_profile"}],
        [{"text": "📤 اشتراک‌گذاری", "callback_data": "menu_share"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

def more_submenu(lang):
    """زیرمنو: خدمات بیشتر"""
    return {"inline_keyboard": [
        [{"text": "📢 رویدادها و اخبار", "callback_data": "menu_events"},
         {"text": "🤝 شبکه اجتماعی", "callback_data": "menu_social"}],
        [{"text": "⏰ یادآوری‌ها", "callback_data": "menu_reminder"},
         {"text": "🕊️ مهدویت", "callback_data": "menu_mahdi"}],
        [{"text": "📝 پیشنهادات و انتقادات", "callback_data": "menu_feedback"},
         {"text": "🌍 تنظیمات زبان", "callback_data": "menu_change_lang"}],
        [{"text": "❓ راهنمای کاربری", "callback_data": "menu_help"},
         {"text": "ℹ️ درباره ربات", "callback_data": "menu_about"}],
        [{"text": "📨 تماس با ما", "callback_data": "menu_admin_msg"},
         {"text": "🔔 تنظیمات اعلان‌ها", "callback_data": "menu_daily_toggle"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

def mahdi_submenu(lang):
    """زیرمنو: مهدویت"""
    return {"inline_keyboard": [
        [{"text": "🕊️ ۵ صلوات (۳ امتیاز)", "callback_data": "mahdi_salawat_5"},
         {"text": "🕊️ ۱۴ صلوات (۵ امتیاز)", "callback_data": "mahdi_salawat_14"}],
        [{"text": "🕊️ ۷۲ صلوات (۱۰ امتیاز)", "callback_data": "mahdi_salawat_72"},
         {"text": "🎁 هدیه به امام زمان", "callback_data": "mahdi_gift"}],
        [{"text": "🤝 کمک به دیگران", "callback_data": "mahdi_help"},
         {"text": "🤲 دعا برای ظهور", "callback_data": "mahdi_dua"}],
        [{"text": "💭 تفکر درباره ظهور", "callback_data": "mahdi_thought"},
         {"text": "📊 آمار مهدوی من", "callback_data": "mahdi_stats"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

def admin_menu(chat_id, lang="fa"):
    """پنل مدیریت"""
    return {"inline_keyboard": [
        [{"text": "📊 آمار و گزارشات", "callback_data": "admin_stats"}],
        [{"text": "📩 مدیریت بازخوردها", "callback_data": "admin_feedbacks"}],
        [{"text": "📢 ارسال اطلاعیه همگانی", "callback_data": "admin_broadcast"}],
        [{"text": "👥 مدیریت کاربران", "callback_data": "admin_users"}],
        [{"text": "⚙️ تنظیمات پیشرفته", "callback_data": "admin_schedule"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}]
    ]}

# =========================================================
# ۲۸-ج. کیبوردهای قدیمی (سازگاری با نسخه‌های قبلی)
# =========================================================
def quest_keyboard(lang):
    return {"inline_keyboard": [
        [{"text": "🧠 جستجوی هوشمند (۵ امتیاز)", "callback_data": "quest_smart_search"}],
        [{"text": "🌅 بازدید روزانه (۵ امتیاز)", "callback_data": "quest_daily_visit"}],
        [{"text": "📝 ارسال پیشنهاد (۵ امتیاز)", "callback_data": "quest_feedback"}],
        [{"text": "🕊️ مطالعه حدیث (۲ امتیاز)", "callback_data": "quest_hadith"}],
        [{"text": "✨ قرآن در لحظه (۲ امتیاز)", "callback_data": "quest_instant_quran"}],
        [{"text": "🤝 دعوت از دوستان (۱۰ امتیاز)", "callback_data": "quest_referral"}],
        [{"text": "📊 مشاهده امتیازات", "callback_data": "show_quest_points"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]}

def best_users_keyboard(lang):
    return {"inline_keyboard": [
        [{"text": "🏅 بهترین کاربر روز", "callback_data": "show_best_daily"}],
        [{"text": "🏆 بهترین کاربر هفته", "callback_data": "show_best_weekly"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]}

def referral_keyboard(lang, referral_code):
    bot_username = BOT_USERNAME
    referral_link = f"https://ble.ir/{bot_username}?start=ref_{referral_code}"
    return {"inline_keyboard": [
        [{"text": "📤 اشتراک‌گذاری لینک", "url": f"https://ble.ir/share?url={referral_link}&text=🌸 به ربات بپیوند! 🎁"}],
        [{"text": "📋 کپی لینک", "callback_data": "copy_referral"}],
        [{"text": "📊 آمار دعوت‌ها", "callback_data": "referral_stats"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]}

def favorites_keyboard(lang, user_id):
    favorites = get_favorites(user_id)
    if not favorites:
        return back_menu_keyboard(lang)
    keyboard = []
    for i, fav in enumerate(favorites[:5]):
        keyboard.append([{"text": f"📖 {fav.get('surah', '')} - {fav.get('verse', '')}", "callback_data": f"show_fav_{i}"}])
    keyboard.append([{"text": "🗑️ حذف همه", "callback_data": "clear_favorites"}])
    keyboard.append([{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}])
    return {"inline_keyboard": keyboard}

def faq_keyboard(lang):
    return {"inline_keyboard": [
        [{"text": "❓ نحوه استفاده", "callback_data": "faq_usage"}],
        [{"text": "📖 جستجوی قرآن", "callback_data": "faq_search"}],
        [{"text": "🤖 هوش مصنوعی", "callback_data": "faq_ai"}],
        [{"text": "🏆 امتیازات", "callback_data": "faq_points"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]}

def profile_keyboard(lang):
    return {"inline_keyboard": [
        [{"text": "✏️ تغییر نام", "callback_data": "profile_name"}],
        [{"text": "📝 تغییر بیو", "callback_data": "profile_bio"}],
        [{"text": "📊 مشاهده پروفایل", "callback_data": "profile_view"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]}

def share_keyboard(lang):
    return {"inline_keyboard": [
        [{"text": "📤 اشتراک‌گذاری ربات", "switch_inline_query": "ربات قرآن و عترت"}],
        [{"text": "📋 کپی لینک", "callback_data": "copy_link"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]}

def reminder_keyboard(lang):
    return {"inline_keyboard": [
        [{"text": "🕐 یادآوری روزانه", "callback_data": "reminder_daily"}],
        [{"text": "🔔 یادآوری هفتگی", "callback_data": "reminder_weekly"}],
        [{"text": "📋 مشاهده یادآوری‌ها", "callback_data": "reminder_list"}],
        [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
    ]}

# =========================================================
# ۲۹. عضویت اجباری
# =========================================================
MEMBERSHIP_CACHE = {}
CACHE_DURATION = 300

def check_membership(chat_id):
    if not CHANNEL_ID or not FEATURES["force_join"]:
        return True
    cache_key = f"membership_{chat_id}"
    if cache_key in MEMBERSHIP_CACHE:
        result, timestamp = MEMBERSHIP_CACHE[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            return result
    try:
        result = send_bale("getChatMember", {"chat_id": CHANNEL_ID, "user_id": chat_id})
        if result and result.get("ok"):
            status = result.get("result", {}).get("status", "")
            is_member = status in ["member", "administrator", "creator"]
            MEMBERSHIP_CACHE[cache_key] = (is_member, time.time())
            return is_member
        return True
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت: {e}")
        return True

# =========================================================
# ۳۰. توابع کمکی
# =========================================================
def get_system_stats():
    stats = {"total_users": get_user_count(), "active_users_7d": get_active_users(7), "active_users_30d": get_active_users(30), "highest_score": get_highest_score(), "total_feedbacks": 0, "pending_feedbacks": 0, "quran_count": len(QURAN_DATA), "nahj_count": len(NAHJ_DATA), "sahifeh_count": len(SAHIFEH_DATA), "total_referrals": 0, "features_status": FEATURES}
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM feedbacks")
        stats["total_feedbacks"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM feedbacks WHERE status='pending'")
        stats["pending_feedbacks"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM user_quests")
        stats["total_quests"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM referrals")
        stats["total_referrals"] = cur.fetchone()[0]
        conn.close()
    except Exception as e:
        logger.error(f"خطا در دریافت آمار: {e}")
    return stats

def format_system_stats():
    stats = get_system_stats()
    return f"""💻 <b>وضعیت سیستم</b>\n{'='*50}\n📊 <b>آمار کلی:</b>\n👥 کل کاربران: {stats['total_users']}\n🟢 فعال (۷ روز): {stats['active_users_7d']}\n🟡 فعال (۳۰ روز): {stats['active_users_30d']}\n📖 آیات قرآن: {stats['quran_count']}\n📜 نهج‌البلاغه: {stats['nahj_count']}\n🤲 صحیفه سجادیه: {stats['sahifeh_count']}\n📩 بازخوردها: {stats['total_feedbacks']}\n⏳ در انتظار: {stats['pending_feedbacks']}\n🎯 کوئست‌ها: {stats.get('total_quests', 0)}\n🤝 دعوت‌ها: {stats.get('total_referrals', 0)}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"""

# =========================================================
# ۳۱. وب هوک و مدیریت یکپارچه درخواست‌ها
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
            
            if text and text.startswith("/start"):
                parts = text.split()
                if len(parts) > 1 and parts[1].startswith("ref_"):
                    referral_code = parts[1].replace("ref_", "")
                    try:
                        conn = db_conn()
                        cur = conn.cursor()
                        cur.execute("SELECT chat_id FROM users WHERE referral_code = ?", (referral_code,))
                        referrer = cur.fetchone()
                        conn.close()
                        if referrer and referrer[0] != chat_id:
                            ensure_user(chat_id, first_name, referrer[0])
                        else:
                            ensure_user(chat_id, first_name)
                    except Exception as e:
                        logger.error(f"خطا در پردازش کد دعوت: {e}")
                        ensure_user(chat_id, first_name)
                else:
                    ensure_user(chat_id, first_name)
            else:
                ensure_user(chat_id, first_name)
            
            update_user(chat_id, name=first_name)
            user = get_user(chat_id)
            lang = user["lang"]
            
            if text == "/start" or text == "شروع":
                update_user(chat_id, state="none")
                send_message(chat_id, safe_text(lang, "select_lang"), lang_keyboard())
                return "OK", 200
            
            if chat_id != ADMIN_ID:
                try:
                    if not check_membership(chat_id):
                        send_message(chat_id, safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID), join_keyboard())
                        return "OK", 200
                except Exception as e:
                    logger.error(f"خطا در بررسی عضویت: {e}")
            
            try:
                handled = handle_state_message(chat_id, text, user)
                if handled:
                    return "OK", 200
            except Exception as e:
                logger.error(f"خطا در پردازش وضعیت: {e}")
                send_message(chat_id, "⚠️ یه خطای کوچیک رخ داد! 😅\nلطفاً دوباره تلاش کن.")
                update_user(chat_id, state="none")
                return "OK", 200
            
            # پیام خوش‌آمدگویی جدید
            title = get_user_title(user.get("score", 0))
            greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
            
            if lang == "fa":
                welcome_text = f"""
🌟 <b>به خانواده بزرگ کانون قرآن و عترت خوش آمدی!</b>
{greeting}

👋 <b>سلام</b> {first_name} عزیز!

👑 <b>عنوان شما:</b> {title}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 <b>چهار گنج بی‌نظیر در یک ربات:</b>
📖 قرآن کریم | 📜 نهج‌البلاغه | 🤲 صحیفه سجادیه | 🕊️ احادیث

🤖 <b>همراه با هوش مصنوعی پیشرفته</b> برای پاسخگویی هوشمند

👨‍🎓 <b>مناسب برای:</b> دانشجویان، اساتید، پژوهشگران و همه علاقه‌مندان

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 <b>توصیه ما:</b> با دکمه «کتابخانه قرآن» شروع کنید.

👇 از منوی زیر انتخاب کنید:
"""
            else:
                welcome_text = safe_text(lang, "welcome", name=first_name)
            
            send_message(chat_id, welcome_text, main_menu(chat_id, lang))
            update_user_score(chat_id, "daily_visit", user)
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
                if chat_id != ADMIN_ID:
                    try:
                        if not check_membership(chat_id):
                            send_message(chat_id, safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID), join_keyboard())
                            return "OK", 200
                    except Exception as e:
                        logger.error(f"خطا در بررسی عضویت: {e}")
                greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
                title = get_user_title(user.get("score", 0))
                if lang == "fa":
                    welcome_text = f"{greeting}\n\n{first_name} جان! 😍\n\nبه ربات خوش آمدی.\n👑 عنوان: {title}\n\nاز منوی زیر استفاده کن:"
                else:
                    welcome_text = safe_text(lang, "welcome", name=first_name)
                send_message(chat_id, welcome_text, main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # تأیید عضویت
            # ===========================
            if cb_data == "check_join":
                try:
                    if check_membership(chat_id):
                        send_message(chat_id, safe_text(lang, "joined_success"), main_menu(chat_id, lang))
                    else:
                        send_message(chat_id, safe_text(lang, "not_joined_yet"), join_keyboard())
                except Exception as e:
                    logger.error(f"خطا در بررسی عضویت: {e}")
                    send_message(chat_id, "⚠️ خطا در بررسی عضویت.", join_keyboard())
                return "OK", 200
            
            # ===========================
            # بازگشت به منوی اصلی
            # ===========================
            if cb_data == "back_main":
                update_user(chat_id, state="none")
                greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
                title = get_user_title(user.get("score", 0))
                if lang == "fa":
                    send_message(chat_id, f"{greeting}\n\n{first_name} جان! 🍃\nخوش برگشتی! 🌸\n👑 عنوان: {title}", main_menu(chat_id, lang))
                else:
                    send_message(chat_id, f"{greeting}\n\n{safe_text(lang, 'back_to_menu')}", main_menu(chat_id, lang))
                return "OK", 200
            
            if chat_id != ADMIN_ID:
                try:
                    if not check_membership(chat_id):
                        send_message(chat_id, safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID), join_keyboard())
                        return "OK", 200
                except Exception as e:
                    logger.error(f"خطا در بررسی عضویت: {e}")
            
            # ===========================
            # منوی کتابخانه
            # ===========================
            if cb_data == "menu_library":
                send_message(chat_id, "📚 <b>کتابخانه قرآن</b>\n\nانتخاب کنید:", library_submenu(lang))
                return "OK", 200
            
            # ===========================
            # منوی جستجو
            # ===========================
            if cb_data == "menu_search":
                send_message(chat_id, "🔍 <b>جستجوی هوشمند</b>\n\nانتخاب کنید:", search_submenu(lang))
                return "OK", 200
            
            # ===========================
            # منوی هوش مصنوعی
            # ===========================
            if cb_data == "menu_ai":
                send_message(chat_id, "🤖 <b>مشاوره هوش مصنوعی</b>\n\nانتخاب کنید:", ai_submenu(lang))
                return "OK", 200
            
            # ===========================
            # منوی جام قرآنی
            # ===========================
            if cb_data == "menu_competitions":
                send_message(chat_id, "🏆 <b>جام قرآنی</b>\n\nانتخاب کنید:", competitions_submenu(lang))
                return "OK", 200
            
            # ===========================
            # منوی پروفایل
            # ===========================
            if cb_data == "menu_account":
                send_message(chat_id, "👤 <b>پروفایل من</b>\n\nانتخاب کنید:", account_submenu(lang))
                return "OK", 200
            
            # ===========================
            # منوی خدمات بیشتر
            # ===========================
            if cb_data == "menu_more":
                send_message(chat_id, "⚙️ <b>خدمات بیشتر</b>\n\nانتخاب کنید:", more_submenu(lang))
                return "OK", 200
            
            # ===========================
            # منوی مهدویت
            # ===========================
            if cb_data == "menu_mahdi":
                if not FEATURES["mahdi_section"]:
                    send_message(chat_id, "🔧 این بخش غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                try:
                    conn = db_conn()
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM mahdi_actions WHERE user_id = ? AND completed_at > datetime('now', '-1 day')", (chat_id,))
                    today_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM mahdi_actions WHERE user_id = ?", (chat_id,))
                    total_count = cur.fetchone()[0]
                    conn.close()
                except:
                    today_count = 0
                    total_count = 0
                
                msg = f"""🕊️ <b>بخش مهدویت</b>
🌟 {first_name} جان! امروز برای امام زمان (عج) چه می‌کنی؟

📊 آمار امروز شما:
• اقدامات امروز: {today_count} مورد
• کل اقدامات: {total_count} مورد

💡 با انجام هر یک از این کارها، علاوه بر امتیاز، به ظهور نزدیک‌تر می‌شوی:

• ۵ صلوات (۳ امتیاز) 🌹
• ۱۴ صلوات (۵ امتیاز) 🌹
• ۷۲ صلوات (۱۰ امتیاز) 🌹
• هدیه به امام زمان (۳ امتیاز) 🎁
• کمک به دیگران (۵ امتیاز) 🤝
• دعا برای ظهور (۳ امتیاز) 🤲
• تفکر درباره ظهور (۲ امتیاز) 💭

🌹 هر روز می‌توانی این کارها را انجام دهی.
🕊️ امام زمان (عج) منتظر اعمال خوب توست!"""
                send_message(chat_id, msg, mahdi_submenu(lang))
                return "OK", 200
            
            # ===========================
            # اقدامات مهدویت
            # ===========================
            if cb_data.startswith("mahdi_"):
                action_id = cb_data
                action_info = None
                for item in MAHDI_MESSAGES_DATA:
                    if item["id"] == action_id:
                        action_info = item
                        break
                
                if action_info:
                    try:
                        conn = db_conn()
                        cur = conn.cursor()
                        cur.execute("""
                            SELECT id FROM mahdi_actions 
                            WHERE user_id = ? AND action_id = ? 
                            AND completed_at > datetime('now', '-1 day')
                        """, (chat_id, action_id))
                        existing = cur.fetchone()
                        
                        if existing:
                            conn.close()
                            repeat_messages = [
                                "🌸 امروز قبلاً این کار را انجام داده‌ای!\n🌟 فردا دوباره امتحان کن!",
                                "🌹 امروز روح امام زمان (عج) از کارت خوشحال شد!\n💚 فردا هم منتظر اعمال خوب توست!",
                                "🕊️ امروز نور دیگری به دل امام زمان (عج) فرستادی!\n🌟 فردا دوباره بیا!"
                            ]
                            send_message(chat_id, f"✨ {random.choice(repeat_messages)}\n\n🕊️ {action_info['title']}", mahdi_submenu(lang))
                            return "OK", 200
                        
                        cur.execute("""
                            INSERT INTO mahdi_actions (user_id, action_id, completed_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        """, (chat_id, action_id))
                        conn.commit()
                        conn.close()
                        
                        points = action_info["points"]
                        update_user(chat_id, score=points)
                        update_user_score(chat_id, action_id, user)
                        
                        congrat_messages = [
                            f"🌹 {points} نور به قلب امام زمان (عج) فرستادی!",
                            f"✨ با این کار، {points} قدم به ظهور نزدیک‌تر شدی!",
                            f"🕊️ امروز {points} نوری بر دل امام زمان (عج) تاباندی!",
                            f"💚 {points} امتیاز برای نزدیکی به ظهور!",
                            f"🌟 {points} درجه در بهشت رضوان! 🌹"
                        ]
                        
                        msg = f"""🕊️ <b>{action_info['title']}</b>

{action_info['message']}

🌟 {random.choice(congrat_messages)}
💚 هر روز می‌توانی این کار را تکرار کنی.
🕌 به یاد امام زمان (عج) باش!"""
                        send_message(chat_id, msg, mahdi_submenu(lang))
                        
                    except Exception as e:
                        logger.error(f"خطا در ثبت اقدام مهدویت: {e}")
                        send_message(chat_id, "⚠️ خطا در ثبت اقدام. لطفاً دوباره تلاش کنید.", mahdi_submenu(lang))
                else:
                    send_message(chat_id, "🔧 این اقدام وجود ندارد.", main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # دکمه‌های کتابخانه - قرآن، نهج‌البلاغه، صحیفه
            # ===========================
            if cb_data == "menu_quran":
                send_message(chat_id, "📖 <b>قرآن کریم</b>\n\nبرای جستجو در قرآن، از دکمه «جستجوی هوشمند» استفاده کنید.\n\n💡 می‌توانید سوره یا موضوع مورد نظر را جستجو کنید.", library_submenu(lang))
                return "OK", 200
            
            if cb_data == "menu_nahj":
                send_message(chat_id, "📜 <b>نهج‌البلاغه</b>\n\nبرای جستجو در نهج‌البلاغه، از دکمه «جستجوی هوشمند» استفاده کنید.\n\n💡 می‌توانید خطبه، حکمت یا نامه مورد نظر را جستجو کنید.", library_submenu(lang))
                return "OK", 200
            
            if cb_data == "menu_sahifeh":
                send_message(chat_id, "🤲 <b>صحیفه سجادیه</b>\n\nبرای جستجو در صحیفه سجادیه، از دکمه «جستجوی هوشمند» استفاده کنید.\n\n💡 می‌توانید دعای مورد نظر را جستجو کنید.", library_submenu(lang))
                return "OK", 200
            
            # ===========================
            # مقالات علمی
            # ===========================
            if cb_data == "menu_articles":
                update_user(chat_id, state="waiting_article_search")
                if lang == "fa":
                    msg = """📚 <b>جستجوی مقالات علمی</b>
🔍 موضوع مقاله یا کلیدواژه مورد نظر را وارد کنید:
💡 این موتور در پایگاه‌های علمی معتبر جستجو می‌کند.
📝 لطفاً عبارت خود را ارسال کنید:"""
                else:
                    msg = safe_text(lang, "article_prompt")
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # جستجو در قرآن (تخصصی)
            # ===========================
            if cb_data == "menu_quran_search":
                update_user(chat_id, state="waiting_quran_only")
                if lang == "fa":
                    msg = "📖 <b>جستجو در قرآن کریم</b>\n\nکلمه یا آیه مورد نظر را وارد کنید:\n💡 مثال: «بسم الله» یا «آیه الکرسی»"
                else:
                    msg = "📖 Search in the Holy Quran\n\nEnter a word or verse:"
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # جستجو در اینترنت
            # ===========================
            if cb_data == "menu_internet_search":
                if not FEATURES["internet_search"]:
                    send_message(chat_id, "🔧 جستجوی اینترنتی غیرفعال است.", search_submenu(lang))
                    return "OK", 200
                update_user(chat_id, state="waiting_internet_search")
                if lang == "fa":
                    msg = "🌐 <b>جستجو در اینترنت</b>\n\nموضوع مورد نظر خود را وارد کنید:\n💡 جستجو در گوگل با استفاده از Serper.dev"
                else:
                    msg = "🌐 Internet Search\n\nEnter your search term:"
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # جستجو در نهج‌البلاغه
            # ===========================
            if cb_data == "menu_nahj_search":
                update_user(chat_id, state="waiting_nahj_search")
                if lang == "fa":
                    msg = "📜 <b>جستجو در نهج‌البلاغه</b>\n\nکلمه یا موضوع مورد نظر را وارد کنید:\n💡 مثال: «عدالت» یا «خطبه شقشقیه»"
                else:
                    msg = "📜 Search in Nahjul Balagha\n\nEnter a word or topic:"
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # جستجو در صحیفه سجادیه
            # ===========================
            if cb_data == "menu_sahifeh_search":
                update_user(chat_id, state="waiting_sahifeh_search")
                if lang == "fa":
                    msg = "🤲 <b>جستجو در صحیفه سجادیه</b>\n\nکلمه یا موضوع مورد نظر را وارد کنید:\n💡 مثال: «دعا» یا «رحمت»"
                else:
                    msg = "🤲 Search in Sahifeh Sajjadieh\n\nEnter a word or topic:"
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # روند پیشرفت
            # ===========================
            if cb_data == "menu_progress":
                user_data = get_user(chat_id)
                if lang == "fa":
                    msg = f"""📈 <b>روند پیشرفت شما</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 نام: {user_data.get('name', 'نامشخص')}
🏆 امتیاز: {user_data.get('score', 0)}
📖 کل جستجوها: {user_data.get('search_count', 0)}
🔥 روزهای پیاپی: {user_data.get('streak', 0)}
⭐ امتیاز بازخورد: {user_data.get('feedback_score', 0)}
🎯 بازدیدها: {user_data.get('total_visits', 0)}
✅ کوئست‌ها: {user_data.get('total_quests_completed', 0)}
🤝 دعوت‌ها: {user_data.get('referral_count', 0)}
💰 امتیاز دعوت: {user_data.get('referral_earned', 0)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💪 به تلاش خود ادامه دهید! 🚀"""
                else:
                    msg = safe_text(lang, "progress_info", default="📈 Your Progress")
                send_message(chat_id, msg, competitions_submenu(lang))
                return "OK", 200
            
            # ===========================
            # شبکه اجتماعی
            # ===========================
            if cb_data == "menu_social":
                bot_username = BOT_USERNAME
                if lang == "fa":
                    msg = f"""🤝 <b>شبکه اجتماعی ربات</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 با ما در شبکه‌های اجتماعی همراه شوید:

📢 <b>کانال تلگرام:</b>
{CHANNEL_ID}

🤖 <b>ربات:</b>
https://ble.ir/{bot_username}

📱 <b>اشتراک‌گذاری:</b>
با دوستان خود به اشتراک بگذارید و از دعوت‌ها امتیاز بگیرید!

💚 همراه همیشگی شما در مسیر نور"""
                else:
                    msg = f"🤝 Social Network\n\nChannel: {CHANNEL_ID}\nBot: https://ble.ir/{bot_username}"
                send_message(chat_id, msg, more_submenu(lang))
                return "OK", 200
            
            # ===========================
            # آمار مهدوی من
            # ===========================
            if cb_data == "mahdi_stats":
                if not FEATURES["mahdi_section"]:
                    send_message(chat_id, "🔧 این بخش غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                try:
                    conn = db_conn()
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM mahdi_actions WHERE user_id = ?", (chat_id,))
                    total = cur.fetchone()[0]
                    cur.execute("SELECT action_id, COUNT(*) FROM mahdi_actions WHERE user_id = ? GROUP BY action_id", (chat_id,))
                    actions = cur.fetchall()
                    conn.close()
                    
                    if lang == "fa":
                        msg = f"📊 <b>آمار مهدوی شما</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🌟 کل اقدامات: {total} مورد\n\n"
                        if actions:
                            msg += "🏷️ <b>تفکیک اقدامات:</b>\n"
                            for action_id, count in actions:
                                action_name = next((item['title'] for item in MAHDI_MESSAGES_DATA if item['id'] == action_id), action_id)
                                msg += f"• {action_name}: {count} بار\n"
                        else:
                            msg += "🌸 هنوز هیچ اقدامی انجام نداده‌اید.\n💡 از منوی مهدویت شروع کنید!"
                    else:
                        msg = f"📊 Your Mahdi Stats\nTotal: {total}"
                    send_message(chat_id, msg, mahdi_submenu(lang))
                except Exception as e:
                    logger.error(f"خطا در دریافت آمار مهدوی: {e}")
                    send_message(chat_id, "⚠️ خطا در دریافت آمار.", mahdi_submenu(lang))
                return "OK", 200
            
            # ===========================
            # دستاوردهای من
            # ===========================
            if cb_data == "menu_achievements":
                achievements = get_user_achievements(chat_id)
                if lang == "fa":
                    if achievements:
                        msg = "🏅 <b>دستاوردهای شما</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        for ach in achievements:
                            msg += f"✅ {ach['name']}\n   💰 {ach['points']} امتیاز\n   📅 {ach['unlocked_at'][:10] if ach.get('unlocked_at') else ''}\n\n"
                    else:
                        msg = "🏅 شما هنوز هیچ دستاوردی کسب نکرده‌اید.\n\n💡 با فعالیت در ربات، دستاوردهای جدید کسب کنید:\n• جستجوی هوشمند 🔍\n• ارسال پیشنهاد 📝\n• بازدید روزانه 🌅\n• مطالعه حدیث 🕊️\n• دعوت از دوستان 🤝"
                else:
                    msg = safe_text(lang, "achievements_info", default="🏅 Your Achievements")
                send_message(chat_id, msg, account_submenu(lang))
                return "OK", 200
            
            # ===========================
            # جستجوی هوشمند
            # ===========================
            if cb_data == "menu_smart_search":
                update_user(chat_id, state="waiting_quran_search")
                if lang == "fa":
                    msg = """🧠 <b>جستجوی هوشمند اسلامی</b>
🔍 کلمه یا موضوع مورد نظرت رو وارد کن:
💡 <b>این موتور پیشرفته با هوش مصنوعی در تمام منابع زیر جستجو می‌کند:</b>
📖 قرآن کریم - با ترجمه و تفسیر
📜 نهج‌البلاغه
🤲 صحیفه سجادیه
🕊️ احادیث با منبع کامل
🌐 اینترنت (گوگل)
🤖 هوش مصنوعی
📝 لطفاً عبارت خود را ارسال کن:"""
                else:
                    msg = safe_text(lang, "search_quran_prompt")
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # حدیث روز
            # ===========================
            if cb_data == "menu_hadith" or cb_data == "menu_hadith_old":
                if not FEATURES["hadith_dhikr"]:
                    send_message(chat_id, "🔧 این ویژگی غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                item = random.choice(HADITHS_WITH_DHIKR)
                msg = f"""🕊️ <b>حدیث روز</b>
{item['hadith']}
📝 متن عربی:
{item['arabic']}
📚 <b>منابع:</b>
• {item['source']}
• {item['source2']}
🔹 <b>ذکر روزانه:</b>
{item['dhikr']}
🏷️ دسته: {item['category']}
💚 با یاد خدا دل‌ها آرام می‌گیرد."""
                send_message(chat_id, msg, main_menu(chat_id, lang))
                update_user(chat_id, score=1)
                update_user_score(chat_id, "hadith_read", user)
                return "OK", 200
            
            # ===========================
            # قرآن در لحظه
            # ===========================
            if cb_data == "menu_instant_quran":
                if not FEATURES["instant_quran"]:
                    send_message(chat_id, "🔧 این ویژگی غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                item = random.choice(INSTANT_QURAN_FULL)
                msg = f"""📖 <b>قرآن در لحظه</b>
<b>{item['surah']} (آیه {item['verse']})</b>
{item['arabic']}
✨ {item['trans']}
💚 هر لحظه با قرآن، هر لحظه با نور."""
                send_message(chat_id, msg, main_menu(chat_id, lang))
                update_user(chat_id, score=1)
                update_user_score(chat_id, "instant_quran", user)
                return "OK", 200
            
            # ===========================
            # رویدادها
            # ===========================
            if cb_data == "menu_events":
                if lang == "fa":
                    msg = """📢 <b>رویدادها و مسابقات کانون</b>
🔹 <b>جشنواره قرآن و عترت</b>
• زمان: سالانه
🔹 <b>مسابقات حفظ و مفاهیم قرآن</b>
• دوره‌های ماهانه
🔹 <b>کارگاه‌های تفسیر و تدبر</b>
• هر هفته چهارشنبه‌ها
🔹 <b>برنامه‌های ماه رمضان</b>
• محفل انس با قرآن
🔹 <b>جلسات هفتگی قرآن</b>
• هر جمعه
📌 برای ثبت‌نام به کانال مراجعه کنید."""
                else:
                    msg = safe_text(lang, "events_text")
                send_message(chat_id, msg, main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # پیشنهاد/انتقاد
            # ===========================
            if cb_data == "menu_feedback":
                update_user(chat_id, state="waiting_feedback")
                if lang == "fa":
                    msg = """📝 <b>پیشنهاد یا انتقاد خود را بنویسید</b>
💡 نکات برای دریافت امتیاز بیشتر:
• پیشنهاد خود را دقیق و تأثیرگذار بنویسید
• پیشنهاد سازنده و عملی ارائه دهید
⭐ حداکثر امتیاز: ۱۰"""
                else:
                    msg = safe_text(lang, "feedback_prompt", default="📝 Write your suggestion or critique:")
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # پیام به ادمین
            # ===========================
            if cb_data == "menu_admin_msg":
                update_user(chat_id, state="waiting_admin_msg")
                send_message(chat_id, safe_text(lang, "admin_msg_prompt"), back_menu_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # آمار من
            # ===========================
            if cb_data == "menu_stats":
                latest_user = get_user(chat_id)
                title = get_user_title(latest_user.get("score", 0))
                send_message(chat_id, safe_text(lang, "stats", name=first_name, score=latest_user["score"], search_count=latest_user["search_count"], streak=latest_user["streak"], feedback_score=latest_user["feedback_score"], join_date=latest_user["join_date"], title=title, visits=latest_user["total_visits"], quests=latest_user["total_quests_completed"], referrals=latest_user["referral_count"], referral_earned=latest_user["referral_earned"]), main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # لیگ قرآنی
            # ===========================
            if cb_data == "menu_league":
                if not FEATURES["leaderboard"]:
                    send_message(chat_id, "🔧 این ویژگی غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                top_users = get_leaderboard(10)
                if top_users:
                    leaderboard = ""
                    medals = ["🥇", "🥈", "🥉"]
                    for i, user_data in enumerate(top_users, 1):
                        if len(user_data) >= 5:
                            name, score, visits, streak, referrals = user_data[0], user_data[1], user_data[2], user_data[3], user_data[4]
                        elif len(user_data) >= 4:
                            name, score, visits, streak = user_data[0], user_data[1], user_data[2], user_data[3]
                            referrals = 0
                        else:
                            name, score = user_data[0], user_data[1]
                            visits, streak, referrals = 0, 0, 0
                        if i <= 3:
                            leaderboard += f"{medals[i-1]} {name} — {score} امتیاز (🔥 {streak} روز، 🤝 {referrals} دعوت)\n"
                        else:
                            leaderboard += f"{i}. {name} — {score} امتیاز (🔥 {streak} روز، 🤝 {referrals} دعوت)\n"
                else:
                    leaderboard = "🌟 <b>هنوز کاربری در لیگ قرآنی ثبت نشده است!</b>\n\n💡 اولین نفر باش و با استفاده از ربات امتیاز جمع کن:\n• جستجوی هوشمند 🧠\n• ارسال پیشنهاد 📝\n• بازدید روزانه 🌅\n• مطالعه حدیث 🕊️\n• دعوت از دوستان 🤝"
                send_message(chat_id, safe_text(lang, "league_text", leaderboard=leaderboard), main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # کارنامه من
            # ===========================
            if cb_data == "menu_scorecard":
                rank = get_user_rank(chat_id)
                latest_user = get_user(chat_id)
                title = get_user_title(latest_user.get("score", 0))
                send_message(chat_id, safe_text(lang, "scorecard_text", name=first_name, score=latest_user["score"], rank=rank, search_count=latest_user["search_count"], streak=latest_user["streak"], feedback_score=latest_user["feedback_score"], title=title, quests=latest_user["total_quests_completed"], referrals=latest_user["referral_count"], referral_earned=latest_user["referral_earned"]), main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # تغییر زبان
            # ===========================
            if cb_data == "menu_change_lang":
                send_message(chat_id, safe_text(lang, "select_lang"), lang_keyboard())
                return "OK", 200
            
            # ===========================
            # دریافت روزانه
            # ===========================
            if cb_data == "menu_daily_toggle":
                if not FEATURES["daily_receive"]:
                    send_message(chat_id, "🔧 این ویژگی غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                current = user.get("receive_daily", 0)
                new_value = 0 if current == 1 else 1
                update_user(chat_id, receive_daily=new_value)
                if new_value == 1:
                    send_message(chat_id, safe_text(lang, "daily_enable"), main_menu(chat_id, lang))
                else:
                    send_message(chat_id, safe_text(lang, "daily_disable"), main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # درباره ربات
            # ===========================
            if cb_data == "menu_about":
                send_message(chat_id, safe_text(lang, "about"), main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # راهنما
            # ===========================
            if cb_data == "menu_help":
                if lang == "fa":
                    help_text = """❓ <b>راهنمای استفاده از ربات</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 <b>جستجوی هوشمند اسلامی:</b>
• عبارت مورد نظر را وارد کنید
• نتایج از قرآن، نهج‌البلاغه، صحیفه سجادیه، احادیث و اینترنت

🕊️ <b>حدیث و ذکر:</b>
• دریافت حدیث روزانه با منبع کامل

✨ <b>قرآن در لحظه:</b>
• دریافت آیه‌های کوتاه و پرمعنا

🏆 <b>لیگ قرآنی:</b>
• رقابت با سایر کاربران و کسب امتیاز

🎯 <b>کوئست‌های روزانه:</b>
• انجام کوئست‌های مختلف و دریافت امتیاز

🤝 <b>سیستم دعوت:</b>
• دعوت از دوستان با لینک اختصاصی

🕊️ <b>بخش مهدویت:</b>
• اعمال مربوط به امام زمان (عج)

🌍 <b>زبان‌های پشتیبانی:</b>
• فارسی 🇮🇷 | English 🇬🇧 | العربية 🇸🇦

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💚 همراه همیشگی تو در مسیر نور"""
                else:
                    help_text = safe_text(lang, "help_text", default="📚 Help Guide")
                send_message(chat_id, help_text, main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # یادآوری
            # ===========================
            if cb_data == "menu_reminder":
                send_message(chat_id, "⏰ <b>سیستم یادآوری</b>\n\n📝 متن یادآوری خود را بنویسید.\n\n💡 مثال: «تلاوت قرآن ساعت ۸ صبح»", reminder_keyboard(lang))
                update_user(chat_id, state="waiting_reminder")
                return "OK", 200
            
            if cb_data == "reminder_daily":
                send_message(chat_id, "🕐 <b>یادآوری روزانه</b>\n\n📝 لطفاً متن یادآوری خود را بنویسید.\n\n⏰ این یادآوری هر روز در همین ساعت به شما نمایش داده می‌شود.", back_menu_keyboard(lang))
                update_user(chat_id, state="waiting_reminder")
                return "OK", 200
            
            if cb_data == "reminder_weekly":
                send_message(chat_id, "📅 <b>یادآوری هفتگی</b>\n\n📝 لطفاً متن یادآوری خود را بنویسید.\n\n⏰ این یادآوری هر هفته در همین روز و ساعت به شما نمایش داده می‌شود.", back_menu_keyboard(lang))
                update_user(chat_id, state="waiting_reminder")
                return "OK", 200
            
            if cb_data == "reminder_list":
                try:
                    conn = db_conn()
                    cur = conn.cursor()
                    cur.execute("SELECT reminder_text, remind_at FROM reminders WHERE user_id = ? AND is_done = 0 ORDER BY remind_at LIMIT 5", (chat_id,))
                    reminders = cur.fetchall()
                    conn.close()
                    if reminders:
                        msg = "📋 <b>یادآوری‌های شما:</b>\n\n"
                        for r in reminders:
                            msg += f"📝 {r[0]}\n⏰ {r[1]}\n\n"
                        send_message(chat_id, msg, reminder_keyboard(lang))
                    else:
                        send_message(chat_id, "📋 هیچ یادآوری فعالی ندارید.", reminder_keyboard(lang))
                except Exception as e:
                    logger.error(f"خطا در دریافت یادآوری‌ها: {e}")
                    send_message(chat_id, "⚠️ خطا در دریافت یادآوری‌ها.", reminder_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # اشتراک‌گذاری
            # ===========================
            if cb_data == "menu_share":
                bot_username = BOT_USERNAME
                share_text = f"""🌟 <b>ربات کانون قرآن و عترت</b>
✨ همراه همیشگی تو در مسیر نور و معرفت
🧠 جستجوی هوشمند با AI
🕊️ حدیث و ذکر روزانه
🏆 لیگ قرآنی
🎯 کوئست‌های روزانه
🕊️ بخش مهدویت
🤝 سیستم دعوت و پاداش
💚 با ما همراه شو:
https://ble.ir/{bot_username}"""
                send_message(chat_id, share_text, share_keyboard(lang))
                return "OK", 200
            
            if cb_data == "copy_link":
                bot_username = BOT_USERNAME
                send_message(chat_id, f"📋 <b>لینک ربات:</b>\n\nhttps://ble.ir/{bot_username}\n\n💚 این لینک رو با دوستانت به اشتراک بذار!", share_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # کوئست‌های روزانه
            # ===========================
            if cb_data == "menu_quests":
                if lang == "fa":
                    msg = "🎯 <b>کوئست‌های روزانه</b>\n\nبا انجام هر کوئست، امتیاز بگیر و در لیگ قرآنی بدرخش! 🌟"
                else:
                    msg = safe_text(lang, "quests_info", default="🎯 Daily Quests")
                send_message(chat_id, msg, quest_keyboard(lang))
                return "OK", 200
            
            if cb_data.startswith("quest_"):
                quest_id = cb_data.replace("quest_", "")
                
                if quest_id == "referral":
                    try:
                        conn = db_conn()
                        cur = conn.cursor()
                        cur.execute("SELECT id FROM referrals WHERE referrer_id = ? AND created_at > datetime('now', '-1 day')", (chat_id,))
                        has_referral = cur.fetchone()
                        conn.close()
                        if has_referral:
                            success, message = complete_quest(chat_id, "referral", user)
                            send_message(chat_id, message, quest_keyboard(lang) if success else main_menu(chat_id, lang))
                        else:
                            send_message(chat_id, "🤝 امروز هیچ دعوتی نداشته‌اید!\n\nبرای انجام این کوئست، لطفاً از دکمه «دعوت از دوستان» استفاده کنید.", quest_keyboard(lang))
                    except Exception as e:
                        logger.error(f"خطا در بررسی دعوت: {e}")
                        send_message(chat_id, "⚠️ خطا در بررسی دعوت.", quest_keyboard(lang))
                elif quest_id in ["smart_search", "daily_visit", "feedback", "hadith", "instant_quran"]:
                    success, message = complete_quest(chat_id, quest_id, user)
                    send_message(chat_id, message, quest_keyboard(lang) if success else main_menu(chat_id, lang))
                elif quest_id == "show_quest_points":
                    status = get_quests_status(chat_id)
                    msg = "🎯 <b>وضعیت کوئست‌های روزانه</b>\n\n"
                    for q in status:
                        icon = "✅" if q["completed"] else "⬜"
                        msg += f"{icon} {q['label']} — {q['points']} امتیاز\n"
                        if not q["completed"]:
                            msg += f"   💡 {q['desc']}\n"
                        msg += "\n"
                    msg += f"\n📊 کل امتیازات کسب شده امروز: {user.get('score', 0)}"
                    send_message(chat_id, msg, quest_keyboard(lang))
                else:
                    send_message(chat_id, "🔧 این کوئست غیرفعال است.", main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # بهترین کاربران
            # ===========================
            if cb_data == "menu_best_users":
                if lang == "fa":
                    msg = "🏅 <b>بهترین کاربران</b>\n\nهر شب ساعت ۲۳:۵۹ بهترین کاربر روز\nهر جمعه ساعت ۲۳:۵۹ بهترین کاربر هفته\n\nبرای مشاهده انتخاب کن:"
                else:
                    msg = safe_text(lang, "best_users_info", default="🏅 Best Users")
                send_message(chat_id, msg, best_users_keyboard(lang))
                return "OK", 200
            
            if cb_data == "show_best_daily":
                best = get_best_user_real("daily")
                if best:
                    msg = f"""🏅 <b>بهترین کاربر روز</b>
🌟 نام: {best['user_name']}
🏆 امتیاز: {best['score']}
📅 تاریخ: {best['date']}
💚 تبریک به این عزیز! 🌸"""
                else:
                    msg = "🏅 هنوز بهترین کاربر روز مشخص نشده است."
                send_message(chat_id, msg, best_users_keyboard(lang))
                return "OK", 200
            
            if cb_data == "show_best_weekly":
                best = get_best_user_real("weekly")
                if best:
                    msg = f"""🏆 <b>بهترین کاربر هفته</b>
🌟 نام: {best['user_name']}
🏆 امتیاز: {best['score']}
📅 هفته: {best['date']}
💚 تبریک ویژه به این عزیز! 🌸"""
                else:
                    msg = "🏆 هنوز بهترین کاربر هفته مشخص نشده است."
                send_message(chat_id, msg, best_users_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # دعوت از دوستان
            # ===========================
            if cb_data == "menu_referral":
                referral_code = user.get("referral_code", "")
                if not referral_code:
                    referral_code = generate_referral_code()
                    update_user(chat_id, referral_code=referral_code)
                msg = f"""🤝 <b>سیستم دعوت از دوستان</b>
🌟 کد دعوت شما: <code>{referral_code}</code>
🎁 با دعوت از دوستان:
• به شما و دوستتان ۱۰ امتیاز هدیه داده می‌شود
• با هر دعوت، یک کوئست جدید فعال می‌شود
📊 تعداد دعوت‌های شما: {user.get('referral_count', 0)}
💰 امتیاز کسب شده از دعوت‌ها: {user.get('referral_earned', 0)}
📤 لینک دعوت خود را با دوستان به اشتراک بگذارید:"""
                send_message(chat_id, msg, referral_keyboard(lang, referral_code))
                return "OK", 200
            
            if cb_data == "copy_referral":
                referral_code = user.get("referral_code", "")
                if not referral_code:
                    referral_code = generate_referral_code()
                    update_user(chat_id, referral_code=referral_code)
                referral_link = f"https://ble.ir/{BOT_USERNAME}?start=ref_{referral_code}"
                send_message(chat_id, f"📋 <b>لینک دعوت شما:</b>\n\n{referral_link}\n\n🌸 این لینک رو با دوستانت به اشتراک بذار!", referral_keyboard(lang, referral_code))
                return "OK", 200
            
            if cb_data == "referral_stats":
                referrals_count = user.get("referral_count", 0)
                referrals_earned = user.get("referral_earned", 0)
                msg = f"""📊 <b>آمار دعوت‌های شما</b>
🤝 تعداد دعوت‌ها: {referrals_count}
💰 امتیاز کسب شده: {referrals_earned}
🏅 <b>دستاوردهای دعوت:</b>
• ۵ دعوت: 🥉 دعوت‌کننده برنزی
• ۱۰ دعوت: 🥈 دعوت‌کننده نقره‌ای
• ۲۰ دعوت: 🥇 دعوت‌کننده طلایی"""
                referral_code = user.get("referral_code", "")
                if not referral_code:
                    referral_code = generate_referral_code()
                    update_user(chat_id, referral_code=referral_code)
                send_message(chat_id, msg, referral_keyboard(lang, referral_code))
                return "OK", 200
            
            # ===========================
            # آیات مورد علاقه
            # ===========================
            if cb_data == "menu_favorites":
                favorites = get_favorites(chat_id)
                if favorites:
                    msg = format_favorites_message(favorites, lang)
                    keyboard = []
                    for i, fav in enumerate(favorites[:5]):
                        keyboard.append([{"text": f"🗑️ حذف {fav.get('surah', '')} - {fav.get('verse', '')}", "callback_data": f"remove_fav_{fav.get('index', i)}"}])
                    keyboard.append([{"text": "🗑️ حذف همه", "callback_data": "clear_favorites"}])
                    keyboard.append([{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}])
                    send_message(chat_id, msg, {"inline_keyboard": keyboard})
                else:
                    msg = "❤️ هنوز هیچ آیه‌ای ذخیره نکرده‌اید.\n\n💡 برای ذخیره آیه، پس از جستجوی هوشمند، روی دکمه «ذخیره این آیه» کلیک کنید."
                    send_message(chat_id, msg, main_menu(chat_id, lang))
                return "OK", 200
            
            if cb_data.startswith("show_fav_"):
                index = int(cb_data.replace("show_fav_", ""))
                favorites = get_favorites(chat_id)
                if index < len(favorites):
                    fav = favorites[index]
                    msg = f"""📖 <b>{fav.get('surah', '')} (آیه {fav.get('verse', '')})</b>
{fav.get('text', '')}
✨ {fav.get('trans', '')}
💡 <b>تفسیر:</b> {fav.get('interpretation', '')}
🏷️ <b>موضوعات:</b> {', '.join(fav.get('topics', ['عمومی']))}
📅 ذخیره شده: {fav.get('saved_at', '').split('T')[0] if fav.get('saved_at') else 'نامشخص'}"""
                    fav_keyboard = {
                        "inline_keyboard": [
                            [{"text": "🗑️ حذف این آیه", "callback_data": f"remove_fav_{fav.get('index', 0)}"}],
                            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
                        ]
                    }
                    send_message(chat_id, msg, fav_keyboard)
                else:
                    send_message(chat_id, "⚠️ آیه مورد نظر یافت نشد.", favorites_keyboard(lang, chat_id))
                return "OK", 200
            
            if cb_data.startswith("remove_fav_"):
                index_str = cb_data.replace("remove_fav_", "")
                try:
                    index = int(index_str)
                except:
                    index = 0
                success, message = remove_favorite(chat_id, index)
                if success:
                    send_message(chat_id, message, main_menu(chat_id, lang))
                else:
                    send_message(chat_id, message, favorites_keyboard(lang, chat_id))
                return "OK", 200
            
            if cb_data == "clear_favorites":
                if str(chat_id) in FAVORITES_DATA:
                    FAVORITES_DATA[str(chat_id)] = []
                    save_library_file(FAVORITES_FILE, FAVORITES_DATA)
                    send_message(chat_id, "🗑️ تمام آیات مورد علاقه شما حذف شد.", main_menu(chat_id, lang))
                else:
                    send_message(chat_id, "❤️ شما هیچ آیۀ ذخیره‌ای ندارید.", main_menu(chat_id, lang))
                return "OK", 200
            
            if cb_data.startswith("save_ayah_"):
                index = int(cb_data.replace("save_ayah_", ""))
                ayah_data = None
                for item in QURAN_DATA:
                    if item.get("index") == index:
                        ayah_data = item
                        break
                if ayah_data:
                    success, message = add_favorite(chat_id, ayah_data)
                    if success:
                        update_user(chat_id, score=1)
                        send_message(chat_id, f"{message}\n\n🌟 ۱ امتیاز اضافی برای ذخیره آیه!", main_menu(chat_id, lang))
                    else:
                        send_message(chat_id, message, main_menu(chat_id, lang))
                else:
                    send_message(chat_id, "⚠️ آیه مورد نظر یافت نشد.", main_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # سوالات متداول
            # ===========================
            if cb_data == "menu_faq":
                send_message(chat_id, "❓ <b>سوالات متداول</b>\n\nسوال خود را انتخاب کنید:", faq_keyboard(lang))
                return "OK", 200
            
            if cb_data.startswith("faq_"):
                faq_type = cb_data.replace("faq_", "")
                faq_responses = {
                    "usage": "❓ <b>نحوه استفاده از ربات</b>\n\nبا انتخاب هر دکمه از منوی اصلی، می‌توانید از امکانات ربات استفاده کنید.\n• برای جستجو، دکمه «جستجوی هوشمند» را بزنید.\n• برای حدیث روز، دکمه «حدیث و ذکر روز» را بزنید.\n• برای مشاهده آمار، دکمه «آمار من» را بزنید.",
                    "search": "📖 <b>جستجوی قرآن</b>\n\nکلمه یا موضوع مورد نظر خود را وارد کنید.\nربات در قرآن، نهج‌البلاغه، صحیفه سجادیه و احادیث جستجو می‌کند.\nهمچنین از هوش مصنوعی برای تحلیل استفاده می‌کند.",
                    "ai": "🤖 <b>هوش مصنوعی</b>\n\nهر سوال قرآنی یا دینی دارید، می‌توانید از بخش «هوش مصنوعی» بپرسید.\nپاسخ‌ها با استفاده از DeepSeek تولید می‌شوند.",
                    "points": "🏆 <b>سیستم امتیازات</b>\n\nبا انجام فعالیت‌های زیر امتیاز کسب کنید:\n• جستجوی هوشمند: ۵ امتیاز\n• بازدید روزانه: ۵ امتیاز\n• ارسال پیشنهاد: ۵ امتیاز\n• مطالعه حدیث: ۲ امتیاز\n• دعوت از دوستان: ۱۰ امتیاز\n• اقدامات مهدویت: ۲ تا ۱۰ امتیاز"
                }
                msg = faq_responses.get(faq_type, "❓ سوال مورد نظر یافت نشد.")
                send_message(chat_id, msg, faq_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # ویرایش پروفایل
            # ===========================
            if cb_data == "menu_profile":
                user_data = get_user(chat_id)
                if lang == "fa":
                    msg = f"""✏️ <b>ویرایش پروفایل</b>
👤 نام: {user_data.get('name', 'نامشخص')}
📝 بیو: {user_data.get('bio', 'ثبت نشده')}
🏆 امتیاز: {user_data.get('score', 0)}
👑 عنوان: {get_user_title(user_data.get('score', 0))}
                
برای ویرایش از گزینه‌های زیر استفاده کن:"""
                else:
                    msg = safe_text(lang, "profile_info", default="✏️ Edit Profile")
                send_message(chat_id, msg, profile_keyboard(lang))
                return "OK", 200
            
            if cb_data == "profile_name":
                send_message(chat_id, "✏️ <b>تغییر نام</b>\n\nنام جدید خود را وارد کنید:", back_menu_keyboard(lang))
                update_user(chat_id, state="waiting_profile_name")
                return "OK", 200
            
            if cb_data == "profile_bio":
                send_message(chat_id, "📝 <b>تغییر بیو</b>\n\nبیو جدید خود را وارد کنید (حداکثر ۱۰۰ کاراکتر):", back_menu_keyboard(lang))
                update_user(chat_id, state="waiting_profile_bio")
                return "OK", 200
            
            if cb_data == "profile_view":
                user_data = get_user(chat_id)
                achievements = get_user_achievements(chat_id)
                if lang == "fa":
                    msg = f"""📊 <b>پروفایل شما</b>
👤 نام: {user_data.get('name', 'نامشخص')}
📝 بیو: {user_data.get('bio', 'ثبت نشده')}
🏆 امتیاز: {user_data.get('score', 0)}
👑 عنوان: {get_user_title(user_data.get('score', 0))}
🔥 روزهای پیاپی: {user_data.get('streak', 0)}
🎯 بازدیدها: {user_data.get('total_visits', 0)}
📅 تاریخ عضویت: {user_data.get('join_date', 'نامشخص')}
🏅 دستاوردها: {len(achievements)} مورد"""
                    if achievements:
                        msg += "\n\n🏅 <b>دستاوردهای شما:</b>\n"
                        for ach in achievements[:5]:
                            msg += f"• {ach['name']} 💰 {ach['points']} امتیاز\n"
                else:
                    msg = safe_text(lang, "profile_view", default="📊 Your Profile")
                send_message(chat_id, msg, profile_keyboard(lang))
                return "OK", 200
            
            # ===========================
            # پنل ادمین
            # ===========================
            if cb_data == "admin_panel":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                if not FEATURES["admin_panel"]:
                    send_message(chat_id, "🔧 پنل ادمین غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                stats = get_system_stats()
                admin_text = f"""🛠️ <b>پنل مدیریت</b>
{'='*50}
📊 <b>آمار کلی:</b>
👥 کل کاربران: {stats['total_users']}
🟢 فعال (۷ روز): {stats['active_users_7d']}
📩 بازخوردهای در انتظار: {stats['pending_feedbacks']}
🏆 برترین امتیاز: {stats['highest_score']}
🤝 کل دعوت‌ها: {stats.get('total_referrals', 0)}
📚 <b>محتوای کتابخانه:</b>
📖 قرآن: {stats['quran_count']} آیه
📜 نهج‌البلاغه: {stats['nahj_count']} فراز
🤲 صحیفه سجادیه: {stats['sahifeh_count']} دعا
🧠 موضوعات: {len(TOPICS_DATA)} موضوع
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
                stats = get_system_stats()
                stats_text = f"""📊 <b>آمار کامل ربات</b>
{'='*50}
👥 <b>کاربران:</b>
• کل کاربران: {stats['total_users']}
• فعال (۷ روز): {stats['active_users_7d']}
• فعال (۳۰ روز): {stats['active_users_30d']}
📝 <b>بازخوردها:</b>
• کل بازخوردها: {stats['total_feedbacks']}
• در انتظار بررسی: {stats['pending_feedbacks']}
🏆 <b>امتیازات:</b>
• بالاترین امتیاز: {stats['highest_score']}
📚 <b>کتابخانه:</b>
• آیات قرآن: {stats['quran_count']}
• فرازهای نهج‌البلاغه: {stats['nahj_count']}
• دعاهای صحیفه سجادیه: {stats['sahifeh_count']}
🎯 <b>کوئست‌ها:</b>
• کل کوئست‌های انجام شده: {stats.get('total_quests', 0)}
🤝 <b>دعوت‌ها:</b>
• کل دعوت‌ها: {stats.get('total_referrals', 0)}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
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
                cur.execute("SELECT id, user_name, content, score, created_at, category FROM feedbacks WHERE status='pending' ORDER BY score DESC, id DESC LIMIT 10")
                feedbacks = cur.fetchall()
                conn.close()
                if feedbacks:
                    msg = "📩 <b>لیست انتقادات و پیشنهادات:</b>\n\n"
                    for f in feedbacks:
                        msg += f"""📌 {f[1]}
📝 {f[2][:100]}...
⭐ امتیاز: {f[3]}
🏷️ دسته: {f[5]}
📅 {f[4]}
"""
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
                    send_message(chat_id, "🔧 این ویژگی غیرفعال است.", admin_menu(chat_id, lang))
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
                    msg = "👥 <b>لیست کاربران (۲۰ نفر برتر):</b>\n\n"
                    for i, (uid, name, score) in enumerate(users, 1):
                        title = get_user_title(score)
                        msg += f"{i}. {name} — {score} امتیاز ({title})\n"
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
                times = "🕐 ۸:۰۰ صبح (قرآن)\n🕐 ۱۲:۰۰ ظهر (صحیفه سجادیه)\n🕐 ۱۸:۰۰ عصر (نهج‌البلاغه)"
                send_message(chat_id, f"""⏰ <b>تنظیمات زمان‌بندی</b>
وضعیت: {schedule_status}
زمان‌های ارسال:
{times}
📌 برای تغییر وضعیت، از دکمه «کنترل ویژگی‌ها» استفاده کنید.""", admin_menu(chat_id, lang))
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
            # وضعیت سیستم
            # ===========================
            if cb_data == "admin_system":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                send_message(chat_id, format_system_stats(), admin_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # مدیریت دستاوردها
            # ===========================
            if cb_data == "admin_achievements":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                msg = "🏅 <b>دستاوردهای قابل کسب</b>\n\n"
                for key, achievement in ACHIEVEMENTS.items():
                    msg += f"{achievement['name']}\n   💰 {achievement['points']} امتیاز\n\n"
                msg += "\n📌 کاربران با کسب امتیاز، این دستاوردها را دریافت می‌کنند."
                send_message(chat_id, msg, admin_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # مدیریت بهترین کاربران
            # ===========================
            if cb_data == "admin_best_users":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                msg = "🏆 <b>مدیریت بهترین کاربران</b>\n\n"
                best_daily = get_best_user_real("daily")
                if best_daily:
                    msg += f"🏅 بهترین کاربر روز:\n{best_daily['user_name']} — {best_daily['score']} امتیاز\n\n"
                else:
                    msg += "🏅 بهترین کاربر روز: هنوز مشخص نشده\n\n"
                best_weekly = get_best_user_real("weekly")
                if best_weekly:
                    msg += f"🏆 بهترین کاربر هفته:\n{best_weekly['user_name']} — {best_weekly['score']} امتیاز\n\n"
                else:
                    msg += "🏆 بهترین کاربر هفته: هنوز مشخص نشده\n\n"
                msg += "📌 این عناوین هر روز ساعت ۲۳:۵۹ و هر جمعه ساعت ۲۳:۵۹ به‌روزرسانی می‌شوند."
                send_message(chat_id, msg, admin_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # آمار دعوت‌ها
            # ===========================
            if cb_data == "admin_referrals":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                try:
                    conn = db_conn()
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM referrals")
                    total_ref = cur.fetchone()[0]
                    cur.execute("SELECT user_name, referral_count, referral_earned FROM users WHERE referral_count > 0 ORDER BY referral_count DESC LIMIT 10")
                    top_referrers = cur.fetchall()
                    conn.close()
                    msg = "🤝 <b>آمار دعوت‌ها</b>\n\n"
                    msg += f"📊 کل دعوت‌ها: {total_ref}\n\n"
                    if top_referrers:
                        msg += "🏆 <b>برترین دعوت‌کنندگان:</b>\n\n"
                        for i, (name, count, earned) in enumerate(top_referrers, 1):
                            msg += f"{i}. {name} — {count} دعوت (💰 {earned} امتیاز)\n"
                    else:
                        msg += "📌 هنوز دعوتی ثبت نشده است."
                    send_message(chat_id, msg, admin_menu(chat_id, lang))
                except Exception as e:
                    logger.error(f"خطا در دریافت آمار دعوت‌ها: {e}")
                    send_message(chat_id, "⚠️ خطا در دریافت آمار دعوت‌ها.", admin_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # گزارش هفتگی
            # ===========================
            if cb_data == "admin_weekly_report":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                send_weekly_report()
                send_message(chat_id, "📊 گزارش هفتگی به ادمین ارسال شد.", admin_menu(chat_id, lang))
                return "OK", 200
            
            # ===========================
            # نظرسنجی‌ها
            # ===========================
            if cb_data == "admin_surveys":
                if chat_id != ADMIN_ID:
                    send_message(chat_id, "⛔ دسترسی غیرمجاز.")
                    return "OK", 200
                if not SURVEYS_DATA:
                    send_message(chat_id, "📝 هیچ نظرسنجی فعالی وجود ندارد.", admin_menu(chat_id, lang))
                    return "OK", 200
                msg = "📝 <b>نظرسنجی‌های فعال</b>\n\n"
                for sid, survey in SURVEYS_DATA.items():
                    if survey.get("active", True):
                        results = get_survey_results(sid)
                        if results:
                            msg += f"📌 {survey['question']}\n"
                            for r in results['results']:
                                msg += f"   {r['option']}: {r['votes']} رأی ({r['percentage']}%)\n"
                            msg += f"   📊 مجموع: {results['total_votes']} رأی\n\n"
                send_message(chat_id, msg, admin_menu(chat_id, lang))
                return "OK", 200
        
        return "OK", 200
    
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"WEBHOOK ERROR: {error_msg}\n{traceback_str}")
        log_error("webhook_error", error_msg, traceback_str)
        return "OK", 200

# =========================================================
# ۳۲. ادامه وب هوک - توابع وضعیت
# =========================================================
def handle_state_message(chat_id, text, user):
    lang = user["lang"]
    state = user["state"]
    name = user["name"] or "کاربر گرامی"
    
    if state == "waiting_ai":
        send_message(chat_id, safe_text(lang, "ai_wait"))
        answer = ask_ai(text, lang)
        send_message(chat_id, f"🤖 {answer}", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score=2)
        update_user_score(chat_id, "ai_question", user)
        return True
    
    if state == "waiting_admin_msg":
        try:
            admin_text = f"""📩 <b>پیام جدید از کاربر</b>
👤 نام: {name}
🆔 chat_id: {chat_id}
📝 امتیاز: {user.get('score', 0)}
💬 متن:
{text}"""
            result = send_message_with_retry(ADMIN_ID, admin_text)
            if result and result.get("ok"):
                send_message(chat_id, safe_text(lang, "admin_msg_sent"), main_menu(chat_id, lang))
            else:
                send_message(chat_id, "⚠️ متأسفانه پیام شما ارسال نشد.", main_menu(chat_id, lang))
        except Exception as e:
            logger.error(f"خطا در ارسال پیام به ادمین: {e}")
            send_message(chat_id, "⚠️ خطا در ارسال پیام.", main_menu(chat_id, lang))
        update_user(chat_id, state="none")
        return True
    
    if state == "waiting_quran_search":
        send_chat_action(chat_id, "typing")
        try:
            results = smart_search(text, lang)
            if results and results["sources_count"] > 0:
                formatted_result = format_smart_results(results, text, lang)
                send_message(chat_id, formatted_result, main_menu(chat_id, lang))
                update_user(chat_id, state="none", score=3, search_count=1)
                update_user_score(chat_id, "smart_search", user)
                if results.get("quran"):
                    first_ayah = results["quran"][0]
                    fav_keyboard = {
                        "inline_keyboard": [
                            [{"text": "❤️ ذخیره این آیه", "callback_data": f"save_ayah_{first_ayah.get('index', 0)}"}],
                            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
                        ]
                    }
                    send_message(chat_id, "💡 آیا می‌خواهید این آیه را در علاقه‌مندی‌های خود ذخیره کنید؟", fav_keyboard)
                return True
        except Exception as e:
            logger.error(f"خطا در جستجوی پیشرفته: {e}")
        
        # جستجوی ساده به عنوان پشتیبان
        results = search_quran_only(text)
        if results:
            msg = "📖 <b>نتایج جستجو در قرآن:</b>\n\n"
            for i, item in enumerate(results[:5], 1):
                msg += f"{i}. {format_search_result(item, 'قرآن')}\n\n"
            send_message(chat_id, msg, main_menu(chat_id, lang))
            update_user(chat_id, score=1, search_count=1)
            update_user_score(chat_id, "quran_search", user)
        else:
            other_results = search_other_books(text)
            if other_results:
                msg = "📚 <b>در قرآن یافت نشد، اما در سایر کتاب‌ها:</b>\n\n"
                for i, item in enumerate(other_results[:3], 1):
                    book_type = item.get("book_type", "نهج‌البلاغه")
                    msg += f"{i}. {format_search_result(item, book_type)}\n\n"
                send_message(chat_id, msg, main_menu(chat_id, lang))
            else:
                suggestions = "💡 کلمات کلیدی پیشنهادی:\n• ایمان\n• صبر\n• نماز\n• توکل\n• رحمت"
                send_message(chat_id, f"😔 نتیجه‌ای برای «{text}» پیدا نشد.\n\n{suggestions}", main_menu(chat_id, lang))
        update_user(chat_id, state="none")
        return True
    
    if state == "waiting_feedback":
        if not FEATURES["feedback_system"]:
            send_message(chat_id, "🔧 این ویژگی غیرفعال است.", main_menu(chat_id, lang))
            update_user(chat_id, state="none")
            return True
        update_user(chat_id, state="none")
        score = 0
        category = "general"
        if "قرآن" in text or "ترجمه" in text:
            category = "quran"
            score += 2
        elif "حدیث" in text:
            category = "hadith"
            score += 2
        elif "پیشنهاد" in text:
            category = "suggestion"
            score += 3
        elif "انتقاد" in text:
            category = "critique"
            score += 3
        if len(text) > 50:
            score += 2
        if len(text) > 100:
            score += 1
        if "لطفا" in text or "متشکرم" in text:
            score += 1
        score = min(score, 10)
        try:
            conn = db_conn()
            cur = conn.cursor()
            cur.execute("INSERT INTO feedbacks (user_id, user_name, type, content, score, created_at, category) VALUES (?, ?, 'suggestion', ?, ?, CURRENT_TIMESTAMP, ?)", (chat_id, name, text, score, category))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطا در ذخیره پیشنهاد: {e}")
        if score >= 3:
            update_user(chat_id, score=score, feedback_score=score)
            send_message(chat_id, safe_text(lang, "feedback_score_msg", score=score), main_menu(chat_id, lang))
            send_message_with_retry(ADMIN_ID, f"""📩 <b>پیشنهاد جدید</b>\n👤 {name}\n📝 {text}\n⭐ امتیاز: {score}""")
        else:
            send_message(chat_id, safe_text(lang, "feedback_no_score"), main_menu(chat_id, lang))
        update_user_score(chat_id, "feedback", user)
        return True
    
    if state == "waiting_broadcast":
        if chat_id != ADMIN_ID:
            send_message(chat_id, "⛔ دسترسی غیرمجاز.")
            update_user(chat_id, state="none")
            return True
        if not FEATURES["broadcast"]:
            send_message(chat_id, "🔧 این ویژگی غیرفعال است.", admin_menu(chat_id, lang))
            update_user(chat_id, state="none")
            return True
        update_user(chat_id, state="none")
        users = get_all_users(10000)
        count = 0
        for uid, uname, uscore in users:
            try:
                send_message(int(uid), f"""📢 <b>اطلاعیه کانون قرآن و عترت</b>\n\n{text}\n🙏 از همراهی شما سپاسگزاریم.""")
                count += 1
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"خطا در ارسال به {uid}: {e}")
        save_sent_message("broadcast", text, f"{count} users")
        send_message(chat_id, safe_text(lang, "broadcast_success", count=count), admin_menu(chat_id, lang))
        return True
    
    if state == "waiting_reminder":
        try:
            conn = db_conn()
            cur = conn.cursor()
            cur.execute("INSERT INTO reminders (user_id, reminder_text, remind_at, created_at) VALUES (?, ?, datetime('now', '+1 day'), CURRENT_TIMESTAMP)", (chat_id, text))
            conn.commit()
            conn.close()
            send_message(chat_id, f"✅ یادآوری ثبت شد:\n📝 {text}\n⏰ فردا در همین ساعت.", main_menu(chat_id, lang))
        except Exception as e:
            logger.error(f"خطا در ثبت یادآوری: {e}")
            send_message(chat_id, "⚠️ خطا در ثبت یادآوری.", main_menu(chat_id, lang))
        update_user(chat_id, state="none")
        return True
    
    if state == "waiting_profile_name":
        if len(text) > 30:
            send_message(chat_id, "⚠️ نام نباید بیشتر از ۳۰ کاراکتر باشد.", back_menu_keyboard(lang))
            return True
        update_user(chat_id, name=text, state="none")
        send_message(chat_id, f"✅ نام شما با موفقیت به «{text}» تغییر یافت!", main_menu(chat_id, lang))
        return True
    
    if state == "waiting_profile_bio":
        if len(text) > 100:
            send_message(chat_id, "⚠️ بیو نباید بیشتر از ۱۰۰ کاراکتر باشد.", back_menu_keyboard(lang))
            return True
        update_user(chat_id, bio=text, state="none")
        send_message(chat_id, f"✅ بیو شما با موفقیت به روز شد!", main_menu(chat_id, lang))
        return True
    
    # =========================================================
    # وضعیت‌های جدید برای دکمه‌های اضافه شده
    # =========================================================
    if state == "waiting_article_search":
        send_chat_action(chat_id, "typing")
        results = internet_search(text, lang)
        if results:
            msg = safe_text(lang, "article_result", query=text, results="")
            for i, item in enumerate(results[:5], 1):
                msg += f"\n{i}. <b>{item.get('title', 'بدون عنوان')}</b>\n"
                if item.get('snippet'):
                    msg += f"   📝 {item.get('snippet', '')[:150]}...\n"
                if item.get('link'):
                    msg += f"   🔗 <a href='{item['link']}'>لینک</a>\n"
            send_message(chat_id, msg, library_submenu(lang))
        else:
            if lang == "fa":
                msg = f"😔 نتیجه‌ای برای «{text}» پیدا نشد.\n\n💡 پیشنهاد: از کلمات کلیدی ساده‌تر استفاده کنید."
            else:
                msg = f"😔 No results found for «{text}»."
            send_message(chat_id, msg, library_submenu(lang))
        update_user(chat_id, state="none")
        return True
    
    if state == "waiting_quran_only":
        send_chat_action(chat_id, "typing")
        results = search_quran_only(text)
        if results:
            msg = "📖 <b>نتایج جستجو در قرآن:</b>\n\n"
            for i, item in enumerate(results[:5], 1):
                msg += f"{i}. {format_search_result(item, 'قرآن')}\n\n"
            send_message(chat_id, msg, search_submenu(lang))
            update_user(chat_id, score=1, search_count=1)
            update_user_score(chat_id, "quran_search", user)
        else:
            if lang == "fa":
                msg = f"😔 نتیجه‌ای برای «{text}» در قرآن پیدا نشد.\n\n💡 از جستجوی جامع یا هوش مصنوعی استفاده کنید."
            else:
                msg = f"😔 No results found in Quran for «{text}»."
            send_message(chat_id, msg, search_submenu(lang))
        update_user(chat_id, state="none")
        return True
    
    if state == "waiting_internet_search":
        send_chat_action(chat_id, "typing")
        results = internet_search(text, lang)
        if results:
            msg = f"🌐 <b>نتایج جستجوی اینترنتی برای «{text}»</b>\n\n"
            for i, item in enumerate(results[:5], 1):
                msg += f"{i}. <b>{item.get('title', 'بدون عنوان')}</b>\n"
                if item.get('snippet'):
                    msg += f"   📝 {item.get('snippet', '')[:150]}...\n"
                if item.get('link'):
                    msg += f"   🔗 <a href='{item['link']}'>لینک</a>\n"
                if item.get('source'):
                    msg += f"   📌 منبع: {item['source']}\n"
                msg += "\n"
            send_message(chat_id, msg, search_submenu(lang))
        else:
            if lang == "fa":
                msg = f"😔 نتیجه‌ای برای «{text}» در اینترنت پیدا نشد.\n\n💡 پیشنهاد: کلمات کلیدی خود را تغییر دهید."
            else:
                msg = f"😔 No results found for «{text}»."
            send_message(chat_id, msg, search_submenu(lang))
        update_user(chat_id, state="none")
        return True
    
    if state == "waiting_nahj_search":
        send_chat_action(chat_id, "typing")
        results = search_other_books(text)
        nahj_results = [r for r in results if r.get("book_type") == "نهج‌البلاغه"]
        if nahj_results:
            msg = "📜 <b>نتایج جستجو در نهج‌البلاغه:</b>\n\n"
            for i, item in enumerate(nahj_results[:5], 1):
                msg += f"{i}. {format_search_result(item, 'نهج‌البلاغه')}\n\n"
            send_message(chat_id, msg, search_submenu(lang))
        else:
            if lang == "fa":
                msg = f"😔 نتیجه‌ای برای «{text}» در نهج‌البلاغه پیدا نشد.\n\n💡 از جستجوی جامع استفاده کنید."
            else:
                msg = f"😔 No results found in Nahjul Balagha for «{text}»."
            send_message(chat_id, msg, search_submenu(lang))
        update_user(chat_id, state="none")
        return True
    
    if state == "waiting_sahifeh_search":
        send_chat_action(chat_id, "typing")
        results = search_other_books(text)
        sahifeh_results = [r for r in results if r.get("book_type") == "صحیفه سجادیه"]
        if sahifeh_results:
            msg = "🤲 <b>نتایج جستجو در صحیفه سجادیه:</b>\n\n"
            for i, item in enumerate(sahifeh_results[:5], 1):
                msg += f"{i}. {format_search_result(item, 'صحیفه سجادیه')}\n\n"
            send_message(chat_id, msg, search_submenu(lang))
        else:
            if lang == "fa":
                msg = f"😔 نتیجه‌ای برای «{text}» در صحیفه سجادیه پیدا نشد.\n\n💡 از جستجوی جامع استفاده کنید."
            else:
                msg = f"😔 No results found in Sahifeh Sajjadieh for «{text}»."
            send_message(chat_id, msg, search_submenu(lang))
        update_user(chat_id, state="none")
        return True
    
    # وضعیت جستجوی پیشرفته‌تر - پشتیبانی از هوش مصنوعی
    if state == "waiting_ai_ask":
        send_message(chat_id, "⏳ در حال پردازش سوال شما با هوش مصنوعی...")
        answer = ask_ai(text, lang)
        send_message(chat_id, f"🤖 {answer}", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score=2)
        return True
    
    if state == "menu_ai_ask":
        update_user(chat_id, state="waiting_ai_ask")
        send_message(chat_id, "🤖 <b>پرسش از هوش مصنوعی</b>\n\nسوال خود را مطرح کنید:", back_menu_keyboard(lang))
        return True
    
    if state == "menu_ai_tafsir":
        update_user(chat_id, state="waiting_ai_ask")
        send_message(chat_id, "📝 <b>تفسیر موضوعی</b>\n\nموضوع مورد نظر برای تفسیر را وارد کنید:", back_menu_keyboard(lang))
        return True
    
    if state == "menu_ai_suggest":
        update_user(chat_id, state="waiting_ai_ask")
        send_message(chat_id, "🔮 <b>پیشنهاد موضوعی</b>\n\nموضوع مورد نظر را وارد کنید تا پیشنهادات مرتبط دریافت کنید:", back_menu_keyboard(lang))
        return True
    
    return False

# =========================================================
# ۳۳. مسیرهای تست و سلامت
# =========================================================
@app.route("/", methods=["GET", "HEAD"])
def health():
    return jsonify({
        "status": "ok",
        "service": "labbayk_quranbot",
        "version": "22.1",
        "time": datetime.now().isoformat(),
        "persian_date": get_persian_date(),
        "total_users": get_user_count(),
        "features": FEATURES,
        "port": PORT,
        "jdatetime_installed": HAS_JDATETIME,
        "quran_count": len(QURAN_DATA),
        "nahj_count": len(NAHJ_DATA),
        "sahifeh_count": len(SAHIFEH_DATA)
    }), 200

@app.route("/webhook", methods=["GET", "HEAD"])
def webhook_check():
    return jsonify({"status": "ok", "message": "Webhook is alive"}), 200

# =========================================================
# ۳۴. اجرای استارتاپ و سرور وب
# =========================================================
def startup():
    try:
        logger.info("🚀 شروع راه‌اندازی ربات...")
        init_db()
        logger.info("✅ دیتابیس راه‌اندازی شد.")
        load_library()
        logger.info("✅ کتابخانه بارگذاری شد.")
        
        # بررسی کلیدهای API
        if OPENROUTER_KEY and len(OPENROUTER_KEY) > 10:
            logger.info("✅ کلید OpenRouter تنظیم شده است.")
            logger.info(f"📌 مدل استفاده شده: {OPENROUTER_MODEL}")
            FEATURES["deepseek_ai"] = True
        else:
            logger.warning("⚠️ کلید OpenRouter نامعتبر است.")
            FEATURES["deepseek_ai"] = False
        
        if SERPER_API_KEY and len(SERPER_API_KEY) > 10:
            logger.info("✅ کلید Serper.dev تنظیم شده است (جستجوی گوگل)")
            FEATURES["internet_search"] = True
        else:
            logger.warning("⚠️ کلید Serper.dev تنظیم نشده است.")
        
        # راه‌اندازی تسک‌های زمان‌بندی
        if FEATURES["daily_posts"]:
            scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("✅ اسکژولر روزانه راه‌اندازی شد.")
        
        if FEATURES["best_user_daily"] or FEATURES["best_user_weekly"]:
            best_user_thread = threading.Thread(target=schedule_best_users, daemon=True)
            best_user_thread.start()
            logger.info("✅ اسکژولر بهترین کاربران راه‌اندازی شد.")
        
        if FEATURES["auto_backup"]:
            backup_thread = threading.Thread(target=backup_scheduler, daemon=True)
            backup_thread.start()
            logger.info("✅ اسکژولر بک‌آپ راه‌اندازی شد.")
        
        if FEATURES["weekly_report"]:
            weekly_report_thread = threading.Thread(target=weekly_report_scheduler, daemon=True)
            weekly_report_thread.start()
            logger.info("✅ اسکژولر گزارش هفتگی راه‌اندازی شد.")
        
        if FEATURES["motivational_messages"]:
            motivational_thread = threading.Thread(target=motivational_scheduler, daemon=True)
            motivational_thread.start()
            logger.info("✅ اسکژولر پیام‌های انگیزشی راه‌اندازی شد.")
        
        if FEATURES["religious_reminders"]:
            religious_thread = threading.Thread(target=religious_reminder_scheduler, daemon=True)
            religious_thread.start()
            logger.info("✅ اسکژولر مناسبت‌های مذهبی راه‌اندازی شد.")
        
        # پاکسازی کش
        def cache_cleaner():
            while True:
                try:
                    time.sleep(21600)
                    MEMBERSHIP_CACHE.clear()
                    SEARCH_CACHE.clear()
                    logger.info("🧹 کش پاکسازی شد.")
                except Exception as e:
                    logger.error(f"خطا در پاکسازی کش: {e}")
        cleaner_thread = threading.Thread(target=cache_cleaner, daemon=True)
        cleaner_thread.start()
        logger.info("✅ تمیزکاری کش راه‌اندازی شد.")
        
        logger.info("🎉 ربات با موفقیت راه‌اندازی شد!")
        logger.info(f"📊 آمار اولیه: {get_system_stats()}")
        logger.info(f"🌐 سرور روی پورت {PORT} در حال اجراست...")
        logger.info(f"🌍 زبان‌های پشتیبانی: فارسی, English, العربية")
        logger.info(f"🕊️ بخش مهدویت: {'فعال' if FEATURES['mahdi_section'] else 'غیرفعال'}")
        logger.info(f"❤️ سیستم ذخیره آیات: {'فعال' if FEATURES['favorites'] else 'غیرفعال'}")
        logger.info(f"📚 سیستم ارسال سه‌گانه: قرآن + صحیفه + نهج‌البلاغه")
        logger.info(f"📖 تعداد آیات قرآن: {len(QURAN_DATA)}")
        logger.info(f"📜 تعداد فرازهای نهج‌البلاغه: {len(NAHJ_DATA)}")
        logger.info(f"🤲 تعداد دعاهای صحیفه: {len(SAHIFEH_DATA)}")
        logger.info(f"🤖 وضعیت هوش مصنوعی: {'فعال ✅' if FEATURES['deepseek_ai'] else 'غیرفعال ❌'}")
        logger.info(f"🌐 وضعیت جستجوی اینترنتی: {'فعال ✅' if FEATURES['internet_search'] else 'غیرفعال ❌'}")
        logger.info(f"📋 نسخه ربات: ۲۲.۱ (دانشجوپسند - رفع دکمه‌های خراب)")
    except Exception as e:
        logger.error(f"❌ خطا در راه‌اندازی: {e}")

def daily_scheduler():
    time.sleep(30)
    while True:
        try:
            send_daily_posts()
            update_daily_stats()
        except Exception as e:
            logger.error(f"خطا در اسکجولر: {e}")
        time.sleep(60)

startup()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 ربات روی پورت {port} در حال اجراست...")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
