# -*- coding: utf-8 -*-
"""
ربات حرفه‌ای کانون قرآن و عترت - نسخه ۱۵.۰ (نسخه نهایی و جامع)
ویژه دانشگاه علوم پزشکی شیراز
با موتور دانش اسلامی (Islamic Knowledge Engine) و جستجوی پیشرفته
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
# تنظیمات لاگ‌گیری پیشرفته (قبل از هر چیز)
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
# پشتیبانی از تاریخ شمسی (با fallback به میلادی)
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

# کلیدهای API برای جستجوی اینترنتی
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CX_ID = os.getenv("GOOGLE_CX_ID", "")
SERP_API_KEY = os.getenv("SERP_API_KEY", "")

# =========================================================
# ۲. Feature Flags (کنترل ویژگی‌ها با تنظیمات پویا)
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
    "voice_search": True,
    "favorites": True,
    "surveys": True,
    "weekly_report": True,
    "auto_backup": True,
    "profile_edit": True,
    "motivational_messages": True,
    "religious_reminders": True,
    "quran_images": True,
    "faq_system": True
}

# =========================================================
# ۳. سیستم چندزبانه (قبل از استفاده)
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
        "stats": "📊 آمار تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}\n⭐ امتیاز پیشنهادات: {feedback_score}\n📅 تاریخ عضویت: {join_date}\n👑 عنوان: {title}\n🎯 بازدیدها: {visits}\n✅ کوئست‌های انجام شده: {quests}\n🤝 دعوت‌ها: {referrals}\n💰 امتیاز دعوت: {referral_earned}",
        "about": "🌸 این ربات با عشق توسط کانون قرآن و عترت دانشگاه علوم پزشکی شیراز طراحی شده است.\n\n📚 امکانات:\n• جستجوی هوشمند اسلامی 🧠\n• هوش مصنوعی DeepSeek 🤖\n• جستجوی صوتی 🎤\n• حدیث و ذکر روزانه 🕊️\n• قرآن در لحظه ✨\n• کارنامه و لیگ قرآنی 🏆\n• ارسال روزانه 🔔\n• پیشنهاد و انتقاد ⭐\n• کوئست‌های روزانه 🎯\n• بهترین کاربران 🏅\n• سیستم دعوت 🤝\n• ذخیره آیات مورد علاقه ❤️\n• نظرسنجی 📝\n• یادآوری مناسبت‌ها 🕌\n• پشتیبانی از زبان عربی 🇸🇦\n\n💚 همراه همیشگی تو در مسیر نور",
        "daily_enable": "✅ دریافت روزانه فعال شد. هر روز با عشق محتوای جدید می‌فرستم.",
        "daily_disable": "❌ دریافت روزانه غیرفعال شد. هر وقت خواستی فعالش کن.",
        "daily_toggle": "🔔 دریافت روزانه",
        "back_to_menu": "🏠 برگشت به منوی اصلی",
        "search_quran_prompt": "📖 کلمه یا عبارت مورد نظرت رو بفرست تا با عشق جستجو کنیم.",
        "article_prompt": "📚 موضوع مقاله یا کلیدواژه‌ات رو بفرست.",
        "league_text": "🏆 لیگ قرآنی:\n\n{leaderboard}\n\n💡 برای کسب امتیاز:\n• جستجوی قرآن 📖\n• ارسال پیشنهاد 📝\n• بازدید روزانه 🌅\n• مطالعه حدیث 🕊️\n• دعوت از دوستان 🤝",
        "scorecard_text": "📋 کارنامه و رتبه تو:\n\n👤 نام: {name}\n🏆 امتیاز: {score}\n🎯 رتبه: {rank}\n📖 جستجوها: {search_count}\n🔥 روزهای پیاپی: {streak}\n⭐ امتیاز پیشنهادات: {feedback_score}\n👑 عنوان: {title}\n✅ کوئست‌ها: {quests}\n🤝 دعوت‌ها: {referrals}\n💰 امتیاز دعوت: {referral_earned}",
        "events_text": "📢 رویدادها و مسابقات کانون:\n\n🔹 جشنواره قرآن و عترت\n🔹 مسابقات حفظ و مفاهیم قرآن\n🔹 کارگاه‌های تفسیر و تدبر\n🔹 برنامه‌های ماه رمضان\n🔹 جلسات هفتگی قرآن\n🔹 مسابقات مقاله‌نویسی قرآنی\n\n📌 برای اطلاعات بیشتر به کانال مراجعه کن.",
        "unknown_error": "⚠️ یه خطای کوچک رخ داد. دوباره امتحان کن، مطمئنم موفق می‌شی.",
        "article_result": "📚 نتایج جستجوی مقالات علمی برای «{query}»:\n\n{results}\n\n💡 اگر نتیجه‌ای نیافتی، می‌تونی از مقالات پیشنهادی ما استفاده کنی.",
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
        "admin_system": "💻 وضعیت سیستم",
        "admin_achievements": "🏅 مدیریت دستاوردها",
        "admin_best_users": "🏆 بهترین کاربران",
        "admin_referrals": "🤝 آمار دعوت‌ها",
        "admin_weekly_report": "📊 گزارش هفتگی",
        "admin_surveys": "📝 نظرسنجی‌ها",
        "menu_labels": {
            "islamic_search": "🧠 جستجوی هوشمند",
            "ai": "🤖 هوش مصنوعی",
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
            "about": "ℹ️ درباره ربات",
            "help": "❓ راهنما",
            "share": "📤 اشتراک‌گذاری",
            "reminder": "⏰ یادآوری",
            "quests": "🎯 کوئست‌های روزانه",
            "best_users": "🏅 بهترین کاربران",
            "referral": "🤝 دعوت از دوستان",
            "favorites": "❤️ آیات مورد علاقه",
            "faq": "❓ سوالات متداول",
            "voice_search": "🎤 جستجوی صوتی",
            "profile": "✏️ ویرایش پروفایل"
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
        "stats": "📊 Your stats:\n\n👤 Name: {name}\n🏆 Score: {score}\n📖 Searches: {search_count}\n🔥 Streak: {streak}\n⭐ Feedback Score: {feedback_score}\n📅 Join Date: {join_date}\n👑 Title: {title}\n🎯 Visits: {visits}\n✅ Quests completed: {quests}\n🤝 Referrals: {referrals}\n💰 Referral earned: {referral_earned}",
        "about": "🌸 This bot is designed with love by the Quran & Etrat Center of Shiraz University of Medical Sciences.\n\n📚 Features:\n• Smart Islamic Search 🧠\n• AI Assistant 🤖\n• Voice Search 🎤\n• Hadith & Dhikr 🕊️\n• Instant Quran ✨\n• Scorecard & Quran League 🏆\n• Daily Receive 🔔\n• Suggestion & Critique ⭐\n• Daily Quests 🎯\n• Best Users 🏅\n• Referral System 🤝\n• Favorite Verses ❤️\n• Surveys 📝\n• Religious Reminders 🕌\n• Arabic Support 🇸🇦",
        "daily_enable": "✅ Daily receive enabled.",
        "daily_disable": "❌ Daily receive disabled.",
        "daily_toggle": "🔔 Daily Receive",
        "back_to_menu": "🏠 Back to main menu",
        "search_quran_prompt": "📖 Send a word or phrase to search.",
        "article_prompt": "📚 Send your article topic or keyword.",
        "league_text": "🏆 Quran League:\n\n{leaderboard}\n\n💡 To earn points:\n• Quran Search 📖\n• Send feedback 📝\n• Daily visit 🌅\n• Read Hadith 🕊️\n• Invite friends 🤝",
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
        "menu_labels": {
            "islamic_search": "🧠 Smart Search",
            "ai": "🤖 AI Assistant",
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
            "about": "ℹ️ About Bot",
            "help": "❓ Help",
            "share": "📤 Share",
            "reminder": "⏰ Reminder",
            "quests": "🎯 Daily Quests",
            "best_users": "🏅 Best Users",
            "referral": "🤝 Invite Friends",
            "favorites": "❤️ Favorite Verses",
            "faq": "❓ FAQ",
            "voice_search": "🎤 Voice Search",
            "profile": "✏️ Edit Profile"
        }
    },
    "ar": {
        "select_lang": "🌍 الرجاء اختيار لغتك:",
        "welcome": "مرحباً {name}! 😍\nمرحباً بك في بوت القرآن والعترة بجامعة علوم الطب شيراز.\nالرجاء اختيار خيار:",
        "force_join": "🌸 للاستفادة من خدمات البوت، الرجاء الانضمام إلى قناتنا أولاً:\n{channel}\n\nثم اضغط /start مرة أخرى.",
        "joined_success": "✅ تم تأكيد العضوية. مرحباً بك!",
        "not_joined_yet": "🥲 لم يتم تأكيد عضويتك بعد. الرجاء الانضمام أولاً.",
        "ai_prompt": "🤖 اسأل سؤالك، عزيزي!",
        "ai_wait": "⏳ الرجاء الانتظار... جاري التفكير!",
        "admin_msg_prompt": "📩 أرسل رسالتك وسأقوم بإرسالها إلى المشرف:",
        "admin_msg_sent": "✅ تم إرسال رسالتك إلى المشرف.",
        "under_construction": "🚧 هذا القسم قيد الإنشاء.",
        "stats": "📊 إحصائياتك:\n\n👤 الاسم: {name}\n🏆 النقاط: {score}\n📖 عمليات البحث: {search_count}\n🔥 الأيام المتتالية: {streak}\n⭐ نقاط الاقتراحات: {feedback_score}\n📅 تاريخ الانضمام: {join_date}\n👑 اللقب: {title}\n🎯 الزيارات: {visits}\n✅ المهام المنجزة: {quests}\n🤝 الدعوات: {referrals}\n💰 نقاط الدعوة: {referral_earned}",
        "about": "🌸 تم تصميم هذا البوت بحب من قبل مركز القرآن والعترة بجامعة علوم الطب شيراز.\n\n📚 الميزات:\n• البحث الإسلامي الذكي 🧠\n• المساعد الذكي 🤖\n• البحث الصوتي 🎤\n• الحديث والذكر اليومي 🕊️\n• القرآن في لحظة ✨\n• بطاقة النتائج والدوري القرآني 🏆\n• الاستلام اليومي 🔔\n• الاقتراحات والنقد ⭐\n• المهام اليومية 🎯\n• أفضل المستخدمين 🏅\n• نظام الدعوة 🤝\n• الآيات المفضلة ❤️\n• الاستطلاعات 📝\n• تذكير المناسبات 🕌\n• دعم اللغة العربية 🇸🇦",
        "daily_enable": "✅ تم تفعيل الاستلام اليومي.",
        "daily_disable": "❌ تم تعطيل الاستلام اليومي.",
        "daily_toggle": "🔔 الاستلام اليومي",
        "back_to_menu": "🏠 العودة إلى القائمة الرئيسية",
        "search_quran_prompt": "📖 أرسل كلمة أو عبارة للبحث.",
        "article_prompt": "📚 أرسل موضوع المقال أو الكلمة المفتاحية.",
        "league_text": "🏆 الدوري القرآني:\n\n{leaderboard}\n\n💡 لكسب النقاط:\n• البحث في القرآن 📖\n• إرسال اقتراح 📝\n• الزيارة اليومية 🌅\n• قراءة الحديث 🕊️\n• دعوة الأصدقاء 🤝",
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
        "menu_labels": {
            "islamic_search": "🧠 البحث الذكي",
            "ai": "🤖 المساعد الذكي",
            "hadith": "🕊️ الحديث والذكر اليومي",
            "instant_quran": "✨ القرآن في لحظة",
            "events": "📢 الفعاليات والمسابقات",
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
            "voice_search": "🎤 البحث الصوتي",
            "profile": "✏️ تعديل الملف الشخصي"
        }
    }
}

def safe_lang_dict(lang_code):
    """دریافت دیکشنری زبان با پشتیبانی از خطا"""
    return LANGS.get(lang_code, LANGS["fa"])

def safe_text(lang_code, key, default=None, **kwargs):
    """دریافت متن با پشتیبانی از جایگزینی و خطا"""
    lang_dict = safe_lang_dict(lang_code)
    text = lang_dict.get(key, default if default is not None else key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

# =========================================================
# ۴. داده‌های اولیه و نمونه (توسعه‌یافته با تفسیر)
# =========================================================
DEFAULT_QURAN_SEED = [
    {"index": 1, "surah": "حمد", "verse": 1, "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "trans": "به نام خداوند بخشنده مهربان", "interpretation": "شروع هر کار با نام خدا، نشانه توکل و ایمان است. برای پزشکان و دانشجویان علوم پزشکی، این آیه یادآور شروع هر اقدام درمانی با نام خداوند مهربان است.", "topics": ["ایمان", "توکل", "شروع", "بسم الله"]},
    {"index": 2, "surah": "حمد", "verse": 2, "text": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "trans": "ستایش مخصوص خداوندی است که پروردگار جهانیان است", "interpretation": "تمام هستی و از جمله علم پزشکی، نشانه‌های پروردگار جهانیان است. هر کشف علمی، ستایشی بر عظمت خالق است.", "topics": ["حمد", "ستایش", "خداوند", "جهانیان"]},
    {"index": 3, "surah": "حمد", "verse": 3, "text": "الرَّحْمَٰنِ الرَّحِيمِ", "trans": "بخشنده و مهربان است", "interpretation": "رحمانیت و رحیمیت خدا، الگوی پزشکان در مهربانی با بیماران است.", "topics": ["رحمت", "مهربانی", "بخشش"]},
    {"index": 4, "surah": "حمد", "verse": 4, "text": "مَالِكِ يَوْمِ الدِّينِ", "trans": "مالک روز جزاست", "interpretation": "روز جزا یادآور مسئولیت پزشکان در قبال جان انسان‌هاست.", "topics": ["جزا", "مسئولیت", "حسابرسی"]},
    {"index": 5, "surah": "حمد", "verse": 5, "text": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "trans": "تنها تو را می‌پرستیم و تنها از تو یاری می‌جوییم", "interpretation": "پزشکان و پرستاران در درمان بیماران، تنها به خداوند توکل کنند.", "topics": ["عبادت", "توکل", "یاری"]},
    {"index": 6, "surah": "بقره", "verse": 153, "text": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "trans": "ای کسانی که ایمان آورده‌اید، از صبر و نماز یاری جویید", "interpretation": "صبر در برابر سختی‌های درمان و نماز برای آرامش قلب، دو ابزار قدرتمند برای کادر درمان است.", "topics": ["صبر", "نماز", "یاری", "ایمان"]},
    {"index": 7, "surah": "بقره", "verse": 255, "text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ", "trans": "خداوند است که هیچ معبودی جز او نیست؛ زنده و پایدار است", "interpretation": "خداوند حی و قیوم، منشأ حیات و بقای تمام موجودات است.", "topics": ["توحید", "حیات", "بقا"]},
    {"index": 8, "surah": "بقره", "verse": 286, "text": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "trans": "خداوند هیچ‌کس را جز به اندازه توانش تکلیف نمی‌کند", "interpretation": "هیچ پزشک و پرستاری بیش از توانش مسئول نیست.", "topics": ["توان", "مسئولیت", "آرامش"]},
    {"index": 9, "surah": "آل عمران", "verse": 139, "text": "وَلَا تَهِنُوا وَلَا تَحْزَنُوا وَأَنْتُمُ الْأَعْلَوْنَ إِنْ كُنْتُمْ مُؤْمِنِينَ", "trans": "سست نشوید و غمگین نگردید، که اگر مؤمن باشید شما برترید", "interpretation": "کادر درمان با ایمان به خدا، هرگز سست و غمگین نشوند.", "topics": ["امید", "ایمان", "قدرت"]},
    {"index": 10, "surah": "رعد", "verse": 28, "text": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ", "trans": "آگاه باشید که با یاد خدا دل‌ها آرام می‌گیرد", "interpretation": "پزشکان و پرستاران در شرایط استرس‌زا، با یاد خدا آرامش می‌یابند.", "topics": ["آرامش", "یاد خدا", "استرس"]},
]

DEFAULT_NAHJ_SEED = [
    {"index": 1, "type": "خطبه", "number": 1, "text": "الْحَمْدُ لِلَّهِ الَّذِی لَا یَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ", "trans": "ستایش خدایی را که سخنوران در ستودن او فرومانند", "interpretation": "عظمت خداوند فراتر از توصیف است.", "topics": ["عظمت خدا", "ستایش"]},
    {"index": 2, "type": "حکمت", "number": 1, "text": "كُنْ فِي الْفِتْنَةِ كَابْنِ اللَّبُونِ لاَ ظَهْرٌ فَيُرْكَبَ، وَلاَ ضَرْعٌ فَيُحْلَبَ", "trans": "در فتنه‌ها چونان شتر دو ساله باش، نه پشتی دارد که سوار شوند و نه پستانی که بدوشند", "interpretation": "در بحران‌های پزشکی، متواضع باش و خود را از حاشیه‌ها دور نگهدار.", "topics": ["فتنه", "تواضع", "بحران"]},
    {"index": 3, "type": "نامه", "number": 31, "text": "يَا بُنَيَّ اجْعَلْ نَفْسَكَ مِيزَاناً فِيما بَيْنَكَ وَبَيْنَ غَيْرِكَ", "trans": "پسرم، خویشتن را میان خود و دیگران ترازویی قرار ده", "interpretation": "پزشکان باید در برخورد با بیماران، عدالت را رعایت کنند.", "topics": ["عدالت", "اخلاق", "رفتار"]},
]

DEFAULT_SAHIFEH_SEED = [
    {"index": 1, "dua": 1, "title": "در ستایش پروردگار", "text": "الْحَمْدُ لِلَّهِ الْأَوَّلِ بلا أَوَّلٍ كَانَ قَبْلَهُ", "trans": "ستایش خدای را که نخستین است و پیش از او نخستینی نبوده", "interpretation": "خداوند آغاز همه چیز است.", "topics": ["ستایش", "خدا", "آغاز"]},
    {"index": 2, "dua": 20, "title": "دعای مکارم الاخلاق", "text": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَ آلِهِ ، وَ بَلِّغْ بِإِیمَانِی أَکْمَلَ الْإِیمَانِ", "trans": "بار خدایا بر محمد و آلش درود فرست، و ایمان مرا به کامل‌ترین مرتبه ایمان برسان", "interpretation": "ایمان کامل، آرامش قلبی و قدرت معنوی به پزشکان می‌دهد.", "topics": ["ایمان", "آرامش", "کمال"]},
]

# =========================================================
# ۵. داده‌های موضوعات قرآن (موتور جستجوی معنایی)
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
    "شکر": {"synonyms": ["شکر", "سپاس", "قدردانی"], "keywords": ["شکر", "سپاس"]},
    "توبه": {"synonyms": ["توبه", "بازگشت", "استغفار"], "keywords": ["توبه", "استغفار"]},
    "علم": {"synonyms": ["علم", "دانش", "دانایی", "آگاهی"], "keywords": ["علم", "دانش", "آگاهی"]},
    "سلامتی": {"synonyms": ["سلامتی", "صحه", "تندرستی", "بهداشت"], "keywords": ["سلامتی", "بهداشت"]},
    "شفا": {"synonyms": ["شفا", "درمان", "بهبودی"], "keywords": ["شفا", "درمان"]},
}

# =========================================================
# ۶. احادیث و ذکر روزانه با منبع
# =========================================================
HADITHS_WITH_DHIKR = [
    {"hadith": "بهترین شما کسی است که قرآن را بیاموزد و به دیگران یاد دهد. 🌸", "source": "📚 صحیح بخاری، جلد ۶، صفحه ۵۰۲", "dhikr": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ (۱۰۰ بار)", "category": "آموزش", "topics": ["آموزش", "علم", "یادگیری"]},
    {"hadith": "در قرآن بیندیشید که بهار دل‌هاست. ✨", "source": "📚 نهج‌البلاغه، خطبه ۱۷۶", "dhikr": "لَا إِلَٰهَ إِلَّا اللَّهُ (۱۰۰ بار)", "category": "تفکر", "topics": ["تفکر", "آرامش", "قرآن"]},
    {"hadith": "قرآن عهد الهی با بندگان است؛ شایسته است هر روز در آن نظر شود. 📖", "source": "📚 بحارالانوار، جلد ۸۹، صفحه ۲۰۳", "dhikr": "اللَّهُ أَكْبَرُ (۱۰۰ بار)", "category": "تلاوت", "topics": ["تلاوت", "قرآن", "یاد خدا"]},
    {"hadith": "خانه‌هایتان را با تلاوت قرآن نورانی کنید. 🕯️", "source": "📚 مستدرک الوسائل، جلد ۴، صفحه ۲۴۲", "dhikr": "أَسْتَغْفِرُ اللَّهَ (۱۰۰ بار)", "category": "نورانی‌سازی", "topics": ["نور", "قرآن", "آرامش"]},
    {"hadith": "هر کس قرآن را با صدای بلند بخواند، خداوند به او اجر شهید می‌دهد. 🌹", "source": "📚 ثواب الاعمال، صفحه ۱۵۸", "dhikr": "سُبْحَانَ اللَّهِ وَالْحَمْدُ لِلَّهِ (۱۰۰ بار)", "category": "تلاوت", "topics": ["اجر", "شهادت", "قرآن"]},
    {"hadith": "مؤمنان در محبت و مهربانی مانند یک پیکرند. 💚", "source": "📚 صحیح مسلم، جلد ۴، صفحه ۶۵۴", "dhikr": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَآلِ مُحَمَّدٍ (۱۰۰ بار)", "category": "اخوت", "topics": ["مهربانی", "اخوت", "همدلی"]},
    {"hadith": "نیکی را به نیکی پاداش نیست، بلکه به احسان است. 🌟", "source": "📚 غررالحکم، جلد ۲، صفحه ۱۵", "dhikr": "سُبْحَانَ اللَّهِ الْعَظِیمِ (۱۰۰ بار)", "category": "اخلاق", "topics": ["نیکی", "احسان", "پاداش"]},
]

# =========================================================
# ۷. داده‌های مناسبت‌های مذهبی
# =========================================================
RELIGIOUS_OCCASIONS = {
    "نیمه شعبان": {"month": 8, "day": 15, "title": "🎉 ولادت امام زمان (عج)", "message": "🌹 ولادت با سعادت منجی عالم بشریت، امام زمان (عج) مبارک باد!"},
    "ماه رمضان": {"month": 9, "day": 1, "title": "🌙 حلول ماه رمضان", "message": "🌙 ماه رمضان، ماه رحمت و مغفرت بر شما مبارک باد!"},
    "عید فطر": {"month": 10, "day": 1, "title": "🎊 عید سعید فطر", "message": "🎊 عید سعید فطر، روز پاداش روزه‌داران مبارک باد!"},
    "عید قربان": {"month": 12, "day": 10, "title": "🎊 عید سعید قربان", "message": "🎊 عید سعید قربان، روز بندگی و ایثار مبارک باد!"},
    "محرم": {"month": 1, "day": 1, "title": "🖤 ماه محرم", "message": "🖤 ماه محرم، ماه عزاداری سالار شهیدان امام حسین (ع) بر شما تسلیت باد."},
    "عاشورا": {"month": 1, "day": 10, "title": "🖤 تاسوعا و عاشورا", "message": "🖤 تاسوعا و عاشورا، یادآور حماسه کربلا و شهادت امام حسین (ع) بر شما تسلیت باد."},
    "اربـعین": {"month": 2, "day": 20, "title": "🖤 اربعین حسینی", "message": "🖤 اربعین حسینی، روز تجدید میثاق با امام حسین (ع) بر شما تسلیت باد."},
}

# =========================================================
# ۸. احادیث نقل قول روز از نهج‌البلاغه
# =========================================================
NAHJ_QUOTES = [
    {"text": "العلم خیر من المال، العلم یحرسک و انت تحرس المال", "trans": "علم بهتر از مال است، علم از تو نگهبانی می‌کند و تو از مال نگهبانی می‌کنی", "source": "📚 نهج‌البلاغه، حکمت ۱۵"},
    {"text": "الصبر مفتاح الفرج", "trans": "صبر کلید گشایش است", "source": "📚 نهج‌البلاغه، حکمت ۴۰"},
    {"text": "قیمة کل امرء ما یحسنه", "trans": "ارزش هر کس به اندازه چیزی است که خوب انجام می‌دهد", "source": "📚 نهج‌البلاغه، حکمت ۸۱"},
    {"text": "من کثر کلامه کثر خطؤه", "trans": "هر که سخنش بسیار شود، خطایش بسیار می‌شود", "source": "📚 نهج‌البلاغه، حکمت ۷۱"},
    {"text": "العزلة عن اهل السوء خیر من مجالسة اهل الخیر", "trans": "تنهایی از اهل بد بهتر از همنشینی با اهل خوب است", "source": "📚 نهج‌البلاغه، حکمت ۱۰۰"},
]

# =========================================================
# ۹. پیام‌های انگیزشی
# =========================================================
MOTIVATIONAL_MESSAGES = [
    "🌸 هر روز با قرآن، هر روز با نور!",
    "💚 با یاد خدا، دلها آرام می‌گیرد.",
    "🌟 تو می‌توانی! به خدا توکل کن و قدم بردار.",
    "🌺 قرآن را بخوان، که بهار دل‌هاست.",
    "🍃 صبر کن، که خداوند با صابران است.",
    "🕊️ در سختی‌ها، یاد خدا باش که آرامش‌بخش است.",
    "🌙 ماه مبارک رمضان، فرصت طلایی برای خودسازی.",
    "💪 با ایمان و تلاش، می‌توانی به قله‌های موفقیت برسی.",
    "🌹 هر روز یک شروع جدید برای بهتر شدن است.",
    "✨ به امید خدا، همه چیز ممکن است.",
]

INSTANT_QURAN_FULL = [
    {"surah": "الرحمن", "verse": 60, "arabic": "هَلْ جَزَاءُ الْإِحْسَانِ إِلَّا الْإِحْسَانُ", "trans": "آیا پاداش نیکی جز نیکی است؟"},
    {"surah": "الضحی", "verse": 1, "arabic": "وَالضُّحَىٰ", "trans": "سوگند به روشنایی روز"},
    {"surah": "الشرح", "verse": 5, "arabic": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا", "trans": "پس یقیناً با دشواری آسانی است"},
    {"surah": "التين", "verse": 1, "arabic": "وَالتِّينِ وَالزَّيْتُونِ", "trans": "سوگند به انجیر و زیتون"},
    {"surah": "العلق", "verse": 1, "arabic": "اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ", "trans": "بخوان به نام پروردگارت که آفرید"},
    {"surah": "القدر", "verse": 1, "arabic": "إِنَّا أَنزَلْنَاهُ فِي لَيْلَةِ الْقَدْرِ", "trans": "ما آن را در شب قدر نازل کردیم"},
    {"surah": "البقره", "verse": 286, "arabic": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "trans": "خداوند هیچ‌کس را جز به اندازه توانش تکلیف نمی‌کند"},
]

# =========================================================
# ۱۰. جوایز و عناوین کاربران
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
    "🌱 تازه‌کار قرآنی": "شروع راه نورانی! با فعالیت‌های روزانه امتیاز جمع کن.",
    "📖 قرآن‌خوان مبتدی": "قدم اول رو برداشتی! به راهت ادامه بده.",
    "🌟 نورانی": "نور قرآن در دلت روشن شده!",
    "💎 حافظ قرآن": "به جمع حافظان قرآن پیوستی!",
    "🕊️ عاشق قرآن": "عشق به قرآن در دلت جای گرفته!",
    "🔥 مجتهد قرآنی": "تلاش و کوشش تو ستودنی است!",
    "👑 سلطان قرآن": "تو یک سلطان در دنیای قرآن هستی!",
    "🌹 پیشوای قرآنی": "تو الگوی دیگران در مسیر قرآن هستی!"
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
    "referrer_gold": {"name": "🥇 دعوت‌کننده طلایی", "points": 100}
}

# =========================================================
# ۱۱. دکمه‌های جذاب برای کسب امتیاز
# =========================================================
QUEST_ACTIONS = [
    {"id": "quran_search", "label": "📖 جستجوی قرآن", "points": 3, "desc": "هر بار جستجو در قرآن"},
    {"id": "daily_visit", "label": "🌅 بازدید روزانه", "points": 5, "desc": "هر روز از ربات بازدید کن"},
    {"id": "feedback", "label": "📝 ارسال پیشنهاد", "points": 5, "desc": "پیشنهاد سازنده بده"},
    {"id": "hadith_read", "label": "🕊️ مطالعه حدیث", "points": 2, "desc": "حدیث روزانه را بخوان"},
    {"id": "instant_quran", "label": "✨ قرآن در لحظه", "points": 2, "desc": "آیه لحظه را دریافت کن"},
    {"id": "streak_7", "label": "🔥 ۷ روز پیاپی", "points": 15, "desc": "هفت روز متوالی بازدید کن"},
    {"id": "streak_30", "label": "⭐ ۳۰ روز پیاپی", "points": 30, "desc": "سی روز متوالی بازدید کن"},
    {"id": "referral", "label": "🤝 دعوت از دوستان", "points": 10, "desc": "هر دعوت ۱۰ امتیاز برای شما و دوستتان"},
]

# =========================================================
# ۱۲. توابع راه‌اندازی و مدیریت فایل‌های JSON
# =========================================================
def ensure_library_files():
    """ایجاد فایل‌های کتابخانه در صورت عدم وجود"""
    files_to_create = [
        (QURAN_FILE, DEFAULT_QURAN_SEED),
        (NAHJ_FILE, DEFAULT_NAHJ_SEED),
        (SAHIFEH_FILE, DEFAULT_SAHIFEH_SEED),
        (ARTICLES_FILE, {}),
        (TOPICS_FILE, DEFAULT_TOPICS),
        (FAVORITES_FILE, {}),
        (SURVEYS_FILE, {})
    ]
    
    for file_path, default_data in files_to_create:
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
                logger.info(f"📁 فایل {file_path} ایجاد شد.")
            except Exception as e:
                logger.error(f"خطا در ایجاد فایل {file_path}: {e}")
    
    # ایجاد دایرکتوری بک‌آپ
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def load_library():
    """بارگذاری تمام کتابخانه‌ها"""
    global QURAN_DATA, NAHJ_DATA, SAHIFEH_DATA, ARTICLE_CACHE, TOPICS_DATA, FAVORITES_DATA, SURVEYS_DATA
    
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
            
        logger.info(f"📚 کتابخانه بارگذاری شد: قرآن={len(QURAN_DATA)}, نهج={len(NAHJ_DATA)}, صحیفه={len(SAHIFEH_DATA)}, موضوعات={len(TOPICS_DATA)}")
        
        # اگر دیتا خالی بود، با دیتای نمونه پر کن
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
            
    except Exception as e:
        logger.error(f"خطا در بارگذاری فایل‌های کتابخانه: {e}")
        # استفاده از داده‌های پیش‌فرض در صورت خطا
        QURAN_DATA = DEFAULT_QURAN_SEED
        NAHJ_DATA = DEFAULT_NAHJ_SEED
        SAHIFEH_DATA = DEFAULT_SAHIFEH_SEED
        TOPICS_DATA = DEFAULT_TOPICS

def save_library_file(file_path, data):
    """ذخیره داده‌ها در فایل"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"خطا در ذخیره {file_path}: {e}")
        return False

# =========================================================
# ۱۳. سیستم بک‌آپ خودکار
# =========================================================
def auto_backup():
    """انجام بک‌آپ خودکار از دیتابیس و فایل‌ها"""
    if not FEATURES["auto_backup"]:
        return
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
        os.makedirs(backup_folder, exist_ok=True)
        
        # بک‌آپ دیتابیس
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, os.path.join(backup_folder, "bot_data.db"))
        
        # بک‌آپ فایل‌های JSON
        json_files = [QURAN_FILE, NAHJ_FILE, SAHIFEH_FILE, ARTICLES_FILE, TOPICS_FILE, FAVORITES_FILE, SURVEYS_FILE]
        for file in json_files:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(backup_folder, file))
        
        # بک‌آپ لاگ
        if os.path.exists("bot.log"):
            shutil.copy2("bot.log", os.path.join(backup_folder, "bot.log"))
        
        # پاکسازی بک‌آپ‌های قدیمی (فقط ۷ روز اخیر)
        backups = sorted([d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))])
        for backup in backups[:-7]:  # نگهداری ۷ بک‌آپ آخر
            shutil.rmtree(os.path.join(BACKUP_DIR, backup))
        
        logger.info(f"✅ بک‌آپ خودکار در {backup_folder} انجام شد.")
    except Exception as e:
        logger.error(f"خطا در بک‌آپ خودکار: {e}")

def backup_scheduler():
    """اسکجولر بک‌آپ - هر روز ساعت ۳ بامداد"""
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
# ۱۴. سیستم نظرسنجی و رای‌گیری
# =========================================================
def create_survey(question, options, created_by):
    """ایجاد نظرسنجی جدید"""
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
    """رأی دادن به نظرسنجی"""
    if survey_id not in SURVEYS_DATA:
        return False, "نظرسنجی وجود ندارد."
    
    survey = SURVEYS_DATA[survey_id]
    if not survey["active"]:
        return False, "این نظرسنجی به پایان رسیده است."
    
    if option not in survey["options"]:
        return False, "گزینه نامعتبر است."
    
    # بررسی اینکه کاربر قبلاً رأی داده است
    for opt, voters in survey["votes"].items():
        if user_id in voters:
            return False, "شما قبلاً در این نظرسنجی رأی داده‌اید."
    
    survey["votes"][option].append(user_id)
    save_library_file(SURVEYS_FILE, SURVEYS_DATA)
    return True, "رأی شما با موفقیت ثبت شد."

def get_survey_results(survey_id):
    """دریافت نتایج نظرسنجی"""
    if survey_id not in SURVEYS_DATA:
        return None
    
    survey = SURVEYS_DATA[survey_id]
    total_votes = sum(len(voters) for voters in survey["votes"].values())
    results = []
    for option, voters in survey["votes"].items():
        percentage = (len(voters) / total_votes * 100) if total_votes > 0 else 0
        results.append({
            "option": option,
            "votes": len(voters),
            "percentage": round(percentage, 1)
        })
    return {
        "question": survey["question"],
        "total_votes": total_votes,
        "results": results,
        "active": survey["active"]
    }

# =========================================================
# ۱۵. سیستم ذخیره آیات مورد علاقه
# =========================================================
def add_favorite(user_id, verse_data):
    """افزودن آیه به علاقه‌مندی‌ها"""
    user_id = str(user_id)
    if user_id not in FAVORITES_DATA:
        FAVORITES_DATA[user_id] = []
    
    # جلوگیری از تکراری
    for item in FAVORITES_DATA[user_id]:
        if item.get("index") == verse_data.get("index"):
            return False, "این آیه قبلاً در علاقه‌مندی‌های شما ذخیره شده است."
    
    FAVORITES_DATA[user_id].append(verse_data)
    save_library_file(FAVORITES_FILE, FAVORITES_DATA)
    return True, "آیه با موفقیت به علاقه‌مندی‌ها اضافه شد. ❤️"

def get_favorites(user_id):
    """دریافت لیست علاقه‌مندی‌های کاربر"""
    user_id = str(user_id)
    return FAVORITES_DATA.get(user_id, [])

def remove_favorite(user_id, index):
    """حذف آیه از علاقه‌مندی‌ها"""
    user_id = str(user_id)
    if user_id not in FAVORITES_DATA:
        return False, "هیچ آیۀ ذخیره‌ای ندارید."
    
    original_len = len(FAVORITES_DATA[user_id])
    FAVORITES_DATA[user_id] = [item for item in FAVORITES_DATA[user_id] if item.get("index") != index]
    
    if len(FAVORITES_DATA[user_id]) == original_len:
        return False, "این آیه در علاقه‌مندی‌های شما وجود ندارد."
    
    save_library_file(FAVORITES_FILE, FAVORITES_DATA)
    return True, "آیه با موفقیت از علاقه‌مندی‌ها حذف شد. 💔"

# =========================================================
# ۱۶. سیستم جستجوی صوتی (شبیه‌سازی)
# =========================================================
def voice_to_text(audio_file):
    """تبدیل صوت به متن (شبیه‌سازی - در واقعیت نیاز به API دارد)"""
    # در نسخه واقعی باید از Google Speech API یا Azure Speech استفاده کرد
    # اینجا فقط یک شبیه‌سازی است
    return "این یک متن نمونه از جستجوی صوتی است"

# =========================================================
# ۱۷. توابع تاریخ شمسی
# =========================================================
def get_persian_date():
    """دریافت تاریخ شمسی با اعداد فارسی"""
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

def to_persian_numbers(text):
    """تبدیل اعداد انگلیسی به فارسی"""
    persian_numbers = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    for eng, per in persian_numbers.items():
        text = text.replace(eng, per)
    return text

def get_persian_greeting():
    """دریافت سلام به فارسی با تاریخ شمسی"""
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
    """دریافت سلام بر اساس زبان"""
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
# ۱۸. جستجوی اینترنتی واقعی
# =========================================================
def internet_search(query, lang="fa"):
    """جستجوی واقعی از اینترنت با استفاده از چند منبع"""
    if not FEATURES["internet_search"]:
        return []
    
    results = []
    
    # ۱. تلاش با Google Custom Search API
    if GOOGLE_API_KEY and GOOGLE_CX_ID:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_CX_ID,
                "q": query,
                "num": 5
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", [])[:5]:
                    results.append({
                        "title": item.get("title", "بدون عنوان"),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", ""),
                        "source": "Google"
                    })
        except Exception as e:
            logger.error(f"خطا در جستجوی گوگل: {e}")
    
    # ۲. تلاش با SerpAPI
    if SERP_API_KEY and not results:
        try:
            url = "https://serpapi.com/search"
            params = {
                "api_key": SERP_API_KEY,
                "q": query,
                "num": 5,
                "hl": "fa" if lang == "fa" else "en"
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("organic_results", [])[:5]:
                    results.append({
                        "title": item.get("title", "بدون عنوان"),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", ""),
                        "source": "SerpAPI"
                    })
        except Exception as e:
            logger.error(f"خطا در جستجوی SerpAPI: {e}")
    
    # ۳. تلاش با OpenAlex برای مقالات علمی
    if not results:
        try:
            url = f"https://api.openalex.org/works?search={query.replace(' ', '+')}&per-page=5"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for work in data.get("results", [])[:5]:
                    title = work.get("title", "بدون عنوان")
                    doi = work.get("doi", "")
                    link = f"https://doi.org/{doi}" if doi else ""
                    results.append({
                        "title": title,
                        "snippet": work.get("abstract", "")[:200],
                        "link": link,
                        "source": "OpenAlex"
                    })
        except Exception as e:
            logger.error(f"خطا در جستجوی OpenAlex: {e}")
    
    return results

# =========================================================
# ۱۹. موتور جستجوی هوشمند اسلامی (ادغام شده با جستجوی اینترنتی)
# =========================================================
def expand_topic(query):
    """توسعه موضوع با مترادف‌ها و کلمات کلیدی و تطابق فازی"""
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

def advanced_search(query, lang="fa"):
    """جستجوی پیشرفته در تمام منابع اسلامی + اینترنت"""
    if not FEATURES["islamic_knowledge_engine"]:
        return None
    
    cache_key = hashlib.md5(f"{query}_{lang}".encode()).hexdigest()
    if cache_key in SEARCH_CACHE:
        logger.info(f"جستجو از کش: {query}")
        return SEARCH_CACHE[cache_key]
    
    expanded_terms = expand_topic(query)
    results = {
        "quran": [],
        "nahj": [],
        "sahifeh": [],
        "hadith": [],
        "articles": [],
        "internet": []
    }
    
    # جستجو در قرآن
    for item in QURAN_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("surah", "")),
            str(item.get("interpretation", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
        for term in expanded_terms:
            if term in search_text:
                results["quran"].append(item)
                break
    
    # جستجو در نهج‌البلاغه
    for item in NAHJ_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("type", "")),
            str(item.get("interpretation", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
        for term in expanded_terms:
            if term in search_text:
                results["nahj"].append(item)
                break
    
    # جستجو در صحیفه سجادیه
    for item in SAHIFEH_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("title", "")),
            str(item.get("interpretation", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
        for term in expanded_terms:
            if term in search_text:
                results["sahifeh"].append(item)
                break
    
    # جستجو در احادیث
    for item in HADITHS_WITH_DHIKR:
        search_text = " ".join([
            str(item.get("hadith", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
        for term in expanded_terms:
            if term in search_text:
                results["hadith"].append(item)
                break
    
    # جستجوی اینترنتی برای مقالات
    if FEATURES["internet_search"]:
        internet_results = internet_search(query, lang)
        for item in internet_results:
            results["articles"].append({
                "title": item.get("title", ""),
                "summary": item.get("snippet", ""),
                "link": item.get("link", ""),
                "source": item.get("source", ""),
                "category": "اینترنتی"
            })
    
    # محدود کردن نتایج
    results["quran"] = results["quran"][:5]
    results["nahj"] = results["nahj"][:3]
    results["sahifeh"] = results["sahifeh"][:3]
    results["hadith"] = results["hadith"][:3]
    results["articles"] = results["articles"][:5]
    
    SEARCH_CACHE[cache_key] = results
    return results

def format_advanced_results(results, query, lang="fa"):
    """فرمت‌بندی نتایج جستجوی پیشرفته"""
    if not results:
        return f"🔍 نتیجه‌ای برای «{query}» یافت نشد.\n\n💡 سعی کنید با کلمات کلیدی دیگری جستجو کنید."
    
    has_results = False
    output = f"🧠 <b>موتور جستجوی هوشمند اسلامی - «{query}»</b>\n{'='*50}\n\n"
    
    # قرآن
    if results.get("quran"):
        has_results = True
        output += "📖 <b>آیات مرتبط در قرآن:</b>\n\n"
        for i, item in enumerate(results["quran"][:5], 1):
            output += f"{i}. <b>{item['surah']} (آیه {item['verse']})</b>\n"
            output += f"   {item['text']}\n"
            output += f"   ✨ {item['trans']}\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation']}\n"
            output += "\n"
    
    # نهج‌البلاغه
    if results.get("nahj"):
        has_results = True
        output += "📜 <b>فرازهایی از نهج‌البلاغه:</b>\n\n"
        for i, item in enumerate(results["nahj"][:3], 1):
            output += f"{i}. <b>{item['type']} {item['number']}</b>\n"
            output += f"   {item['text']}\n"
            output += f"   ✨ {item['trans']}\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation']}\n"
            output += "\n"
    
    # صحیفه سجادیه
    if results.get("sahifeh"):
        has_results = True
        output += "🤲 <b>دعاهایی از صحیفه سجادیه:</b>\n\n"
        for i, item in enumerate(results["sahifeh"][:3], 1):
            output += f"{i}. <b>{item['title']}</b>\n"
            output += f"   {item['text']}\n"
            output += f"   ✨ {item['trans']}\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation']}\n"
            output += "\n"
    
    # احادیث
    if results.get("hadith"):
        has_results = True
        output += "🕊️ <b>احادیث مرتبط:</b>\n\n"
        for i, item in enumerate(results["hadith"][:3], 1):
            output += f"{i}. {item['hadith']}\n"
            output += f"   🔹 ذکر: {item['dhikr']}\n"
            output += f"   🏷️ دسته: {item['category']}\n\n"
    
    # مقالات
    if results.get("articles"):
        has_results = True
        output += "📚 <b>مقالات مرتبط:</b>\n\n"
        for i, item in enumerate(results["articles"][:5], 1):
            output += f"{i}. <b>{item.get('title', 'بدون عنوان')}</b>\n"
            if item.get('summary'):
                output += f"   📝 {item.get('summary', '')[:150]}...\n"
            if item.get('link'):
                output += f"   🔗 <a href='{item['link']}'>لینک</a>\n"
            if item.get('source'):
                output += f"   📌 منبع: {item['source']}\n"
            output += "\n"
    
    if not has_results:
        return f"🔍 نتیجه‌ای برای «{query}» یافت نشد.\n\n💡 سعی کنید با کلمات کلیدی دیگری جستجو کنید."
    
    output += "💡 <b>پیشنهاد:</b> برای دریافت تحلیل عمیق‌تر، از بخش «هوش مصنوعی» استفاده کنید."
    return output

# =========================================================
# ۲۰. جستجوی ساده قرآن
# =========================================================
def search_quran_only(q):
    """جستجو در قرآن با مدیریت خطا و بازگشت تفسیر"""
    if not FEATURES["quran_search"]:
        return []
    
    q = q.strip().lower()
    if not q or len(q) < 2:
        return []

    results = []
    for item in QURAN_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("surah", "")),
            str(item.get("interpretation", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
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
    """جستجو در نهج‌البلاغه و صحیفه سجادیه با تفسیر"""
    q = q.strip().lower()
    if not q or len(q) < 2:
        return []

    results = []
    
    for item in NAHJ_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("type", "")),
            str(item.get("interpretation", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
        if q in search_text:
            item["book_type"] = "نهج‌البلاغه"
            results.append(item)
    
    for item in SAHIFEH_DATA:
        search_text = " ".join([
            str(item.get("text", "")),
            str(item.get("trans", "")),
            str(item.get("title", "")),
            str(item.get("interpretation", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
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
    """فرمت‌بندی نتایج جستجو با تفسیر"""
    if book_name == "قرآن":
        return f"""📖 <b>{item['surah']} (آیه {item['verse']})</b>
{item['text']}
✨ {item['trans']}
💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}
🏷️ <b>موضوعات:</b> {', '.join(item.get('topics', ['عمومی']))}"""
    elif book_name == "نهج‌البلاغه":
        return f"""📜 <b>{item['type']} {item['number']}</b>
{item['text']}
✨ {item['trans']}
💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}
🏷️ <b>موضوعات:</b> {', '.join(item.get('topics', ['عمومی']))}"""
    elif book_name == "صحیفه سجادیه":
        return f"""🤲 <b>{item['title']} (دعای {item['dua']})</b>
{item['text']}
✨ {item['trans']}
💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}
🏷️ <b>موضوعات:</b> {', '.join(item.get('topics', ['عمومی']))}"""
    return f"📚 <b>{item.get('title', '')}</b>\n{item['text']}\n✨ {item['trans']}\n💡 <b>تفسیر:</b> {item.get('interpretation', 'تفسیر ثبت نشده')}"

# =========================================================
# ۲۱. سیستم پاداش و امتیازدهی هوشمند
# =========================================================
def calculate_reward(action, user_data):
    """محاسبه امتیاز بر اساس نوع فعالیت"""
    if not FEATURES["smart_rewards"]:
        return 0, "🌱"
    
    rewards = {
        "quran_search": {"points": 3, "emoji": "📖"},
        "daily_visit": {"points": 5, "emoji": "🌅"},
        "feedback": {"points": 5, "emoji": "⭐"},
        "hadith_read": {"points": 2, "emoji": "🕊️"},
        "instant_quran": {"points": 2, "emoji": "✨"},
        "streak_bonus": {"points": 15, "emoji": "🔥"},
        "feedback_high_score": {"points": 10, "emoji": "💎"},
        "quest_complete": {"points": 5, "emoji": "🎯"},
        "referral_bonus": {"points": 10, "emoji": "🤝"},
        "advanced_search": {"points": 5, "emoji": "🧠"}
    }
    
    reward = rewards.get(action, {"points": 1, "emoji": "🌸"})
    points = reward["points"]
    emoji = reward["emoji"]
    
    if user_data.get("streak", 0) >= 7:
        points += 5
        emoji = "🔥"
    
    return points, emoji

def update_user_score(chat_id, action, user_data):
    """به‌روزرسانی امتیاز کاربر با اعمال پاداش"""
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
    """دریافت عنوان کاربر بر اساس امتیاز"""
    if not FEATURES["user_titles"]:
        return "🌱 کاربر قرآنی"
    
    titles = sorted(USER_TITLES.items(), reverse=True)
    for threshold, title in titles:
        if score >= threshold:
            return title
    return "🌱 کاربر قرآنی"

def get_user_title_description(title):
    """دریافت توضیحات عنوان کاربر"""
    return USER_TITLE_DESCRIPTIONS.get(title, "در مسیر رشد و تعالی قرآنی قدم بردار!")

def check_achievements(chat_id, action, user_data):
    """بررسی و ثبت دستاوردهای جدید"""
    if not FEATURES["achievement_system"]:
        return
    
    achievements = []
    score = user_data.get("score", 0)
    streak = user_data.get("streak", 0)
    feedback_score = user_data.get("feedback_score", 0)
    search_count = user_data.get("search_count", 0)
    referral_count = user_data.get("referral_count", 0)
    
    if action == "quran_search" and search_count >= 1:
        achievements.append("first_search")
    if action == "daily_visit" and user_data.get("daily_visit_count", 0) >= 1:
        achievements.append("daily_visitor")
    if action == "feedback" and feedback_score >= 10:
        achievements.append("feedback_master")
    if action == "quran_search" and score >= 50:
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
    if action == "advanced_search":
        achievements.append("knowledge_seeker")
    
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
            logger.info(f"دستاورد جدید برای کاربر {chat_id}: {achievement_key}")
        except Exception as e:
            logger.error(f"خطا در ثبت دستاورد {achievement_key}: {e}")

def get_user_achievements(chat_id):
    """دریافت لیست دستاوردهای کاربر"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT achievement_key, unlocked_at 
            FROM user_achievements 
            WHERE user_id = ?
            ORDER BY unlocked_at DESC
        """, (chat_id,))
        rows = cur.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            achievement = ACHIEVEMENTS.get(row[0])
            if achievement:
                results.append({
                    "name": achievement["name"],
                    "points": achievement["points"],
                    "unlocked_at": row[1]
                })
        return results
    except Exception as e:
        logger.error(f"خطا در دریافت دستاوردهای کاربر {chat_id}: {e}")
        return []

# =========================================================
# ۲۲. سیستم کوئست‌های روزانه
# =========================================================
def complete_quest(chat_id, quest_id, user_data):
    """انجام کوئست و دریافت امتیاز"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM user_quests 
            WHERE user_id = ? AND quest_id = ? 
            AND completed_at > datetime('now', '-1 day')
        """, (chat_id, quest_id))
        existing = cur.fetchone()
        
        if existing:
            conn.close()
            return False, "قبلاً این کوئست را امروز انجام داده‌اید! 🌸"
        
        cur.execute("""
            INSERT INTO user_quests (user_id, quest_id, completed_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (chat_id, quest_id))
        conn.commit()
        conn.close()
        
        quest = next((q for q in QUEST_ACTIONS if q["id"] == quest_id), None)
        if quest:
            update_user(chat_id, score=quest["points"], total_quests_completed=1)
            update_user(chat_id, last_quest_date=datetime.now().date().isoformat())
            return True, f"🎯 کوئست «{quest['label']}» انجام شد!\n🌟 {quest['points']} امتیاز دریافت کردی!"
        
        return True, "🎯 کوئست انجام شد! 🌟"
    except Exception as e:
        logger.error(f"خطا در انجام کوئست {quest_id}: {e}")
        return False, "⚠️ خطا در انجام کوئست. لطفاً دوباره تلاش کنید."

def get_quests_status(chat_id):
    """دریافت وضعیت کوئست‌های روزانه"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT quest_id FROM user_quests 
            WHERE user_id = ? 
            AND completed_at > datetime('now', '-1 day')
        """, (chat_id,))
        completed = [row[0] for row in cur.fetchall()]
        conn.close()
        
        status = []
        for quest in QUEST_ACTIONS:
            is_completed = quest["id"] in completed
            status.append({
                "id": quest["id"],
                "label": quest["label"],
                "points": quest["points"],
                "desc": quest["desc"],
                "completed": is_completed
            })
        return status
    except Exception as e:
        logger.error(f"خطا در دریافت وضعیت کوئست‌ها: {e}")
        return []

# =========================================================
# ۲۳. سیستم بهترین کاربر روز و هفته (واقعی)
# =========================================================
def get_best_user_real(period_type):
    """دریافت بهترین کاربر واقعی روز یا هفته"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        
        if period_type == "daily":
            today = datetime.now().date().isoformat()
            cur.execute("""
                SELECT chat_id, name, score 
                FROM users 
                WHERE last_active > datetime('now', '-1 day')
                ORDER BY score DESC 
                LIMIT 1
            """)
        else:
            cur.execute("""
                SELECT chat_id, name, score 
                FROM users 
                WHERE last_active > datetime('now', '-7 days')
                ORDER BY score DESC 
                LIMIT 1
            """)
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                "user_id": row[0],
                "user_name": row[1] or "کاربر ناشناس",
                "score": row[2] or 0,
                "date": datetime.now().date().isoformat()
            }
        
        return None
    except Exception as e:
        logger.error(f"خطا در دریافت بهترین کاربر: {e}")
        return None

def save_best_user_real(period_type):
    """ذخیره بهترین کاربر واقعی روز یا هفته"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        
        if period_type == "daily":
            cur.execute("""
                SELECT chat_id, name, score 
                FROM users 
                WHERE last_active > datetime('now', '-1 day')
                ORDER BY score DESC 
                LIMIT 1
            """)
        else:
            cur.execute("""
                SELECT chat_id, name, score 
                FROM users 
                WHERE last_active > datetime('now', '-7 days')
                ORDER BY score DESC 
                LIMIT 1
            """)
        
        user = cur.fetchone()
        
        if user:
            chat_id, name, score = user
            period_date = datetime.now().date().isoformat()
            
            cur.execute("""
                INSERT INTO best_users (user_id, user_name, score, period_type, period_date, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (chat_id, name, score, period_type, period_date))
            
            conn.commit()
            
            if period_type == "daily":
                message = f"""🏅 <b>بهترین کاربر روز</b>

🌟 کاربر: {name}
🏆 امتیاز: {score}
📅 تاریخ: {period_date}

💚 تبریک به این عزیز! 🌸
🕌 ادامه بده تا همیشه در مسیر نور باشی."""
            else:
                message = f"""🏆 <b>بهترین کاربر هفته</b>

🌟 کاربر: {name}
🏆 امتیاز: {score}
📅 هفته: {period_date}

💚 تبریک ویژه به این عزیز! 🌸
🕌 با تلاش خود الگوی دیگران باش."""
            
            send_message(CHANNEL_ID, message)
            logger.info(f"بهترین کاربر واقعی {period_type} ذخیره شد: {name} با {score} امتیاز")
        
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره بهترین کاربر: {e}")

def schedule_best_users():
    """برنامه‌ریزی برای ثبت بهترین کاربران واقعی"""
    while True:
        try:
            now = datetime.now()
            
            if now.hour == 23 and now.minute == 59 and FEATURES["best_user_daily"]:
                save_best_user_real("daily")
                logger.info("بهترین کاربر روز واقعی ثبت شد.")
                time.sleep(60)
            
            if now.weekday() == 4 and now.hour == 23 and now.minute == 59 and FEATURES["best_user_weekly"]:
                save_best_user_real("weekly")
                logger.info("بهترین کاربر هفته واقعی ثبت شد.")
                time.sleep(60)
            
            time.sleep(30)
        except Exception as e:
            logger.error(f"خطا در برنامه‌ریزی بهترین کاربران: {e}")
            time.sleep(60)

# =========================================================
# ۲۴. سیستم ارسال روزانه
# =========================================================
def send_daily_posts():
    """ارسال محتوای روزانه در ۳ زمان مشخص"""
    try:
        if not FEATURES["daily_posts"]:
            return
        
        now = datetime.now()
        
        scheduled_times = [
            (8, 0, "صبح 🌅"),
            (12, 0, "ظهر ☀️"),
            (18, 0, "عصر 🌇")
        ]
        
        for hour, minute, time_name in scheduled_times:
            if now.hour == hour and 0 <= now.minute <= 2:
                if now.minute != 0:
                    time.sleep(1)
                    continue
                
                logger.info(f"🔄 شروع ارسال پست روزانه - {time_name}")
                
                # ۱. آیه روز از قرآن با تفسیر
                q_item, q_idx = next_item("quran", QURAN_DATA)
                q_msg = ""
                if q_item:
                    interpretation = q_item.get('interpretation', 'تفسیر: این آیه یادآور اهمیت ایمان و عمل صالح است.')
                    topics = ', '.join(q_item.get('topics', ['عمومی']))
                    
                    q_msg = f"""📘 <b>آیه منتخب روز</b>

سوره {q_item['surah']} - آیه {q_item['verse']}

{q_item['text']}

🔹 ترجمه:
{q_item['trans']}

💡 <b>تفسیر:</b> {interpretation}

🏷️ <b>موضوعات:</b> {topics}"""
                    
                    send_message(CHANNEL_ID, q_msg)
                    set_publish_index("quran", q_idx)
                    save_sent_message("daily_quran", q_msg, CHANNEL_ID)
                    logger.info(f"آیه روزانه با تفسیر ارسال شد - {time_name}")
                    time.sleep(2)
                
                # ۲. حدیث روز با منبع
                hadith_item = random.choice(HADITHS_WITH_DHIKR)
                hadith_msg = f"""🕊️ <b>حدیث روز</b>

{hadith_item['hadith']}

📚 <b>منبع:</b> {hadith_item['source']}

🔹 <b>ذکر روزانه:</b>
{hadith_item['dhikr']}

🏷️ دسته: {hadith_item['category']}

💚 با یاد خدا دل‌ها آرام می‌گیرد."""
                
                send_message(CHANNEL_ID, hadith_msg)
                save_sent_message("daily_hadith", hadith_msg, CHANNEL_ID)
                logger.info(f"حدیث روزانه ارسال شد - {time_name}")
                time.sleep(2)
                
                # ۳. نقل قول روز از نهج‌البلاغه
                nahj_quote = random.choice(NAHJ_QUOTES)
                nahj_msg = f"""📜 <b>نقل قول روز از نهج‌البلاغه</b>

{nahj_quote['text']}

✨ {nahj_quote['trans']}

📚 {nahj_quote['source']}

💡 با حکمت‌های امیرالمؤمنین علی (ع) زندگی را زیباتر کن."""
                
                send_message(CHANNEL_ID, nahj_msg)
                save_sent_message("daily_nahj", nahj_msg, CHANNEL_ID)
                logger.info(f"نقل قول از نهج‌البلاغه ارسال شد - {time_name}")
                time.sleep(2)
                
                # ۴. ارسال به کاربرانی که دریافت روزانه فعال دارند
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
                            greeting = safe_text(user_lang, "daily_greeting", default="🌸 پیام روزانه")
                            
                            daily_msg = f"""🌟 <b>{greeting} کانون قرآن و عترت</b>

{q_msg if q_msg else '📖 با قرآن زندگی کن'}

{hadith_msg}

{nahj_msg}

🙏 از همراهی شما سپاسگزاریم.
🕌 با ما در مسیر نور همراه باش."""
                            
                            send_message(user[0], daily_msg)
                            sent_count += 1
                            time.sleep(0.2)
                            
                            if sent_count % 10 == 0:
                                time.sleep(0.5)
                        except Exception as e:
                            logger.error(f"خطا در ارسال به {user[0]}: {e}")
                    
                    logger.info(f"پیام روزانه به {sent_count} کاربر ارسال شد - {time_name}")
                except Exception as e:
                    logger.error(f"خطا در دریافت کاربران: {e}")
                
                logger.info(f"✅ ارسال روزانه کامل شد - {time_name}")
                break
        
        time.sleep(10)
    except Exception as e:
        logger.error(f"خطا در ارسال روزانه: {e}")

def next_item(book_name, data_list):
    """دریافت آیتم بعدی برای انتشار"""
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

# =========================================================
# ۲۵. گزارش هفتگی به ادمین
# =========================================================
def send_weekly_report():
    """ارسال گزارش هفتگی به ادمین"""
    if not FEATURES["weekly_report"]:
        return
    
    try:
        now = datetime.now()
        if now.weekday() != 6:  # یکشنبه
            return
        
        conn = db_conn()
        cur = conn.cursor()
        
        # تعداد کل کاربران
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        # کاربران فعال این هفته
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE last_active > datetime('now', '-7 days')
        """)
        active_users = cur.fetchone()[0]
        
        # تعداد جستجوهای این هفته
        cur.execute("""
            SELECT SUM(search_count) FROM users 
            WHERE last_active > datetime('now', '-7 days')
        """)
        searches = cur.fetchone()[0] or 0
        
        # تعداد بازخوردهای این هفته
        cur.execute("""
            SELECT COUNT(*) FROM feedbacks 
            WHERE created_at > datetime('now', '-7 days')
        """)
        feedbacks = cur.fetchone()[0]
        
        # بهترین کاربر هفته
        cur.execute("""
            SELECT name, score FROM users 
            ORDER BY score DESC LIMIT 1
        """)
        best_user = cur.fetchone()
        
        # تعداد دعوت‌های این هفته
        cur.execute("""
            SELECT COUNT(*) FROM referrals 
            WHERE created_at > datetime('now', '-7 days')
        """)
        referrals = cur.fetchone()[0]
        
        conn.close()
        
        report = f"""📊 <b>گزارش هفتگی ربات</b>
{'='*50}

📅 {get_persian_date()}

👥 <b>آمار کاربران:</b>
• کل کاربران: {total_users}
• کاربران فعال این هفته: {active_users}
• رشد هفتگی: {round((active_users / max(total_users, 1)) * 100, 1)}%

📊 <b>آمار فعالیت:</b>
• تعداد جستجوها: {searches}
• بازخوردهای دریافتی: {feedbacks}
• دعوت‌های جدید: {referrals}

🏆 <b>بهترین کاربر هفته:</b>
• {best_user[0] if best_user else 'نامشخص'} با {best_user[1] if best_user else 0} امتیاز

📈 <b>روند کلی:</b>
{get_system_stats()}

💪 به راه خود ادامه دهید! 🚀"""
        
        send_message(ADMIN_ID, report)
        logger.info("📊 گزارش هفتگی به ادمین ارسال شد.")
        
    except Exception as e:
        logger.error(f"خطا در ارسال گزارش هفتگی: {e}")

def weekly_report_scheduler():
    """اسکجولر گزارش هفتگی"""
    while True:
        try:
            time.sleep(3600)  # هر ساعت بررسی کن            send_weekly_report()
        except Exception as e:
            logger.error(f"خطا در اسکجولر گزارش هفتگی: {e}")
            time.sleep(3600)

# =========================================================
# ۲۶. سیستم پیام‌های انگیزشی خودکار
# =========================================================
def send_motivational_messages():
    """ارسال پیام‌های انگیزشی خودکار"""
    if not FEATURES["motivational_messages"]:
        return
    
    try:
        now = datetime.now()
        if now.hour == 7 and now.minute == 0:  # هر روز ساعت ۷ صبح
            msg = random.choice(MOTIVATIONAL_MESSAGES)
            send_message(CHANNEL_ID, f"🌅 {msg}\n\n🌟 روزت پر از نور و آرامش! 🌸")
            logger.info("پیام انگیزشی صبحگاهی ارسال شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال پیام انگیزشی: {e}")

def motivational_scheduler():
    """اسکجولر پیام‌های انگیزشی"""
    while True:
        try:
            send_motivational_messages()
            time.sleep(60)
        except Exception as e:
            logger.error(f"خطا در اسکجولر پیام‌های انگیزشی: {e}")
            time.sleep(60)

# =========================================================
# ۲۷. سیستم یادآوری مناسبت‌های مذهبی
# =========================================================
def check_religious_occasions():
    """بررسی و اعلام مناسبت‌های مذهبی"""
    if not FEATURES["religious_reminders"]:
        return
    
    try:
        now = datetime.now()
        today = (now.month, now.day)
        
        for name, data in RELIGIOUS_OCCASIONS.items():
            if (data["month"], data["day"]) == today:
                message = f"""🕌 <b>{data['title']}</b>

{data['message']}

💚 این مناسبت را گرامی بداریم.
🕌 با دعا و نیایش در این روز خاص، دل را به خدا نزدیک کنیم."""
                
                send_message(CHANNEL_ID, message)
                
                # اطلاع به ادمین
                send_message(ADMIN_ID, f"📢 مناسبت مذهبی امروز:\n{data['title']}\n{data['message']}")
                
                logger.info(f"یادآوری مناسبت مذهبی ارسال شد: {name}")
                break
    except Exception as e:
        logger.error(f"خطا در بررسی مناسبت‌های مذهبی: {e}")

def religious_reminder_scheduler():
    """اسکجولر یادآوری مناسبت‌های مذهبی"""
    while True:
        try:
            check_religious_occasions()
            time.sleep(3600)  # هر ساعت بررسی کن
        except Exception as e:
            logger.error(f"خطا در اسکجولر مناسبت‌های مذهبی: {e}")
            time.sleep(3600)

# =========================================================
# ۲۸. مدیریت دیتابیس
# =========================================================
def db_conn():
    """اتصال به دیتابیس با مدیریت خطا"""
    try:
        return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    except Exception as e:
        logger.error(f"خطا در اتصال به دیتابیس: {e}")
        raise

def init_db():
    """راه‌اندازی دیتابیس با تمام جداول"""
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
            created_at TEXT,
            delivery_status TEXT DEFAULT 'sent'
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type TEXT,
            error_message TEXT,
            traceback TEXT,
            user_id INTEGER,
            created_at TEXT,
            resolved INTEGER DEFAULT 0
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
            status TEXT DEFAULT 'active',
            bonus_given INTEGER DEFAULT 0
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
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id TEXT,
            question TEXT,
            options TEXT,
            created_by INTEGER,
            created_at TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    
    for book in ["quran", "nahj", "sahifeh"]:
        cur.execute("INSERT OR IGNORE INTO publish_state (book_name, last_index) VALUES (?, 0)", (book,))
    
    conn.commit()
    conn.close()
    logger.info("🗄️ دیتابیس با موفقیت راه‌اندازی شد.")

def generate_referral_code():
    """تولید کد دعوت تصادفی برای بله"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))

def get_user(chat_id):
    """دریافت اطلاعات کامل کاربر با مدیریت خطا"""
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
    
    return {
        "name": "", "lang": "fa", "score": 0, "search_count": 0,
        "streak": 0, "feedback_score": 0, "last_active": "",
        "join_date": "", "receive_daily": 0, "state": "none",
        "total_visits": 0, "achievements": "", "last_visit_date": "",
        "daily_visit_count": 0, "total_quests_completed": 0,
        "last_quest_date": "", "referral_code": "",
        "referred_by": 0, "referral_count": 0, "referral_earned": 0,
        "profile_image": "", "bio": ""
    }

def ensure_user(chat_id, name="", referred_by=None):
    """ثبت کاربر جدید با سیستم دعوت"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        
        cur.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        existing = cur.fetchone()
        
        if existing:
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
                    send_message_with_retry(
                        referred_by,
                        f"""🎉 <b>تبریک! شما یک دعوت جدید دارید!</b>

🌸 کاربر جدید با کد دعوت شما عضو شد:
👤 {name}

🌟 ۱۰ امتیاز به حساب شما اضافه شد!
🏆 مجموع دعوت‌های شما: {referrer.get('referral_count', 0) + 1}

💚 به دعوت‌های خود ادامه دهید!"""
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به دعوت‌کننده: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"کاربر جدید ثبت شد: {chat_id} ({name}) - کد دعوت: {referral_code}")
        
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر {chat_id}: {e}")

def update_user(chat_id, **kwargs):
    """به‌روزرسانی اطلاعات کاربر با اعتبارسنجی"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        
        if "lang" in kwargs and kwargs["lang"] not in ["fa", "en", "ar"]:
            kwargs["lang"] = "fa"
        
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ["name", "lang", "state", "achievements", "last_quest_date", 
                       "referral_code", "profile_image", "bio"]:
                fields.append(f"{key} = ?")
                values.append(value)
            elif key in ["score", "search_count", "streak", "feedback_score", 
                        "receive_daily", "total_visits", "daily_visit_count",
                        "total_quests_completed", "referral_count", "referral_earned"]:
                fields.append(f"{key} = {key} + ?")
                values.append(value)
            elif key in ["score_set", "search_count_set", "streak_set", 
                        "referral_count_set", "referral_earned_set"]:
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
    """دریافت آخرین شاخص انتشار کتاب"""
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
    """تنظیم شاخص انتشار کتاب"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE publish_state 
            SET last_index = ?, last_publish_date = CURRENT_TIMESTAMP 
            WHERE book_name = ?
        """, (index_value, book_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در تنظیم وضعیت انتشار {book_name}: {e}")

def get_leaderboard(limit=10):
    """دریافت لیگ قرآنی با کاربران واقعی"""
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
    """محاسبه رتبه کاربر در لیگ قرآنی"""
    try:
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
    except Exception as e:
        logger.error(f"خطا در دریافت رتبه کاربر {chat_id}: {e}")
        return 1

def get_user_count():
    """دریافت تعداد کل کاربران"""
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
    """دریافت بیشترین امتیاز"""
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
    """دریافت لیست تمام کاربران"""
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
    """دریافت کاربران فعال در روزهای اخیر"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(DISTINCT chat_id) 
            FROM users 
            WHERE last_active > datetime('now', '-{} days')
        """.format(days))
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"خطا در دریافت کاربران فعال: {e}")
        return 0

def log_error(error_type, error_message, traceback_str, user_id=None):
    """ثبت خطا در دیتابیس"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO error_logs (error_type, error_message, traceback, user_id, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (error_type, error_message[:500], traceback_str[:500], user_id))
        conn.commit()
        conn.close()
    except:
        pass

def save_sent_message(message_type, content, sent_to):
    """ذخیره پیام ارسالی"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sent_messages (message_type, content, sent_to, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (message_type, content[:500], sent_to))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره پیام ارسالی: {e}")

def update_daily_stats():
    """به‌روزرسانی آمار روزانه"""
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
# ۲۹. ابزارهای ارسال پیام به بله
# =========================================================
def send_bale(method, data, retry_count=3):
    """ارسال درخواست به API بله با قابلیت تکرار"""
    if not TOKEN:
        return {"ok": False, "error": "TOKEN not set"}
    
    url = f"{BASE_URL}/{method}"
    
    for attempt in range(retry_count):
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"BALE API status {response.status_code}: {response.text[:200]}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        except requests.exceptions.Timeout:
            logger.error(f"Timeout در {method} (تلاش {attempt+1})")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"BALE API ERROR in {method}: {e}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
    
    return {"ok": False, "error": "Max retries exceeded"}

def answer_callback(callback_query_id, text=None):
    """پاسخ به callback_query"""
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    return send_bale("answerCallbackQuery", payload)

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """ارسال پیام با پشتیبانی از متن طولانی"""
    if not text:
        return None
    
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            send_message(chat_id, part, reply_markup if i == 0 else None, parse_mode)
        return {"ok": True}
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    
    return send_bale("sendMessage", payload)

def send_message_with_retry(chat_id, text, reply_markup=None, max_retries=3):
    """ارسال پیام با قابلیت تکرار"""
    for attempt in range(max_retries):
        result = send_message(chat_id, text, reply_markup)
        if result and result.get("ok"):
            return result
        time.sleep(2 ** attempt)
    return None

def send_chat_action(chat_id, action="typing"):
    """ارسال وضعیت تایپ یا در حال پردازش"""
    return send_bale("sendChatAction", {
        "chat_id": chat_id,
        "action": action
    })

# =========================================================
# ۳۰. هوش مصنوعی DeepSeek (رفع باگ)
# =========================================================
def ask_deepseek(question, lang):
    """ارسال سوال به DeepSeek با مدیریت کامل خطا و حفظ مکالمه"""
    if not FEATURES["deepseek_ai"]:
        return "🔧 این ویژگی در حال حاضر غیرفعال است."
    
    if not DEEPSEEK_KEY or len(DEEPSEEK_KEY) < 10:
        logger.warning("کلید DeepSeek نامعتبر است")
        return "🔑 کلید API هوش مصنوعی تنظیم نشده است. لطفاً با ادمین تماس بگیرید."
    
    # مدیریت Rate Limit
    current_time = time.time()
    if chat_id in RATE_LIMIT_COUNTER:
        if current_time - RATE_LIMIT_TIME.get(chat_id, 0) < 60:
            RATE_LIMIT_COUNTER[chat_id] = RATE_LIMIT_COUNTER.get(chat_id, 0) + 1
            if RATE_LIMIT_COUNTER[chat_id] > 5:
                return "⏳ تعداد درخواست‌های شما زیاد شده است. لطفاً یک دقیقه صبر کنید و دوباره تلاش کنید."
        else:
            RATE_LIMIT_COUNTER[chat_id] = 1
            RATE_LIMIT_TIME[chat_id] = current_time
    else:
        RATE_LIMIT_COUNTER[chat_id] = 1
        RATE_LIMIT_TIME[chat_id] = current_time
    
    # حفظ تاریخچه مکالمه
    conversation_key = f"conv_{chat_id}"
    if conversation_key not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[conversation_key] = []
    
    language_name = {"fa": "Persian", "en": "English", "ar": "Arabic"}.get(lang, "Persian")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    
    # ساخت پیام‌ها با تاریخچه
    messages = [
        {"role": "system", "content": f"You are a warm, respectful, accurate assistant for a Quranic student bot at Shiraz University of Medical Sciences. Reply in {language_name}. Keep the answer useful, friendly, and well-formatted. If you don't know something, say so clearly. Provide interpretations that are relevant to medical professionals and students."}
    ]
    
    # اضافه کردن تاریخچه (آخرین ۵ پیام)
    for msg in CONVERSATION_HISTORY[conversation_key][-5:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": question})
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        send_chat_action(chat_id, "typing")
        
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=45
        )
        
        logger.info(f"DeepSeek Response Status: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and data["choices"]:
                answer = data["choices"][0]["message"]["content"]
                # ذخیره در تاریخچه
                CONVERSATION_HISTORY[conversation_key].append({"role": "user", "content": question})
                CONVERSATION_HISTORY[conversation_key].append({"role": "assistant", "content": answer})
                return answer
            else:
                logger.error(f"پاسخ غیرمنتظره از DeepSeek: {data}")
                return "⚠️ پاسخ دریافتی نامعتبر بود. لطفاً دوباره تلاش کنید."
        elif res.status_code == 401:
            logger.error("کلید DeepSeek نامعتبر است (401)")
            return "🔑 کلید API نامعتبر است. لطفاً با ادمین تماس بگیرید."
        elif res.status_code == 429:
            logger.error("محدودیت درخواست DeepSeek (429)")
            time.sleep(5)
            return "⏳ تعداد درخواست‌ها محدود شده است. چند لحظه صبر کنید و دوباره تلاش کنید."
        else:
            logger.error(f"خطای DeepSeek: {res.status_code} - {res.text[:200]}")
            return f"⚠️ خطا در ارتباط با هوش مصنوعی (کد {res.status_code}). لطفاً بعداً تلاش کنید."
            
    except requests.exceptions.Timeout:
        logger.error("Timeout در ارتباط با DeepSeek")
        return "⏳ زمان ارتباط با هوش مصنوعی به پایان رسید. لطفاً دوباره تلاش کنید."
    except requests.exceptions.ConnectionError:
        logger.error("خطای اتصال به DeepSeek")
        return "🌐 خطا در اتصال به اینترنت. لطفاً اتصال خود را بررسی کنید."
    except Exception as e:
        logger.error(f"خطای DeepSeek: {e}")
        return "⚠️ خطا در ارتباط با هوش مصنوعی. لطفاً بعداً تلاش کنید."

# =========================================================
# ۳۱. کیبوردهای اینلاین
# =========================================================
def lang_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🇮🇷 فارسی", "callback_data": "setlang_fa"}],
            [{"text": "🇬🇧 English", "callback_data": "setlang_en"}],
            [{"text": "🇸🇦 العربية", "callback_data": "setlang_ar"}]
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

def quest_keyboard(lang):
    return {
        "inline_keyboard": [
            [{"text": "🎯 جستجوی قرآن (۳ امتیاز)", "callback_data": "quest_quran_search"}],
            [{"text": "🌅 بازدید روزانه (۵ امتیاز)", "callback_data": "quest_daily_visit"}],
            [{"text": "📝 ارسال پیشنهاد (۵ امتیاز)", "callback_data": "quest_feedback"}],
            [{"text": "🕊️ مطالعه حدیث (۲ امتیاز)", "callback_data": "quest_hadith"}],
            [{"text": "✨ قرآن در لحظه (۲ امتیاز)", "callback_data": "quest_instant_quran"}],
            [{"text": "🤝 دعوت از دوستان (۱۰ امتیاز)", "callback_data": "quest_referral"}],
            [{"text": "📊 مشاهده امتیازات", "callback_data": "show_quest_points"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def best_users_keyboard(lang):
    return {
        "inline_keyboard": [
            [{"text": "🏅 بهترین کاربر روز", "callback_data": "show_best_daily"}],
            [{"text": "🏆 بهترین کاربر هفته", "callback_data": "show_best_weekly"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def referral_keyboard(lang, referral_code):
    bot_username = BOT_USERNAME
    referral_link = f"https://ble.ir/{bot_username}?start=ref_{referral_code}"
    
    return {
        "inline_keyboard": [
            [{"text": "📤 اشتراک‌گذاری لینک دعوت", "url": f"https://ble.ir/share?url={referral_link}&text=🌸 به ربات کانون قرآن و عترت بپیوند! \nبا این لینک عضو شو و ۱۰ امتیاز هدیه بگیر! 🎁"}],
            [{"text": "📋 کپی لینک", "callback_data": "copy_referral"}],
            [{"text": "📊 آمار دعوت‌ها", "callback_data": "referral_stats"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

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
    return {
        "inline_keyboard": [
            [{"text": "❓ نحوه استفاده", "callback_data": "faq_usage"}],
            [{"text": "📖 جستجوی قرآن", "callback_data": "faq_search"}],
            [{"text": "🤖 هوش مصنوعی", "callback_data": "faq_ai"}],
            [{"text": "🏆 امتیازات", "callback_data": "faq_points"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def profile_keyboard(lang):
    return {
        "inline_keyboard": [
            [{"text": "✏️ تغییر نام", "callback_data": "profile_name"}],
            [{"text": "📝 تغییر بیو", "callback_data": "profile_bio"}],
            [{"text": "📊 مشاهده پروفایل", "callback_data": "profile_view"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def main_menu(chat_id, lang):
    labels = safe_lang_dict(lang)["menu_labels"]
    buttons = [
        [{"text": labels["islamic_search"], "callback_data": "menu_islamic_search"},
         {"text": labels["ai"], "callback_data": "menu_ai"}],
        [{"text": labels["hadith"], "callback_data": "menu_hadith"},
         {"text": labels["instant_quran"], "callback_data": "menu_instant_quran"}],
        [{"text": labels["events"], "callback_data": "menu_events"},
         {"text": labels["feedback"], "callback_data": "menu_feedback"}],
        [{"text": labels["admin_msg"], "callback_data": "menu_admin_msg"},
         {"text": labels["stats"], "callback_data": "menu_stats"}],
        [{"text": labels["league"], "callback_data": "menu_league"},
         {"text": labels["scorecard"], "callback_data": "menu_scorecard"}],
        [{"text": labels["change_lang"], "callback_data": "menu_change_lang"},
         {"text": labels["about"], "callback_data": "menu_about"}],
        [{"text": labels["help"], "callback_data": "menu_help"},
         {"text": labels["reminder"], "callback_data": "menu_reminder"}],
        [{"text": labels["share"], "callback_data": "menu_share"},
         {"text": labels["quests"], "callback_data": "menu_quests"}],
        [{"text": labels["best_users"], "callback_data": "menu_best_users"},
         {"text": labels["referral"], "callback_data": "menu_referral"}],
        [{"text": labels["favorites"], "callback_data": "menu_favorites"},
         {"text": labels["faq"], "callback_data": "menu_faq"}],
        [{"text": labels["voice_search"], "callback_data": "menu_voice_search"},
         {"text": labels["profile"], "callback_data": "menu_profile"}]
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
            [{"text": safe_text(lang, "admin_system"), "callback_data": "admin_system"}],
            [{"text": safe_text(lang, "admin_achievements"), "callback_data": "admin_achievements"}],
            [{"text": safe_text(lang, "admin_best_users"), "callback_data": "admin_best_users"}],
            [{"text": safe_text(lang, "admin_referrals"), "callback_data": "admin_referrals"}],
            [{"text": safe_text(lang, "admin_weekly_report"), "callback_data": "admin_weekly_report"}],
            [{"text": safe_text(lang, "admin_surveys"), "callback_data": "admin_surveys"}],
            [{"text": safe_text(lang, "admin_back"), "callback_data": "back_main"}]
        ]
    }

def share_keyboard(lang):
    return {
        "inline_keyboard": [
            [{"text": "📤 اشتراک‌گذاری ربات", "switch_inline_query": "ربات قرآن و عترت"}],
            [{"text": "📋 کپی لینک", "callback_data": "copy_link"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def reminder_keyboard(lang):
    return {
        "inline_keyboard": [
            [{"text": "🕐 تنظیم یادآوری روزانه", "callback_data": "reminder_daily"}],
            [{"text": "🔔 تنظیم یادآوری هفتگی", "callback_data": "reminder_weekly"}],
            [{"text": "📋 مشاهده یادآوری‌ها", "callback_data": "reminder_list"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

# =========================================================
# ۳۲. عضویت اجباری کانال
# =========================================================
MEMBERSHIP_CACHE = {}
CACHE_DURATION = 300

def check_membership(chat_id):
    """بررسی عضویت کاربر با استفاده از کش و مدیریت خطا"""
    if not CHANNEL_ID or not FEATURES["force_join"]:
        return True
    
    cache_key = f"membership_{chat_id}"
    if cache_key in MEMBERSHIP_CACHE:
        result, timestamp = MEMBERSHIP_CACHE[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            return result
    
    try:
        result = send_bale("getChatMember", {
            "chat_id": CHANNEL_ID,
            "user_id": chat_id
        })
        
        if result and result.get("ok"):
            status = result.get("result", {}).get("status", "")
            is_member = status in ["member", "administrator", "creator"]
            MEMBERSHIP_CACHE[cache_key] = (is_member, time.time())
            logger.info(f"عضویت کاربر {chat_id}: {is_member} (status: {status})")
            return is_member
        
        logger.warning(f"پاسخ ناموفق از API برای عضویت {chat_id}: {result}")
        return True
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت {chat_id}: {e}")
        return True

# =========================================================
# ۳۳. توابع کمکی
# =========================================================
def get_user_state(chat_id):
    """دریافت وضعیت کاربر"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT state FROM users WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else "none"
    except Exception as e:
        logger.error(f"خطا در دریافت وضعیت کاربر {chat_id}: {e}")
        return "none"

def get_system_stats():
    """دریافت آمار کامل سیستم"""
    stats = {
        "total_users": get_user_count(),
        "active_users_7d": get_active_users(7),
        "active_users_30d": get_active_users(30),
        "highest_score": get_highest_score(),
        "total_feedbacks": 0,
        "pending_feedbacks": 0,
        "quran_count": len(QURAN_DATA),
        "nahj_count": len(NAHJ_DATA),
        "sahifeh_count": len(SAHIFEH_DATA),
        "total_referrals": 0,
        "features_status": FEATURES
    }
    
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
    """فرمت‌بندی آمار سیستم برای نمایش"""
    stats = get_system_stats()
    
    return f"""💻 <b>وضعیت سیستم</b>

📊 <b>آمار کلی:</b>
👥 کل کاربران: {stats['total_users']}
🟢 کاربران فعال (۷ روز): {stats['active_users_7d']}
🟡 کاربران فعال (۳۰ روز): {stats['active_users_30d']}

🏆 <b>آمار محتوا:</b>
📖 آیات قرآن: {stats['quran_count']}
📜 خطبه‌های نهج‌البلاغه: {stats['nahj_count']}
🤲 دعاهای صحیفه سجادیه: {stats['sahifeh_count']}
🧠 موضوعات: {len(TOPICS_DATA)}

📝 <b>بازخوردها:</b>
📩 کل بازخوردها: {stats['total_feedbacks']}
⏳ در انتظار بررسی: {stats['pending_feedbacks']}

🎯 <b>کوئست‌ها:</b>
✅ کل کوئست‌های انجام شده: {stats.get('total_quests', 0)}

🤝 <b>دعوت‌ها:</b>
✅ کل دعوت‌ها: {stats.get('total_referrals', 0)}

⚙️ <b>ویژگی‌های فعال:</b>
{', '.join([k for k, v in stats['features_status'].items() if v])}

📅 آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""

# =========================================================
# ۳۴. وب هوک و مدیریت درخواست‌ها
# =========================================================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_token():
    """پردازش تمام درخواست‌های ورودی"""
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
            
            # پردازش کد دعوت در start
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
                            logger.info(f"کاربر {chat_id} با کد دعوت {referral_code} ثبت شد")
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

            if text == "/start" or text == "شروع" or text == "/start@labbayk_quranbot":
                update_user(chat_id, state="none")
                send_message(
                    chat_id,
                    safe_text(lang, "select_lang"),
                    lang_keyboard()
                )
                return "OK", 200

            # بررسی عضویت
            if chat_id != ADMIN_ID:
                try:
                    is_member = check_membership(chat_id)
                    if not is_member:
                        send_message(
                            chat_id,
                            safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID),
                            join_keyboard()
                        )
                        return "OK", 200
                except Exception as e:
                    logger.error(f"خطا در بررسی عضویت: {e}")

            # پردازش وضعیت‌های خاص
            try:
                handled = handle_state_message(chat_id, text, user)
                if handled:
                    return "OK", 200
            except Exception as e:
                logger.error(f"خطا در پردازش وضعیت: {e}")
                send_message(chat_id, "⚠️ یه خطای کوچیک رخ داد! 😅\nلطفاً دوباره تلاش کن.")
                update_user(chat_id, state="none")
                return "OK", 200

            # نمایش منوی اصلی
            greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
            title = get_user_title(user.get("score", 0))
            title_desc = get_user_title_description(title)
            
            if lang == "fa":
                welcome_text = f"""{greeting}

{first_name} جان! 😍

چقدر خوشحالم که به جمع ما پیوندی! 🌸

به ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.
👑 عنوان تو: {title}
💡 {title_desc}

✨ اینجا یه همراه همیشگی برای مسیر نور و معرفتته:
• جستجوی هوشمند اسلامی 🧠
• هوش مصنوعی پاسخ‌گو 🤖
• جستجوی صوتی 🎤
• حدیث و ذکر روزانه 🕊️
• قرآن در لحظه ✨
• و کلی قابلیت دیگه!

👇 از منوی زیر انتخاب کن:"""
            else:
                welcome_text = safe_text(lang, "welcome", name=first_name)
            
            send_message(chat_id, welcome_text, main_menu(chat_id, lang))
            update_user_score(chat_id, "daily_visit", user)
            
            return "OK", 200

        # پردازش callback_query
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

            # تغییر زبان
            if cb_data.startswith("setlang_"):
                new_lang = cb_data.replace("setlang_", "").strip()
                if new_lang not in LANGS:
                    new_lang = "fa"

                update_user(chat_id, lang=new_lang, state="none")
                user = get_user(chat_id)
                lang = user["lang"]

                if chat_id != ADMIN_ID:
                    try:
                        is_member = check_membership(chat_id)
                        if not is_member:
                            send_message(
                                chat_id,
                                safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID),
                                join_keyboard()
                            )
                            return "OK", 200
                    except Exception as e:
                        logger.error(f"خطا در بررسی عضویت: {e}")
                
                greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
                title = get_user_title(user.get("score", 0))
                if lang == "fa":
                    welcome_text = f"{greeting}\n\n{first_name} جان! 😍\n\nبه ربات کانون قرآن و عترت خوش آمدی.\n👑 عنوان: {title}\n\nاز منوی زیر استفاده کن:"
                else:
                    welcome_text = safe_text(lang, "welcome", name=first_name)
                send_message(chat_id, welcome_text, main_menu(chat_id, lang))
                return "OK", 200

            # تأیید عضویت
            if cb_data == "check_join":
                try:
                    is_member = check_membership(chat_id)
                    if is_member:
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
                except Exception as e:
                    logger.error(f"خطا در بررسی عضویت: {e}")
                    send_message(
                        chat_id,
                        "⚠️ خطا در بررسی عضویت. لطفاً دوباره تلاش کنید.",
                        join_keyboard()
                    )
                return "OK", 200

            # بازگشت به منوی اصلی
            if cb_data == "back_main":
                update_user(chat_id, state="none")
                greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
                title = get_user_title(user.get("score", 0))
                if lang == "fa":
                    send_message(
                        chat_id,
                        f"{greeting}\n\n{first_name} جان! 🍃\nخوش برگشتی به خانه خودت! 🌸\n👑 عنوان: {title}",
                        main_menu(chat_id, lang)
                    )
                else:
                    send_message(
                        chat_id,
                        f"{greeting}\n\n{safe_text(lang, 'back_to_menu')}",
                        main_menu(chat_id, lang)
                    )
                return "OK", 200

            # بررسی عضویت
            if chat_id != ADMIN_ID:
                try:
                    is_member = check_membership(chat_id)
                    if not is_member:
                        send_message(
                            chat_id,
                            safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID),
                            join_keyboard()
                        )
                        return "OK", 200
                except Exception as e:
                    logger.error(f"خطا در بررسی عضویت: {e}")

            # جستجوی هوشمند اسلامی
            if cb_data == "menu_islamic_search":
                update_user(chat_id, state="waiting_quran_search")
                if lang == "fa":
                    msg = f"""🧠 <b>جستجوی هوشمند اسلامی</b>

🔍 کلمه یا موضوع مورد نظرت رو وارد کن:

💡 <b>این موتور پیشرفته در تمام منابع زیر جستجو می‌کند:</b>

📖 <b>قرآن کریم</b> - با ترجمه و تفسیر
📜 <b>نهج‌البلاغه</b> - خطبه‌ها، نامه‌ها و حکمت‌ها
🤲 <b>صحیفه سجادیه</b> - دعاهای نورانی
🕊️ <b>احادیث</b> - روایات معصومین با ذکر
📚 <b>مقالات علمی</b> - از گوگل اسکالر
🌐 <b>اینترنت</b> - از سراسر دنیا

🔍 <b>قابلیت‌های پیشرفته:</b>
• تشخیص خودکار موضوع و مترادف‌ها
• جستجوی معنایی (Semantic Search)
• نمایش نتایج دسته‌بندی شده

📝 لطفاً عبارت خود را ارسال کن:"""
                else:
                    msg = safe_text(lang, "search_quran_prompt")
                send_message(chat_id, msg, back_menu_keyboard(lang))
                return "OK", 200

            # حدیث روز با منبع
            if cb_data == "menu_hadith":
                if not FEATURES["hadith_dhikr"]:
                    send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                    return "OK", 200
                
                item = random.choice(HADITHS_WITH_DHIKR)
                msg = f"""🕊️ <b>حدیث روز</b>

{item['hadith']}

📚 <b>منبع:</b> {item['source']}

🔹 <b>ذکر روزانه:</b>
{item['dhikr']}

🏷️ دسته: {item['category']}

💚 با یاد خدا دل‌ها آرام می‌گیرد."""
                send_message(chat_id, msg, main_menu(chat_id, lang))
                update_user(chat_id, score=1)
                update_user_score(chat_id, "hadith_read", user)
                return "OK", 200

            # قرآن در لحظه
            if cb_data == "menu_instant_quran":
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
                update_user(chat_id, score=1)
                update_user_score(chat_id, "instant_quran", user)
                return "OK", 200

            # بقیه دکمه‌ها (به دلیل محدودیت فضا، ادامه در بخش بعدی)
            # ... ادامه در بخش بعدی

        return "OK", 200

    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"WEBHOOK ERROR: {error_msg}\n{traceback_str}")
        log_error("webhook_error", error_msg, traceback_str)
        return "OK", 200

# =========================================================
# ۳۵. مسیرهای تست و سلامت
# =========================================================
@app.route("/", methods=["GET", "HEAD"])
def health():
    """بررسی سلامت ربات"""
    return jsonify({
        "status": "ok",
        "service": "labbayk_quranbot",
        "version": "15.0",
        "time": datetime.now().isoformat(),
        "persian_date": get_persian_date(),
        "quran_records": len(QURAN_DATA),
        "nahj_records": len(NAHJ_DATA),
        "sahifeh_records": len(SAHIFEH_DATA),
        "topics_count": len(TOPICS_DATA),
        "total_users": get_user_count(),
        "active_users_7d": get_active_users(7),
        "features": FEATURES,
        "deepseek_configured": bool(DEEPSEEK_KEY and len(DEEPSEEK_KEY) > 10),
        "port": PORT,
        "supported_languages": ["fa", "en", "ar"],
        "islamic_knowledge_engine": FEATURES["islamic_knowledge_engine"],
        "internet_search": FEATURES["internet_search"],
        "jdatetime_installed": HAS_JDATETIME
    }), 200

@app.route("/webhook", methods=["GET", "HEAD"])
def webhook_check():
    """بررسی وب‌هوک"""
    return jsonify({
        "status": "ok",
        "message": "Webhook is alive",
        "time": datetime.now().isoformat()
    }), 200

# =========================================================
# ۳۶. اجرای استارتاپ
# =========================================================
def startup():
    """راه‌اندازی اولیه ربات با تمام قابلیت‌ها"""
    try:
        logger.info("🚀 شروع راه‌اندازی ربات...")
        
        init_db()
        logger.info("✅ دیتابیس راه‌اندازی شد.")
        
        load_library()
        logger.info("✅ کتابخانه بارگذاری شد.")
        
        if DEEPSEEK_KEY and len(DEEPSEEK_KEY) > 10:
            logger.info("✅ کلید DeepSeek تنظیم شده است.")
            FEATURES["deepseek_ai"] = True
        else:
            logger.warning("⚠️ کلید DeepSeek وجود ندارد یا نامعتبر است.")
            FEATURES["deepseek_ai"] = False
        
        # اسکجولر روزانه
        if FEATURES["daily_posts"]:
            scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("✅ اسکژولر روزانه (۳ زمان) راه‌اندازی شد.")
        
        # اسکجولر بهترین کاربران
        if FEATURES["best_user_daily"] or FEATURES["best_user_weekly"]:
            best_user_thread = threading.Thread(target=schedule_best_users, daemon=True)
            best_user_thread.start()
            logger.info("✅ اسکژولر بهترین کاربران واقعی راه‌اندازی شد.")
        
        # اسکجولر بک‌آپ
        if FEATURES["auto_backup"]:
            backup_thread = threading.Thread(target=backup_scheduler, daemon=True)
            backup_thread.start()
            logger.info("✅ اسکژولر بک‌آپ خودکار راه‌اندازی شد.")
        
        # اسکجولر گزارش هفتگی
        if FEATURES["weekly_report"]:
            weekly_report_thread = threading.Thread(target=weekly_report_scheduler, daemon=True)
            weekly_report_thread.start()
            logger.info("✅ اسکژولر گزارش هفتگی راه‌اندازی شد.")
        
        # اسکجولر پیام‌های انگیزشی
        if FEATURES["motivational_messages"]:
            motivational_thread = threading.Thread(target=motivational_scheduler, daemon=True)
            motivational_thread.start()
            logger.info("✅ اسکژولر پیام‌های انگیزشی راه‌اندازی شد.")
        
        # اسکجولر مناسبت‌های مذهبی
        if FEATURES["religious_reminders"]:
            religious_thread = threading.Thread(target=religious_reminder_scheduler, daemon=True)
            religious_thread.start()
            logger.info("✅ اسکژولر مناسبت‌های مذهبی راه‌اندازی شد.")
        
        # تمیزکاری کش
        def cache_cleaner():
            while True:
                try:
                    time.sleep(21600)
                    MEMBERSHIP_CACHE.clear()
                    SEARCH_CACHE.clear()
                    logger.info("🧹 کش عضویت و جستجو پاکسازی شد.")
                except Exception as e:
                    logger.error(f"خطا در پاکسازی کش: {e}")
        
        cleaner_thread = threading.Thread(target=cache_cleaner, daemon=True)
        cleaner_thread.start()
        logger.info("✅ تمیزکاری کش خودکار راه‌اندازی شد.")
        
        logger.info("🎉 ربات با موفقیت راه‌اندازی شد!")
        logger.info(f"📊 آمار اولیه: {get_system_stats()}")
        logger.info(f"🌐 سرور روی پورت {PORT} در حال اجراست...")
        logger.info(f"🌍 زبان‌های پشتیبانی: فارسی, English, العربية")
        logger.info(f"🧠 موتور دانش اسلامی: {'فعال' if FEATURES['islamic_knowledge_engine'] else 'غیرفعال'}")
        logger.info(f"🌐 جستجوی اینترنتی: {'فعال' if FEATURES['internet_search'] else 'غیرفعال'}")
        logger.info(f"📅 تاریخ شمسی: {'فعال' if HAS_JDATETIME else 'غیرفعال (استفاده از میلادی)'}")
        
    except Exception as e:
        logger.error(f"❌ خطا در راه‌اندازی: {e}")
        logger.error(traceback.format_exc())

def daily_scheduler():
    """اسکجولر روزانه - هر دقیقه بررسی می‌کند"""
    time.sleep(30)
    while True:
        try:
            send_daily_posts()
            update_daily_stats()
        except Exception as e:
            logger.error(f"خطا در اسکجولر: {e}")
        time.sleep(60)

# اجرای startup در زمان بارگذاری
startup()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 ربات روی پورت {port} در حال اجراست...")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
