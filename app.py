# -*- coding: utf-8 -*-
"""
ربات حرفه‌ای کانون قرآن و عترت - نسخه ۹.۰ (نسخه نهایی و جامع)
ویژه دانشگاه علوم پزشکی شیراز
با موتور دانش اسلامی (Islamic Knowledge Engine) و جستجوی معنایی
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
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from functools import wraps
import traceback

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

# متغیرهای سراسری
QURAN_DATA = []
NAHJ_DATA = []
SAHIFEH_DATA = []
ARTICLE_CACHE = {}
TOPICS_DATA = {}
USER_SESSIONS = {}

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
    "semantic_search": True,
    "islamic_knowledge_engine": True
}

# =========================================================
# ۳. داده‌های اولیه و نمونه (توسعه‌یافته با تفسیر)
# =========================================================
DEFAULT_QURAN_SEED = [
    {"index": 1, "surah": "حمد", "verse": 1, "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "trans": "به نام خداوند بخشنده مهربان", "interpretation": "شروع هر کار با نام خدا، نشانه توکل و ایمان است. برای پزشکان و دانشجویان علوم پزشکی، این آیه یادآور شروع هر اقدام درمانی با نام خداوند مهربان است.", "topics": ["ایمان", "توکل", "شروع", "بسم الله"]},
    {"index": 2, "surah": "حمد", "verse": 2, "text": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "trans": "ستایش مخصوص خداوندی است که پروردگار جهانیان است", "interpretation": "تمام هستی و از جمله علم پزشکی، نشانه‌های پروردگار جهانیان است. هر کشف علمی، ستایشی بر عظمت خالق است.", "topics": ["حمد", "ستایش", "خداوند", "جهانیان"]},
    {"index": 3, "surah": "حمد", "verse": 3, "text": "الرَّحْمَٰنِ الرَّحِيمِ", "trans": "بخشنده و مهربان است", "interpretation": "رحمانیت و رحیمیت خدا، الگوی پزشکان در مهربانی با بیماران است. همان‌گونه که خداوند به بندگانش مهربان است، پزشک نیز باید نسبت به بیماران مهربان باشد.", "topics": ["رحمت", "مهربانی", "بخشش"]},
    {"index": 4, "surah": "حمد", "verse": 4, "text": "مَالِكِ يَوْمِ الدِّينِ", "trans": "مالک روز جزاست", "interpretation": "روز جزا یادآور مسئولیت پزشکان در قبال جان انسان‌هاست. هر درمان و هر تصمیم پزشکی، در پیشگاه خداوند حساب دارد.", "topics": ["جزا", "مسئولیت", "حسابرسی"]},
    {"index": 5, "surah": "حمد", "verse": 5, "text": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "trans": "تنها تو را می‌پرستیم و تنها از تو یاری می‌جوییم", "interpretation": "پزشکان و پرستاران در درمان بیماران، تنها به خداوند توکل کنند و از او یاری بجویند. علم پزشکی بدون یاری الهی، کامل نمی‌شود.", "topics": ["عبادت", "توکل", "یاری"]},
    {"index": 6, "surah": "بقره", "verse": 153, "text": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "trans": "ای کسانی که ایمان آورده‌اید، از صبر و نماز یاری جویید", "interpretation": "صبر در برابر سختی‌های درمان و نماز برای آرامش قلب، دو ابزار قدرتمند برای کادر درمان است.", "topics": ["صبر", "نماز", "یاری", "ایمان"]},
    {"index": 7, "surah": "بقره", "verse": 255, "text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ", "trans": "خداوند است که هیچ معبودی جز او نیست؛ زنده و پایدار است", "interpretation": "خداوند حی و قیوم، منشأ حیات و بقای تمام موجودات است. پزشکان با این آیه، عظمت خالق حیات را درمی‌یابند.", "topics": ["توحید", "حیات", "بقا"]},
    {"index": 8, "surah": "بقره", "verse": 286, "text": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "trans": "خداوند هیچ‌کس را جز به اندازه توانش تکلیف نمی‌کند", "interpretation": "هیچ پزشک و پرستاری بیش از توانش مسئول نیست. این آیه برای کادر درمان که با فشار کاری روبرو هستند، آرامش‌بخش است.", "topics": ["توان", "مسئولیت", "آرامش"]},
    {"index": 9, "surah": "آل عمران", "verse": 139, "text": "وَلَا تَهِنُوا وَلَا تَحْزَنُوا وَأَنْتُمُ الْأَعْلَوْنَ إِنْ كُنْتُمْ مُؤْمِنِينَ", "trans": "سست نشوید و غمگین نگردید، که اگر مؤمن باشید شما برترید", "interpretation": "کادر درمان با ایمان به خدا، هرگز سست و غمگین نشوند. برتری مؤمنان در آرامش و امیدواری است.", "topics": ["امید", "ایمان", "قدرت"]},
    {"index": 10, "surah": "رعد", "verse": 28, "text": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ", "trans": "آگاه باشید که با یاد خدا دل‌ها آرام می‌گیرد", "interpretation": "پزشکان و پرستاران در شرایط استرس‌زا، با یاد خدا آرامش می‌یابند. این آیه نسخه شفابخش برای دل‌های پریشان است.", "topics": ["آرامش", "یاد خدا", "استرس"]},
]

DEFAULT_NAHJ_SEED = [
    {"index": 1, "type": "خطبه", "number": 1, "text": "الْحَمْدُ لِلَّهِ الَّذِی لَا یَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ", "trans": "ستایش خدایی را که سخنوران در ستودن او فرومانند", "interpretation": "عظمت خداوند فراتر از توصیف است. دانشمندان علوم پزشکی هرچه بیشتر به اسرار خلقت پی می‌برند، به عظمت خالق بیشتر پی می‌برند.", "topics": ["عظمت خدا", "ستایش"]},
    {"index": 2, "type": "حکمت", "number": 1, "text": "كُنْ فِي الْفِتْنَةِ كَابْنِ اللَّبُونِ لاَ ظَهْرٌ فَيُرْكَبَ، وَلاَ ضَرْعٌ فَيُحْلَبَ", "trans": "در فتنه‌ها چونان شتر دو ساله باش، نه پشتی دارد که سوار شوند و نه پستانی که بدوشند", "interpretation": "در بحران‌های پزشکی و اپیدمی‌ها، متواضع باش و خود را از حاشیه‌ها دور نگهدار.", "topics": ["فتنه", "تواضع", "بحران"]},
    {"index": 3, "type": "نامه", "number": 31, "text": "يَا بُنَيَّ اجْعَلْ نَفْسَكَ مِيزَاناً فِيما بَيْنَكَ وَبَيْنَ غَيْرِكَ", "trans": "پسرم، خویشتن را میان خود و دیگران ترازویی قرار ده", "interpretation": "پزشکان باید در برخورد با بیماران، عدالت را رعایت کنند و خود را معیار نیکی قرار دهند.", "topics": ["عدالت", "اخلاق", "رفتار"]},
]

DEFAULT_SAHIFEH_SEED = [
    {"index": 1, "dua": 1, "title": "در ستایش پروردگار", "text": "الْحَمْدُ لِلَّهِ الْأَوَّلِ بلا أَوَّلٍ كَانَ قَبْلَهُ", "trans": "ستایش خدای را که نخستین است و پیش از او نخستینی نبوده", "interpretation": "خداوند آغاز همه چیز است. دانشمندان با شناخت هرچه بیشتر خلقت، به عظمت خالق پی می‌برند.", "topics": ["ستایش", "خدا", "آغاز"]},
    {"index": 2, "dua": 20, "title": "دعای مکارم الاخلاق", "text": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَ آلِهِ ، وَ بَلِّغْ بِإِیمَانِی أَکْمَلَ الْإِیمَانِ", "trans": "بار خدایا بر محمد و آلش درود فرست، و ایمان مرا به کامل‌ترین مرتبه ایمان برسان", "interpretation": "ایمان کامل، آرامش قلبی و قدرت معنوی به پزشکان و پرستاران در مسیر درمان می‌دهد.", "topics": ["ایمان", "آرامش", "کمال"]},
]

# =========================================================
# ۴. داده‌های موضوعات قرآن (موتور جستجوی معنایی)
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
# ۵. احادیث و ذکر روزانه (توسعه‌یافته با تفسیر)
# =========================================================
HADITHS_WITH_DHIKR = [
    {"hadith": "بهترین شما کسی است که قرآن را بیاموزد و به دیگران یاد دهد. 🌸", "dhikr": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ (۱۰۰ بار)", "category": "آموزش", "interpretation": "پزشکان و اساتید دانشگاه، با آموزش علم و دانش به دیگران، در زمره بهترین‌ها قرار می‌گیرند.", "topics": ["آموزش", "علم", "یادگیری"]},
    {"hadith": "در قرآن بیندیشید که بهار دل‌هاست. ✨", "dhikr": "لَا إِلَٰهَ إِلَّا اللَّهُ (۱۰۰ بار)", "category": "تفکر", "interpretation": "تفکر در آیات قرآن، قلب دانشجویان و پزشکان را آرامش می‌بخشد و بهار دل‌هایشان است.", "topics": ["تفکر", "آرامش", "قرآن"]},
    {"hadith": "قرآن عهد الهی با بندگان است؛ شایسته است هر روز در آن نظر شود. 📖", "dhikr": "اللَّهُ أَكْبَرُ (۱۰۰ بار)", "category": "تلاوت", "interpretation": "پزشکان با تلاوت روزانه قرآن، یاد خدا را در قلب خود زنده نگه می‌دارند و با قدرت معنوی بیشتری به درمان می‌پردازند.", "topics": ["تلاوت", "قرآن", "یاد خدا"]},
    {"hadith": "خانه‌هایتان را با تلاوت قرآن نورانی کنید. 🕯️", "dhikr": "أَسْتَغْفِرُ اللَّهَ (۱۰۰ بار)", "category": "نورانی‌سازی", "interpretation": "اتاق عمل و بخش‌های بیمارستان، با تلاوت قرآن نورانی می‌شود و آرامش خاصی به بیماران می‌دهد.", "topics": ["نور", "قرآن", "آرامش"]},
    {"hadith": "هر کس قرآن را با صدای بلند بخواند، خداوند به او اجر شهید می‌دهد. 🌹", "dhikr": "سُبْحَانَ اللَّهِ وَالْحَمْدُ لِلَّهِ (۱۰۰ بار)", "category": "تلاوت", "interpretation": "پزشکانی که در مسیر درمان بیماران، قرآن می‌خوانند، اجر شهید دارند.", "topics": ["اجر", "شهادت", "قرآن"]},
    {"hadith": "مؤمنان در محبت و مهربانی مانند یک پیکرند. 💚", "dhikr": "اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَآلِ مُحَمَّدٍ (۱۰۰ بار)", "category": "اخوت", "interpretation": "کادر درمان با محبت و مهربانی به بیماران، مانند یک پیکر واحد عمل می‌کنند.", "topics": ["مهربانی", "اخوت", "همدلی"]},
    {"hadith": "نیکی را به نیکی پاداش نیست، بلکه به احسان است. 🌟", "dhikr": "سُبْحَانَ اللَّهِ الْعَظِیمِ (۱۰۰ بار)", "category": "اخلاق", "interpretation": "پزشکان و پرستاران با احسان و نیکی به بیماران، پاداشی بزرگ از خداوند دریافت می‌کنند.", "topics": ["نیکی", "احسان", "پاداش"]},
]

# =========================================================
# ۶. داده‌های مقالات محلی (برای زمان عدم دسترسی به API)
# =========================================================
LOCAL_ARTICLES = [
    {"title": "تفسیر سوره حمد", "summary": "بررسی جامع سوره حمد، بزرگترین سوره قرآن", "category": "تفسیر", "topics": ["تفسیر", "قرآن", "حمد"]},
    {"title": "اهمیت نماز در قرآن", "summary": "نقش نماز در زندگی فردی و اجتماعی از دیدگاه قرآن", "category": "عبادت", "topics": ["نماز", "عبادت", "قرآن"]},
    {"title": "تأثیر قرآن بر سلامت روان", "summary": "مطالعه تأثیر تلاوت قرآن بر کاهش استرس و اضطراب", "category": "پزشکی", "topics": ["سلامت", "روان", "استرس"]},
    {"title": "زنان در قرآن", "summary": "بررسی جایگاه و حقوق زنان در آیات قرآن", "category": "اجتماعی", "topics": ["زنان", "حقوق", "قرآن"]},
    {"title": "علم و دانش در قرآن", "summary": "نقش علم و تفکر در آیات الهی", "category": "علمی", "topics": ["علم", "دانش", "تفکر"]},
    {"title": "اخلاق پزشکی در اسلام", "summary": "بررسی اصول اخلاق پزشکی از منظر قرآن و حدیث", "category": "پزشکی", "topics": ["اخلاق", "پزشکی", "اسلام"]},
    {"title": "طب اسلامی و قرآن", "summary": "نقش قرآن در توسعه طب اسلامی", "category": "پزشکی", "topics": ["طب", "اسلام", "قرآن"]},
]

# =========================================================
# ۷. جوایز و عناوین کاربران (سیستم تشویقی)
# =========================================================
USER_TITLES = {
    0: "🌱 تازه‌کار قرآنی",
    50: "📖 قرآن‌خوان مبتدی",
    100: "🌟 نورانی",
    200: "💎 حافظ قرآن",
    350: "🕊️ عاشق قرآن",
    500: "🔥 مجتهد قرآنی",
    750: "👑 سلطان قرآن",
    1000: "🌹 پیشوای قرآنی"
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
# ۸. دکمه‌های جذاب برای کسب امتیاز
# =========================================================
QUEST_ACTIONS = [
    {"id": "quran_search", "label": "📖 جستجوی قرآن", "points": 3, "desc": "هر بار جستجو در قرآن"},
    {"id": "daily_visit", "label": "🌅 بازدید روزانه", "points": 5, "desc": "هر روز از ربات بازدید کن"},
    {"id": "feedback", "label": "📝 ارسال پیشنهاد", "points": 5, "desc": "پیشنهاد سازنده بده (حداکثر ۵ امتیاز)"},
    {"id": "hadith_read", "label": "🕊️ مطالعه حدیث", "points": 2, "desc": "حدیث روزانه را بخوان"},
    {"id": "instant_quran", "label": "✨ قرآن در لحظه", "points": 2, "desc": "آیه لحظه را دریافت کن"},
    {"id": "streak_7", "label": "🔥 ۷ روز پیاپی", "points": 15, "desc": "هفت روز متوالی بازدید کن"},
    {"id": "streak_30", "label": "⭐ ۳۰ روز پیاپی", "points": 30, "desc": "سی روز متوالی بازدید کن"},
    {"id": "referral", "label": "🤝 دعوت از دوستان", "points": 10, "desc": "هر دعوت ۱۰ امتیاز برای شما و دوستتان"},
]

# =========================================================
# ۹. توابع راه‌اندازی و مدیریت فایل‌های JSON
# =========================================================
def ensure_library_files():
    """ایجاد فایل‌های کتابخانه در صورت عدم وجود"""
    files_to_create = [
        (QURAN_FILE, DEFAULT_QURAN_SEED),
        (NAHJ_FILE, DEFAULT_NAHJ_SEED),
        (SAHIFEH_FILE, DEFAULT_SAHIFEH_SEED),
        (ARTICLES_FILE, {}),
        (TOPICS_FILE, DEFAULT_TOPICS)
    ]
    
    for file_path, default_data in files_to_create:
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
                logger.info(f"📁 فایل {file_path} ایجاد شد.")
            except Exception as e:
                logger.error(f"خطا در ایجاد فایل {file_path}: {e}")

def load_library():
    """بارگذاری تمام کتابخانه‌ها"""
    global QURAN_DATA, NAHJ_DATA, SAHIFEH_DATA, ARTICLE_CACHE, TOPICS_DATA
    
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
            
        logger.info(f"📚 کتابخانه بارگذاری شد: قرآن={len(QURAN_DATA)}, نهج={len(NAHJ_DATA)}, صحیفه={len(SAHIFEH_DATA)}, مقالات={len(ARTICLE_CACHE)}, موضوعات={len(TOPICS_DATA)}")
        
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
# ۱۰. مدیریت دیتابیس (توسعه‌یافته با سیستم دعوت)
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
    
    # جدول کاربران (توسعه‌یافته با سیستم دعوت)
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
            referral_earned INTEGER DEFAULT 0
        )
    """)
    
    # جدول وضعیت انتشار
    cur.execute("""
        CREATE TABLE IF NOT EXISTS publish_state (
            book_name TEXT PRIMARY KEY,
            last_index INTEGER DEFAULT 0,
            last_publish_date TEXT
        )
    """)
    
    # جدول محتوای در انتظار
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT,
            content_text TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    # جدول بازخوردها (توسعه‌یافته)
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
    
    # جدول پیام‌های ارسالی
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
    
    # جدول خطاها
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
    
    # جدول دستاوردهای کاربران
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            achievement_key TEXT,
            unlocked_at TEXT,
            UNIQUE(user_id, achievement_key)
        )
    """)
    
    # جدول یادآوری‌ها
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
    
    # جدول آمار پیشرفته
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            total_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            searches_count INTEGER DEFAULT 0,
            feedbacks_count INTEGER DEFAULT 0
        )
    """)
    
    # جدول بهترین کاربران
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
    
    # جدول کوئست‌های انجام شده
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quest_id TEXT,
            completed_at TEXT,
            UNIQUE(user_id, quest_id)
        )
    """)
    
    # جدول دعوت‌ها
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
    
    # مقداردهی اولیه publish_state
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
                   referral_code, referred_by, referral_count, referral_earned
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
                "referral_earned": row[19] or 0
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
        "referred_by": 0, "referral_count": 0, "referral_earned": 0
    }

def ensure_user(chat_id, name="", referred_by=None):
    """ثبت کاربر جدید با سیستم دعوت"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        
        # بررسی وجود کاربر
        cur.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        existing = cur.fetchone()
        
        if existing:
            conn.close()
            return
        
        # تولید کد دعوت
        referral_code = generate_referral_code()
        
        # ثبت کاربر
        cur.execute("""
            INSERT INTO users (chat_id, name, lang, join_date, last_active, 
                             total_visits, referral_code, referred_by)
            VALUES (?, ?, 'fa', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, ?, ?)
        """, (chat_id, name, referral_code, referred_by or 0))
        
        # اگر کاربر با دعوت آمده، امتیاز دهی
        if referred_by and FEATURES["referral_system"]:
            # ۱۰ امتیاز به کاربر جدید
            cur.execute("UPDATE users SET score = score + 10 WHERE chat_id = ?", (chat_id,))
            
            # ۱۰ امتیاز به کاربر دعوت‌کننده
            cur.execute("""
                UPDATE users 
                SET score = score + 10, referral_count = referral_count + 1,
                    referral_earned = referral_earned + 10
                WHERE chat_id = ?
            """, (referred_by,))
            
            # ثبت در جدول referrals
            cur.execute("""
                INSERT INTO referrals (referrer_id, referred_id, referral_code, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (referred_by, chat_id, referral_code))
            
            # اطلاع به دعوت‌کننده
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
        
        # اعتبارسنجی زبان
        if "lang" in kwargs and kwargs["lang"] not in ["fa", "en", "ar"]:
            kwargs["lang"] = "fa"
        
        # ساخت کوئری داینامیک
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ["name", "lang", "state", "achievements", "last_quest_date", "referral_code"]:
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
        
        # همیشه last_active رو به‌روزرسانی کن
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
    """دریافت لیگ قرآنی با کاربران فعال"""
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
        
        # اگر کاربری وجود نداشت، لیست نمونه برگردان
        if not users:
            logger.info("لیگ قرآنی خالی است، استفاده از داده‌های نمونه")
            return [
                ("امیرحسین", 150, 25, 7, 3),
                ("زهرا", 120, 20, 5, 2),
                ("محمد", 100, 18, 4, 1),
                ("سارا", 80, 15, 3, 0),
                ("علی", 60, 12, 2, 0)
            ]
        
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
# ۱۱. ابزارهای ارسال پیام به بله (با قابلیت Retry)
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
    
    # تقسیم متن طولانی
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
# ۱۲. توابع تاریخ شمسی (با fallback به میلادی)
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
    
    # Fallback به تاریخ میلادی
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
# ۱۳. سیستم چندزبانه (توسعه‌یافته با زبان عربی و فارسی‌محور)
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
        "about": "🌸 این ربات با عشق توسط کانون قرآن و عترت دانشگاه علوم پزشکی شیراز طراحی شده است.\n\n📚 امکانات:\n• جستجوی هوشمند قرآن با ترجمه و تفسیر 📖\n• موتور دانش اسلامی (Islamic Knowledge Engine) 🧠\n• هوش مصنوعی DeepSeek 🤖\n• مقالات علمی از گوگل اسکالر 📚\n• حدیث و ذکر روزانه با تفسیر 🕊️\n• قرآن در لحظه ✨\n• کارنامه و لیگ قرآنی 🏆\n• ارسال روزانه 🔔\n• ارسال پیشنهاد و انتقاد با امتیاز ⭐\n• کوئست‌های روزانه 🎯\n• بهترین کاربر روز و هفته 🏅\n• سیستم دعوت و پاداش 🤝\n• پشتیبانی از زبان عربی 🇸🇦\n• جستجوی معنایی (Semantic Search) 🔍\n\n💚 همراه همیشگی تو در مسیر نور",
        "daily_enable": "✅ دریافت روزانه فعال شد. هر روز با عشق محتوای جدید می‌فرستم.",
        "daily_disable": "❌ دریافت روزانه غیرفعال شد. هر وقت خواستی فعالش کن.",
        "daily_toggle": "🔔 دریافت روزانه",
        "back_to_menu": "🏠 برگشت به منوی اصلی",
        "search_quran_prompt": "📖 کلمه یا عبارت قرآنی موردنظرت رو بفرست تا با عشق جستجو کنیم.",
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
            "about": "ℹ️ درباره ربات",
            "help": "❓ راهنما",
            "share": "📤 اشتراک‌گذاری",
            "reminder": "⏰ یادآوری",
            "quests": "🎯 کوئست‌های روزانه",
            "best_users": "🏅 بهترین کاربران",
            "referral": "🤝 دعوت از دوستان",
            "islamic_engine": "🧠 موتور دانش اسلامی"
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
        "about": "🌸 This bot is designed with love by the Quran & Etrat Center of Shiraz University of Medical Sciences.\n\n📚 Features:\n• Smart Quran Search with interpretation 📖\n• Islamic Knowledge Engine 🧠\n• AI Assistant 🤖\n• Scientific Articles from Google Scholar 📚\n• Hadith & Dhikr with interpretation 🕊️\n• Instant Quran ✨\n• Scorecard & Quran League 🏆\n• Daily Receive 🔔\n• Suggestion & Critique with points ⭐\n• Daily Quests 🎯\n• Best Users of the Day/Week 🏅\n• Referral System 🤝\n• Arabic Language Support 🇸🇦\n• Semantic Search 🔍",
        "daily_enable": "✅ Daily receive enabled.",
        "daily_disable": "❌ Daily receive disabled.",
        "daily_toggle": "🔔 Daily Receive",
        "back_to_menu": "🏠 Back to main menu",
        "search_quran_prompt": "📖 Send a Quranic word or phrase to search.",
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
            "about": "ℹ️ About Bot",
            "help": "❓ Help",
            "share": "📤 Share",
            "reminder": "⏰ Reminder",
            "quests": "🎯 Daily Quests",
            "best_users": "🏅 Best Users",
            "referral": "🤝 Invite Friends",
            "islamic_engine": "🧠 Islamic Knowledge Engine"
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
        "about": "🌸 تم تصميم هذا البوت بحب من قبل مركز القرآن والعترة بجامعة علوم الطب شيراز.\n\n📚 الميزات:\n• البحث الذكي في القرآن مع الترجمة والتفسير 📖\n• محرك المعرفة الإسلامية 🧠\n• المساعد الذكي 🤖\n• المقالات العلمية من جوجل سكولار 📚\n• الحديث والذكر اليومي مع التفسير 🕊️\n• القرآن في لحظة ✨\n• بطاقة النتائج والدوري القرآني 🏆\n• الاستلام اليومي 🔔\n• الاقتراحات والنقد مع النقاط ⭐\n• المهام اليومية 🎯\n• أفضل مستخدمي اليوم والأسبوع 🏅\n• نظام الدعوة والمكافآت 🤝\n• دعم اللغة العربية 🇸🇦\n• البحث الدلالي 🔍",
        "daily_enable": "✅ تم تفعيل الاستلام اليومي.",
        "daily_disable": "❌ تم تعطيل الاستلام اليومي.",
        "daily_toggle": "🔔 الاستلام اليومي",
        "back_to_menu": "🏠 العودة إلى القائمة الرئيسية",
        "search_quran_prompt": "📖 أرسل كلمة أو عبارة قرآنية للبحث.",
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
        "menu_labels": {
            "search_quran": "📖 البحث في القرآن",
            "ai": "🤖 المساعد الذكي",
            "articles": "📚 المقالات العلمية",
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
            "islamic_engine": "🧠 محرك المعرفة الإسلامية"
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
# ۱۴. موتور دانش اسلامی (Islamic Knowledge Engine)
# =========================================================
def expand_topic(query):
    """توسعه موضوع با مترادف‌ها و کلمات کلیدی"""
    query_lower = query.lower()
    expanded_terms = [query_lower]
    
    # بررسی در دیکشنری موضوعات
    for topic, data in TOPICS_DATA.items():
        if query_lower in data.get("synonyms", []):
            expanded_terms.extend(data.get("keywords", []))
            expanded_terms.extend(data.get("synonyms", []))
            break
    
    return list(set(expanded_terms))

def semantic_search(query):
    """جستجوی معنایی در تمام منابع اسلامی"""
    if not FEATURES["semantic_search"]:
        return None
    
    expanded_terms = expand_topic(query)
    results = {
        "quran": [],
        "nahj": [],
        "sahifeh": [],
        "hadith": [],
        "articles": []
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
            str(item.get("interpretation", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
        for term in expanded_terms:
            if term in search_text:
                results["hadith"].append(item)
                break
    
    # جستجو در مقالات
    for item in LOCAL_ARTICLES:
        search_text = " ".join([
            str(item.get("title", "")),
            str(item.get("summary", "")),
            str(item.get("category", "")),
            " ".join(item.get("topics", []))
        ]).lower()
        
        for term in expanded_terms:
            if term in search_text:
                results["articles"].append(item)
                break
    
    # محدود کردن نتایج
    results["quran"] = results["quran"][:3]
    results["nahj"] = results["nahj"][:2]
    results["sahifeh"] = results["sahifeh"][:2]
    results["hadith"] = results["hadith"][:2]
    results["articles"] = results["articles"][:2]
    
    return results

def format_semantic_results(results, query, lang="fa"):
    """فرمت‌بندی نتایج جستجوی معنایی"""
    if not results:
        return f"🔍 نتیجه‌ای برای «{query}» در منابع اسلامی یافت نشد.\n\n💡 سعی کنید با کلمات کلیدی دیگری جستجو کنید."
    
    output = f"""🧠 <b>موتور دانش اسلامی - جستجوی «{query}»</b>
{'='*50}

"""
    
    # قرآن
    if results["quran"]:
        output += "📖 <b>آیات مرتبط در قرآن:</b>\n\n"
        for i, item in enumerate(results["quran"][:3], 1):
            output += f"{i}. <b>{item['surah']} (آیه {item['verse']})</b>\n"
            output += f"   {item['text'][:50]}...\n"
            output += f"   ✨ {item['trans'][:50]}...\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation'][:50]}...\n"
            output += "\n"
    
    # نهج‌البلاغه
    if results["nahj"]:
        output += "📜 <b>فرازهایی از نهج‌البلاغه:</b>\n\n"
        for i, item in enumerate(results["nahj"][:2], 1):
            output += f"{i}. <b>{item['type']} {item['number']}</b>\n"
            output += f"   {item['text'][:50]}...\n"
            output += f"   ✨ {item['trans'][:50]}...\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation'][:50]}...\n"
            output += "\n"
    
    # صحیفه سجادیه
    if results["sahifeh"]:
        output += "🤲 <b>دعاهایی از صحیفه سجادیه:</b>\n\n"
        for i, item in enumerate(results["sahifeh"][:2], 1):
            output += f"{i}. <b>{item['title']}</b>\n"
            output += f"   {item['text'][:50]}...\n"
            output += f"   ✨ {item['trans'][:50]}...\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation'][:50]}...\n"
            output += "\n"
    
    # احادیث
    if results["hadith"]:
        output += "🕊️ <b>احادیث مرتبط:</b>\n\n"
        for i, item in enumerate(results["hadith"][:2], 1):
            output += f"{i}. {item['hadith'][:50]}...\n"
            if item.get('interpretation'):
                output += f"   💡 {item['interpretation'][:50]}...\n"
            output += "\n"
    
    # مقالات
    if results["articles"]:
        output += "📚 <b>مقالات مرتبط:</b>\n\n"
        for i, item in enumerate(results["articles"][:2], 1):
            output += f"{i}. <b>{item['title']}</b>\n"
            output += f"   📝 {item['summary'][:50]}...\n"
            output += f"   🏷️ دسته: {item['category']}\n"
            output += "\n"
    
    output += "💡 <b>پیشنهاد:</b> برای دریافت تحلیل عمیق‌تر، از بخش «هوش مصنوعی» استفاده کنید."
    
    return output

# =========================================================
# ۱۵. جستجوی کامل قرآن و کتاب‌ها (با تفسیر)
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
    
    # حذف موارد تکراری
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
    
    # جستجو در نهج‌البلاغه
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
    
    # جستجو در صحیفه سجادیه
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
    
    # حذف موارد تکراری
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
# ۱۶. جستجوی مقالات از گوگل اسکالر
# =========================================================
def search_articles(query):
    """جستجوی مقالات با استفاده از Google Scholar و OpenAlex"""
    if not FEATURES["articles_search"]:
        return "🔧 این ویژگی در حال حاضر غیرفعال است."
    
    query = query.strip()
    if not query or len(query) < 2:
        return "🔍 لطفاً عبارت جستجو را دقیق‌تر وارد کنید."
    
    # چک کردن کش
    cache_key = hashlib.md5(query.encode()).hexdigest()
    if cache_key in ARTICLE_CACHE:
        logger.info(f"مقاله از کش: {query}")
        return ARTICLE_CACHE[cache_key]
    
    results = []
    
    try:
        # تلاش برای جستجو در OpenAlex (که شامل مقالات گوگل اسکالر هم می‌شود)
        url = f"https://api.openalex.org/works?search={query.replace(' ', '+')}&per-page=5&filter=topics.id:T10194,T10195,T10196"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            for work in data.get("results", []):
                title = work.get("title", "")
                doi = work.get("doi", "")
                link = f"https://doi.org/{doi}" if doi else ""
                year = work.get("publication_year", "")
                abstract = work.get("abstract", "")
                
                if title:
                    result_text = f"📄 <b>{title}</b>"
                    if year:
                        result_text += f" ({year})"
                    if abstract:
                        result_text += f"\n📝 {abstract[:200]}..."
                    if link:
                        result_text += f"\n🔗 <a href='{link}'>{link}</a>"
                    results.append(result_text)
        
        # اگر نتیج‌های نیافت یا خطا بود، از مقالات محلی استفاده کن
        if not results:
            return search_local_articles(query)
        
        final_result = '\n\n'.join(results)
        # ذخیره در کش
        ARTICLE_CACHE[cache_key] = final_result
        save_library_file(ARTICLES_FILE, ARTICLE_CACHE)
        return final_result
        
    except Exception as e:
        logger.error(f"خطا در جستجوی مقالات: {e}")
        return search_local_articles(query)

def search_local_articles(query):
    """جستجو در مقالات محلی به عنوان پشتیبان"""
    query = query.lower()
    results = []
    
    # اولویت با مقالات پزشکی و قرآنی
    priority_articles = [a for a in LOCAL_ARTICLES if "پزشکی" in a["category"] or "تفسیر" in a["category"]]
    other_articles = [a for a in LOCAL_ARTICLES if a not in priority_articles]
    
    all_articles = priority_articles + other_articles
    
    for article in all_articles:
        if query in article["title"].lower() or query in article["category"].lower():
            results.append(f"📄 <b>{article['title']}</b>\n📝 {article['summary']}\n🏷️ دسته: {article['category']}")
    
    if results:
        return "📚 مقالات پیشنهادی:\n\n" + '\n\n'.join(results[:3])
    
    # اگر هیچ نتیج‌های نیافت
    return """🔍 نتیجه‌ای برای جستجوی شما پیدا نشد.

📚 پیشنهاد می‌کنم این مقالات رو مطالعه کنی:
• تفسیر سوره حمد
• اهمیت نماز در قرآن
• تأثیر قرآن بر سلامت روان
• اخلاق پزشکی در اسلام
• طب اسلامی و قرآن

💡 یا با کلمات کلیدی دیگه جستجو کن."""

# =========================================================
# ۱۷. سیستم پاداش و امتیازدهی هوشمند
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
        "semantic_search": {"points": 5, "emoji": "🧠"}
    }
    
    reward = rewards.get(action, {"points": 1, "emoji": "🌸"})
    points = reward["points"]
    emoji = reward["emoji"]
    
    # پاداش روزهای پیاپی
    if user_data.get("streak", 0) >= 7:
        points += 5
        emoji = "🔥"
    
    return points, emoji

def update_user_score(chat_id, action, user_data):
    """به‌روزرسانی امتیاز کاربر با اعمال پاداش"""
    points, emoji = calculate_reward(action, user_data)
    
    if points > 0:
        update_user(chat_id, score=points)
        
        # بروزرسانی استریک
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
    
    # بررسی دستاوردها
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
    
    # دستاوردهای مختلف
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
    if action == "semantic_search":
        achievements.append("knowledge_seeker")
    
    # ذخیره دستاوردها
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
# ۱۸. سیستم کوئست‌های روزانه
# =========================================================
def complete_quest(chat_id, quest_id, user_data):
    """انجام کوئست و دریافت امتیاز"""
    try:
        # بررسی آیا کوئست قبلاً انجام شده
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
        
        # ثبت کوئست
        cur.execute("""
            INSERT INTO user_quests (user_id, quest_id, completed_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (chat_id, quest_id))
        conn.commit()
        conn.close()
        
        # اعمال امتیاز
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
# ۱۹. سیستم بهترین کاربر روز و هفته
# =========================================================
def get_best_user(period_type):
    """دریافت بهترین کاربر روز یا هفته"""
    try:
        conn = db_conn()
        cur = conn.cursor()
        
        if period_type == "daily":
            # بهترین کاربر امروز
            today = datetime.now().date().isoformat()
            cur.execute("""
                SELECT user_id, user_name, score, period_date 
                FROM best_users 
                WHERE period_type = 'daily' AND period_date = ?
                ORDER BY score DESC 
                LIMIT 1
            """, (today,))
        else:
            # بهترین کاربر هفته (جمعه)
            today = datetime.now().date()
            days_since_friday = (today.weekday() - 4) % 7
            last_friday = today - timedelta(days=days_since_friday)
            
            cur.execute("""
                SELECT user_id, user_name, score, period_date 
                FROM best_users 
                WHERE period_type = 'weekly'
                ORDER BY created_at DESC 
                LIMIT 1
            """)
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                "user_id": row[0],
                "user_name": row[1],
                "score": row[2],
                "date": row[3]
            }
        
        # اگر کاربری وجود نداشت، بهترین کاربر از بین کاربران واقعی
        users = get_leaderboard(1)
        if users:
            return {
                "user_id": None,
                "user_name": users[0][0],
                "score": users[0][1],
                "date": datetime.now().date().isoformat()
            }
        
        return None
    except Exception as e:
        logger.error(f"خطا در دریافت بهترین کاربر: {e}")
        return None

def save_best_user(period_type):
    """ذخیره بهترین کاربر روز یا هفته"""
    try:
        # دریافت کاربر با بیشترین امتیاز امروز
        conn = db_conn()
        cur = conn.cursor()
        
        if period_type == "daily":
            # بهترین کاربر امروز
            cur.execute("""
                SELECT chat_id, name, score 
                FROM users 
                WHERE last_active > datetime('now', '-1 day')
                ORDER BY score DESC 
                LIMIT 1
            """)
        else:
            # بهترین کاربر هفته
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
            
            # ذخیره در دیتابیس
            cur.execute("""
                INSERT INTO best_users (user_id, user_name, score, period_type, period_date, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (chat_id, name, score, period_type, period_date))
            
            conn.commit()
            
            # ارسال پیام به کانال
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
            logger.info(f"بهترین کاربر {period_type} ذخیره شد: {name} با {score} امتیاز")
        
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره بهترین کاربر: {e}")

def schedule_best_users():
    """برنامه‌ریزی برای ثبت بهترین کاربران"""
    while True:
        try:
            now = datetime.now()
            
            # هر شب ساعت ۲۳:۵۹ بهترین کاربر روز
            if now.hour == 23 and now.minute == 59 and FEATURES["best_user_daily"]:
                save_best_user("daily")
                logger.info("بهترین کاربر روز ثبت شد.")
                time.sleep(60)
            
            # هر جمعه ساعت ۲۳:۵۹ بهترین کاربر هفته
            if now.weekday() == 4 and now.hour == 23 and now.minute == 59 and FEATURES["best_user_weekly"]:
                save_best_user("weekly")
                logger.info("بهترین کاربر هفته ثبت شد.")
                time.sleep(60)
            
            time.sleep(30)
        except Exception as e:
            logger.error(f"خطا در برنامه‌ریزی بهترین کاربران: {e}")
            time.sleep(60)

# =========================================================
# ۲۰. سیستم ارسال روزانه با تفسیر هوشمند
# =========================================================
def get_daily_interpretation(text, lang="fa"):
    """دریافت تفسیر هوشمند برای متن با استفاده از DeepSeek"""
    try:
        if not DEEPSEEK_KEY or len(DEEPSEEK_KEY) < 10:
            return "تفسیر: این آیه/حدیث یادآور اهمیت ایمان و عمل صالح در زندگی است."
        
        language_name = {"fa": "Persian", "en": "English", "ar": "Arabic"}.get(lang, "Persian")
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Provide a brief, profound interpretation (1-3 sentences) of this Islamic text for medical professionals and students. Make it thoughtful and impactful:

Text: {text}

Reply in {language_name}. Keep it short, meaningful, and relevant to healthcare workers. Focus on the spiritual and ethical lessons that can be applied in medical practice and daily life."""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 150
        }
        
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
        
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
        
        return "تفسیر: این متن ارزشمند، یادآور اهمیت ایمان و عمل صالح در مسیر زندگی است."
    except Exception as e:
        logger.error(f"خطا در دریافت تفسیر: {e}")
        return "تفسیر: این متن ارزشمند، یادآور اهمیت ایمان و عمل صالح در مسیر زندگی است."

def send_daily_posts():
    """ارسال محتوای روزانه در ۳ زمان مشخص با تفسیر هوشمند"""
    try:
        if not FEATURES["daily_posts"]:
            return
        
        now = datetime.now()
        
        # زمان‌های ارسال: ۸ صبح، ۱۲ ظهر، ۱۸ عصر
        scheduled_times = [
            (8, 0, "صبح 🌅"),
            (12, 0, "ظهر ☀️"),
            (18, 0, "عصر 🌇")
        ]
        
        for hour, minute, time_name in scheduled_times:
            if now.hour == hour and now.minute == minute:
                logger.info(f"🔄 شروع ارسال پست روزانه - {time_name}")
                
                # ۱. آیه روز از قرآن با تفسیر
                q_item, q_idx = next_item("quran", QURAN_DATA)
                q_msg = ""
                if q_item:
                    # دریافت تفسیر هوشمند
                    interpretation = q_item.get('interpretation', '')
                    if not interpretation or len(interpretation) < 10:
                        interpretation = get_daily_interpretation(q_item['text'], "fa")
                    
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
                
                # ۲. حدیث روز با تفسیر
                hadith_item = random.choice(HADITHS_WITH_DHIKR)
                hadith_interpretation = hadith_item.get('interpretation', '')
                if not hadith_interpretation or len(hadith_interpretation) < 10:
                    hadith_interpretation = get_daily_interpretation(hadith_item['hadith'], "fa")
                
                hadith_topics = ', '.join(hadith_item.get('topics', ['عمومی']))
                
                hadith_msg = f"""🕊️ <b>حدیث روز</b>

{hadith_item['hadith']}

🔹 <b>ذکر روزانه:</b>
{hadith_item['dhikr']}

💡 <b>تفسیر:</b> {hadith_interpretation}

🏷️ دسته: {hadith_item['category']}
🏷️ موضوعات: {hadith_topics}

💚 با یاد خدا دل‌ها آرام می‌گیرد."""
                
                send_message(CHANNEL_ID, hadith_msg)
                save_sent_message("daily_hadith", hadith_msg, CHANNEL_ID)
                logger.info(f"حدیث روزانه با تفسیر ارسال شد - {time_name}")
                time.sleep(2)
                
                # ۳. ارسال به کاربرانی که دریافت روزانه فعال دارند
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

🙏 از همراهی شما سپاسگزاریم.
🕌 با ما در مسیر نور همراه باش."""
                            
                            send_message(user[0], daily_msg)
                            sent_count += 1
                            time.sleep(0.2)
                            
                            # هر ۱۰ پیام یک مکث کوتاه
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
# ۲۱. مدیریت پردازش وضعیت‌های خاص کاربر (توسعه‌یافته)
# =========================================================
def handle_state_message(chat_id, text, user):
    """پردازش پیام‌های وضعیت‌دار کاربر"""
    lang = user["lang"]
    state = user["state"]
    name = user["name"] or "کاربر گرامی"

    # وضعیت هوش مصنوعی
    if state == "waiting_ai":
        send_message(chat_id, safe_text(lang, "ai_wait"))
        answer = ask_deepseek(text, lang)
        send_message(chat_id, f"🤖 {answer}", main_menu(chat_id, lang))
        update_user(chat_id, state="none", score=2)
        update_user_score(chat_id, "ai_question", user)
        return True

    # وضعیت پیام به ادمین
    if state == "waiting_admin_msg":
        try:
            # ارسال به ادمین با فرمت صحیح
            admin_text = f"""📩 <b>پیام جدید از کاربر</b>

👤 نام: {name}
🆔 chat_id: {chat_id}
📝 امتیاز: {user.get('score', 0)}

💬 متن:
{text}"""
            
            # ارسال با retry
            result = send_message_with_retry(ADMIN_ID, admin_text)
            if result and result.get("ok"):
                send_message(chat_id, safe_text(lang, "admin_msg_sent"), main_menu(chat_id, lang))
                logger.info(f"پیام کاربر {chat_id} به ادمین ارسال شد.")
            else:
                send_message(chat_id, "⚠️ متأسفانه پیام شما ارسال نشد. لطفاً دوباره تلاش کنید.", main_menu(chat_id, lang))
                logger.error(f"ارسال پیام به ادمین ناموفق: {result}")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام به ادمین: {e}")
            send_message(chat_id, "⚠️ خطا در ارسال پیام. لطفاً دوباره تلاش کنید.", main_menu(chat_id, lang))
        
        update_user(chat_id, state="none")
        return True

    # وضعیت جستجوی قرآن (با پشتیبانی از Semantic Search)
    if state == "waiting_quran_search":
        send_chat_action(chat_id, "typing")
        
        # بررسی آیا متن طولانی است و نیاز به Semantic Search دارد
        if len(text.split()) <= 5 and text in TOPICS_DATA:
            # جستجوی معنایی با موتور دانش اسلامی
            results = semantic_search(text)
            if results:
                formatted_result = format_semantic_results(results, text, lang)
                send_message(chat_id, formatted_result, main_menu(chat_id, lang))
                update_user(chat_id, state="none", score=2)
                update_user_score(chat_id, "semantic_search", user)
                return True
        
        # جستجوی عادی
        results = search_quran_only(text)
        
        if results:
            msg = "📖 <b>نتایج جستجو در قرآن:</b>\n\n"
            for i, item in enumerate(results[:5], 1):
                msg += f"{i}. {format_search_result(item, 'قرآن')}\n\n"
            
            # اضافه کردن پیشنهاد برای جستجوی بیشتر
            if len(results) > 5:
                msg += f"\n📌 {len(results)-5} نتیجه دیگر یافت شد. برای مشاهده بیشتر، جستجوی دقیق‌تری انجام دهید."
            
            send_message(chat_id, msg, main_menu(chat_id, lang))
            update_user(chat_id, score=1, search_count=1)
            update_user_score(chat_id, "quran_search", user)
        else:
            # جستجو در سایر کتاب‌ها
            other_results = search_other_books(text)
            if other_results:
                msg = "📚 <b>در قرآن یافت نشد، اما در سایر کتاب‌ها:</b>\n\n"
                for i, item in enumerate(other_results[:3], 1):
                    book_type = item.get("book_type", "نهج‌البلاغه")
                    msg += f"{i}. {format_search_result(item, book_type)}\n\n"
                send_message(chat_id, msg, main_menu(chat_id, lang))
            else:
                # پیشنهاد کلمات کلیدی
                suggestions = "💡 کلمات کلیدی پیشنهادی:\n• ایمان\n• صبر\n• نماز\n• توکل\n• رحمت\n• پزشکی\n• سلامت"
                send_message(
                    chat_id,
                    f"😔 نتیجه‌ای برای عبارت «{text}» پیدا نشد.\n\n{suggestions}",
                    main_menu(chat_id, lang)
                )
        update_user(chat_id, state="none")
        return True

    # وضعیت مقالات علمی
    if state == "waiting_article":
        send_chat_action(chat_id, "typing")
        send_message(chat_id, "📚 در حال جستجوی مقالات از گوگل اسکالر...")
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
        
        # امتیازدهی هوشمند (حداکثر ۵ امتیاز)
        score = 0
        category = "general"
        
        # تشخیص دسته‌بندی
        if "قرآن" in text or "ترجمه" in text or "آیه" in text:
            category = "quran"
            score += 1
        elif "حدیث" in text or "روایت" in text:
            category = "hadith"
            score += 1
        elif "ربات" in text or "بات" in text or "گزارش" in text:
            category = "bot"
            score += 1
        elif "پیشنهاد" in text:
            category = "suggestion"
            score += 2
        elif "انتقاد" in text or "مشکل" in text:
            category = "critique"
            score += 2
        
        # امتیاز بر اساس طول متن و محتوا (حداکثر ۵)
        if len(text) > 50:
            score += 2
        if len(text) > 100:
            score += 1
        if "لطفا" in text or "متشکرم" in text or "ممنون" in text:
            score += 1
        if "عالی" in text or "خوب" in text or "قشنگ" in text:
            score += 1
        
        # حداکثر امتیاز ۵
        score = min(score, 5)
        
        try:
            conn = db_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO feedbacks (user_id, user_name, type, content, score, created_at, category)
                VALUES (?, ?, 'suggestion', ?, ?, CURRENT_TIMESTAMP, ?)
            """, (chat_id, name, text, score, category))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطا در ذخیره پیشنهاد: {e}")
        
        # اعمال امتیاز
        if score >= 3:
            update_user(chat_id, score=score, feedback_score=score)
            send_message(chat_id, safe_text(lang, "feedback_score_msg", score=score), main_menu(chat_id, lang))
            
            # ارسال به ادمین
            send_message_with_retry(ADMIN_ID, f"""📩 <b>پیشنهاد جدید</b>

👤 {name} (امتیاز: {user.get('score', 0)})
📝 {text}
⭐ امتیاز: {score}
🏷️ دسته: {category}""")
        else:
            send_message(chat_id, safe_text(lang, "feedback_no_score"), main_menu(chat_id, lang))
            send_message_with_retry(ADMIN_ID, f"📩 پیشنهاد جدید:\n👤 {name}\n📝 {text}\n⭐ امتیاز: {score}")
        
        update_user_score(chat_id, "feedback", user)
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
        failed = 0
        
        for uid, uname, uscore in users:
            try:
                send_message(
                    int(uid),
                    f"""📢 <b>اطلاعیه کانون قرآن و عترت</b>

{text}

🙏 از همراهی شما سپاسگزاریم.
🕌 با ما در مسیر نور همراه باش."""
                )
                count += 1
                time.sleep(0.15)
            except Exception as e:
                logger.error(f"خطا در ارسال به {uid}: {e}")
                failed += 1
        
        save_sent_message("broadcast", text, f"{count} users, {failed} failed")
        send_message(chat_id, safe_text(lang, "broadcast_success", count=count), admin_menu(chat_id, lang))
        return True

    # وضعیت یادآوری
    if state == "waiting_reminder":
        # ذخیره یادآوری
        try:
            conn = db_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO reminders (user_id, reminder_text, remind_at, created_at)
                VALUES (?, ?, datetime('now', '+1 day'), CURRENT_TIMESTAMP)
            """, (chat_id, text))
            conn.commit()
            conn.close()
            
            send_message(
                chat_id,
                f"✅ یادآوری با موفقیت ثبت شد:\n\n📝 {text}\n\n⏰ فردا در همین ساعت بهت یادآوری می‌کنم.",
                main_menu(chat_id, lang)
            )
        except Exception as e:
            logger.error(f"خطا در ثبت یادآوری: {e}")
            send_message(chat_id, "⚠️ خطا در ثبت یادآوری. لطفاً دوباره تلاش کنید.", main_menu(chat_id, lang))
        
        update_user(chat_id, state="none")
        return True

    return False

# =========================================================
# ۲۲. توابع کمکی (توسعه‌یافته)
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
# ۲۳. مسیرهای تست و سلامت (توسعه‌یافته)
# =========================================================
@app.route("/", methods=["GET", "HEAD"])
def health():
    """بررسی سلامت ربات"""
    return jsonify({
        "status": "ok",
        "service": "labbayk_quranbot",
        "version": "9.0",
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
        "semantic_search": FEATURES["semantic_search"],
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
# ۲۴. وب هوک و مدیریت یکپارچه درخواست‌ها (توسعه‌یافته)
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
            
            # پردازش کد دعوت در start (برای بله)
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
                            # ثبت کاربر با دعوت
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

            # پردازش دستور /start
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
                if not check_membership(chat_id):
                    send_message(
                        chat_id,
                        safe_text(lang, "force_join", name=first_name, channel=CHANNEL_ID),
                        join_keyboard()
                    )
                    return "OK", 200

            # پردازش وضعیت‌های خاص
            try:
                handled = handle_state_message(chat_id, text, user)
                if handled:
                    return "OK", 200
            except Exception as e:
                logger.error(f"خطا در پردازش وضعیت: {e}")
                send_message(chat_id, "⚠️ خطایی در پردازش پیام رخ داد. لطفاً دوباره تلاش کنید.")
                update_user(chat_id, state="none")
                return "OK", 200

            # نمایش منوی اصلی با پیام خوش‌آمدگویی پویا
            greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
            
            # دریافت عنوان کاربر
            title = get_user_title(user.get("score", 0))
            
            if lang == "fa":
                welcome_text = f"""{greeting}

{first_name} جان! 😍

به ربات کانون قرآن و عترت دانشگاه علوم پزشکی شیراز خوش آمدی.
👑 عنوان شما: {title}

✨ اینجا همراه همیشگی تو در مسیر نور و معرفت است:
• جستجوی هوشمند قرآن با ترجمه و تفسیر 📖
• موتور دانش اسلامی (Islamic Knowledge Engine) 🧠
• هوش مصنوعی پاسخ‌گو 🤖
• مقالات علمی از گوگل اسکالر 📚
• حدیث و ذکر روزانه با تفسیر 🕊️
• قرآن در لحظه با ترجمه ✨
• پیشنهاد و انتقاد با امتیاز ⭐
• کوئست‌های روزانه 🎯
• سیستم دعوت و پاداش 🤝

👇 از منوی زیبای زیر استفاده کن:"""
            else:
                welcome_text = safe_text(lang, "welcome", name=first_name)
            
            send_message(chat_id, welcome_text, main_menu(chat_id, lang))
            
            # به‌روزرسانی آمار بازدید
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
                    greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
                    title = get_user_title(user.get("score", 0))
                    if lang == "fa":
                        welcome_text = f"{greeting}\n\n{first_name} جان! 😍\n\nبه ربات کانون قرآن و عترت خوش آمدی.\n👑 عنوان: {title}\n\nاز منوی زیر استفاده کن:"
                    else:
                        welcome_text = safe_text(lang, "welcome", name=first_name)
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
                greeting = get_persian_greeting() if lang == "fa" else get_greeting(lang)
                title = get_user_title(user.get("score", 0))
                if lang == "fa":
                    send_message(
                        chat_id,
                        f"{greeting}\n\n{first_name} جان! 🍃\nبه منوی اصلی خوش اومدی.\n👑 عنوان: {title}",
                        main_menu(chat_id, lang)
                    )
                else:
                    send_message(
                        chat_id,
                        f"{greeting}\n\n{safe_text(lang, 'back_to_menu')}",
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
            # موتور دانش اسلامی
            # ===========================
            if cb_data == "menu_islamic_engine":
                if lang == "fa":
                    msg = """🧠 <b>موتور دانش اسلامی (Islamic Knowledge Engine)</b>

این موتور هوشمند، جستجوی شما را در تمام منابع اسلامی انجام می‌دهد:

📖 <b>قرآن کریم</b> - آیات مرتبط با تفسیر
📜 <b>نهج‌البلاغه</b> - خطبه‌ها، نامه‌ها و حکمت‌ها
🤲 <b>صحیفه سجادیه</b> - دعاهای نورانی
🕊️ <b>احادیث</b> - روایات معصومین
📚 <b>مقالات علمی</b> - از گوگل اسکالر

🔍 <b>چگونه کار می‌کند؟</b>
• هر کلمه یا موضوعی را وارد کنید
• ربات مترادف‌ها و کلمات کلیدی را تشخیص می‌دهد
• در همه منابع جستجو می‌کند
• نتایج را به صورت دسته‌بندی شده نمایش می‌دهد

💡 <b>مثال‌ها:</b>
• «صبر» → آیات صبر، روایات صبر، مقالات مرتبط
• «استرس» → آیات آرامش، دعاهای مرتبط، مقالات روانشناسی
• «امید» → آیات امید، حکمت‌های امید، مقالات امیدواری

📝 <b>کافی است موضوع مورد نظر خود را در بخش «جستجوی قرآن» وارد کنید.</b>

🌟 این موتور، ربات را از یک جستجوگر به یک دستیار پژوهشی اسلامی تبدیل می‌کند."""
                else:
                    msg = safe_text(lang, "islamic_engine_info", default="🧠 Islamic Knowledge Engine\n\nSearch in Quran, Nahjolbalagheh, Sahifeh Sajjadieh, Hadiths and Articles.")
                
                send_message(chat_id, msg, main_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # سیستم دعوت
            # ===========================
            if cb_data == "menu_referral":
                referral_code = user.get("referral_code", "")
                if not referral_code:
                    # تولید کد دعوت جدید
                    referral_code = generate_referral_code()
                    update_user(chat_id, referral_code=referral_code)
                
                msg = f"""🤝 <b>سیستم دعوت از دوستان</b>

🌟 کد دعوت شما: <code>{referral_code}</code>

🎁 با دعوت از دوستان:
• به شما و دوستتان ۱۰ امتیاز هدیه داده می‌شود
• با هر دعوت، یک کوئست جدید فعال می‌شود
• پس از ۵ دعوت، عنوان «🥉 دعوت‌کننده برنزی» دریافت می‌کنید

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
                
                # لینک دعوت برای بله
                referral_link = f"https://ble.ir/{BOT_USERNAME}?start=ref_{referral_code}"
                send_message(
                    chat_id,
                    f"📋 <b>لینک دعوت شما:</b>\n\n{referral_link}\n\n🌸 این لینک رو با دوستانت به اشتراک بذار!",
                    referral_keyboard(lang, referral_code)
                )
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
• ۲۰ دعوت: 🥇 دعوت‌کننده طلایی

💪 به دعوت از دوستان ادامه بده!"""
                
                referral_code = user.get("referral_code", "")
                if not referral_code:
                    referral_code = generate_referral_code()
                    update_user(chat_id, referral_code=referral_code)
                
                send_message(chat_id, msg, referral_keyboard(lang, referral_code))
                return "OK", 200

            # ===========================
            # کوئست‌های روزانه
            # ===========================
            if cb_data.startswith("quest_"):
                quest_id = cb_data.replace("quest_", "")
                
                if quest_id == "referral":
                    # کوئست دعوت: بررسی اینکه آیا کاربر امروز دعوت داشته
                    try:
                        conn = db_conn()
                        cur = conn.cursor()
                        cur.execute("""
                            SELECT id FROM referrals 
                            WHERE referrer_id = ? 
                            AND created_at > datetime('now', '-1 day')
                        """, (chat_id,))
                        has_referral = cur.fetchone()
                        conn.close()
                        
                        if has_referral:
                            # انجام کوئست
                            success, message = complete_quest(chat_id, quest_id, user)
                            send_message(chat_id, message, quest_keyboard(lang) if success else main_menu(chat_id, lang))
                            if success:
                                update_user_score(chat_id, "quest_complete", user)
                        else:
                            send_message(
                                chat_id,
                                "🤝 امروز هیچ دعوتی نداشته‌اید!\n\nبرای انجام این کوئست، لطفاً از دکمه «دعوت از دوستان» استفاده کنید و لینک خود را به اشتراک بگذارید.",
                                quest_keyboard(lang)
                            )
                    except Exception as e:
                        logger.error(f"خطا در بررسی دعوت: {e}")
                        send_message(chat_id, "⚠️ خطا در بررسی دعوت. لطفاً دوباره تلاش کنید.", quest_keyboard(lang))
                elif quest_id in ["quran_search", "daily_visit", "feedback", "hadith", "instant_quran"]:
                    # انجام کوئست
                    success, message = complete_quest(chat_id, quest_id, user)
                    send_message(chat_id, message, quest_keyboard(lang) if success else main_menu(chat_id, lang))
                    if success:
                        update_user_score(chat_id, "quest_complete", user)
                elif quest_id == "show_quest_points":
                    # نمایش وضعیت کوئست‌ها
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
                    send_message(chat_id, "🔧 این کوئست در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                return "OK", 200

            # ===========================
            # بهترین کاربران
            # ===========================
            if cb_data == "show_best_daily":
                best = get_best_user("daily")
                if best:
                    msg = f"""🏅 <b>بهترین کاربر روز</b>

🌟 نام: {best['user_name']}
🏆 امتیاز: {best['score']}
📅 تاریخ: {best['date']}

💚 تبریک به این عزیز! 🌸
🕌 با تلاش خود الگوی دیگران باش."""
                else:
                    msg = "🏅 هنوز بهترین کاربر روز مشخص نشده است.\n\n🌟 اولین نفر باش و با فعالیت‌هایت در لیگ قرآنی بدرخش!"
                
                send_message(chat_id, msg, best_users_keyboard(lang))
                return "OK", 200

            if cb_data == "show_best_weekly":
                best = get_best_user("weekly")
                if best:
                    msg = f"""🏆 <b>بهترین کاربر هفته</b>

🌟 نام: {best['user_name']}
🏆 امتیاز: {best['score']}
📅 هفته: {best['date']}

💚 تبریک ویژه به این عزیز! 🌸
🕌 با تلاش خود الگوی دیگران باش."""
                else:
                    msg = "🏆 هنوز بهترین کاربر هفته مشخص نشده است.\n\n🌟 با تلاش مستمر، می‌توانی بهترین هفته باشی!"
                
                send_message(chat_id, msg, best_users_keyboard(lang))
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
                
                stats = get_system_stats()
                admin_text = f"""🛠️ <b>پنل ادمین</b>

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

👥 <b>کاربران:</b>
• کل کاربران: {stats['total_users']}
• فعال (۷ روز): {stats['active_users_7d']}
• فعال (۳۰ روز): {stats['active_users_30d']}

📝 <b>بازخوردها:</b>
• کل بازخوردها: {stats['total_feedbacks']}
• در انتظار بررسی: {stats['pending_feedbacks']}

🏆 <b>امتیازات:</b>
• بالاترین امتیاز: {stats['highest_score']}
• میانگین امتیاز: {stats['total_users'] and stats['highest_score'] // max(stats['total_users'], 1) or 0}

📚 <b>کتابخانه:</b>
• آیات قرآن: {stats['quran_count']}
• فرازهای نهج‌البلاغه: {stats['nahj_count']}
• دعاهای صحیفه سجادیه: {stats['sahifeh_count']}
• موضوعات: {len(TOPICS_DATA)}

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
                cur.execute("""
                    SELECT id, user_name, content, score, created_at, category 
                    FROM feedbacks 
                    WHERE status='pending' 
                    ORDER BY score DESC, id DESC 
                    LIMIT 10
                """)
                feedbacks = cur.fetchall()
                conn.close()
                
                if feedbacks:
                    msg = "📩 <b>لیست انتقادات و پیشنهادات (بر اساس امتیاز):</b>\n\n"
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
                times = "🕐 ۸:۰۰ صبح\n🕐 ۱۲:۰۰ ظهر\n🕐 ۱۸:۰۰ عصر"
                
                send_message(chat_id, f"""⏰ <b>تنظیمات زمان‌بندی</b>

وضعیت: {schedule_status}
زمان‌های ارسال:
{times}

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
                cur.execute("""
                    SELECT error_type, error_message, created_at 
                    FROM error_logs 
                    ORDER BY id DESC 
                    LIMIT 10
                """)
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
                
                # بهترین کاربر روز
                best_daily = get_best_user("daily")
                if best_daily:
                    msg += f"🏅 بهترین کاربر روز:\n{best_daily['user_name']} — {best_daily['score']} امتیاز\n\n"
                else:
                    msg += "🏅 بهترین کاربر روز: هنوز مشخص نشده\n\n"
                
                # بهترین کاربر هفته
                best_weekly = get_best_user("weekly")
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
                    cur.execute("""
                        SELECT COUNT(*) FROM referrals
                    """)
                    total_ref = cur.fetchone()[0]
                    
                    cur.execute("""
                        SELECT user_name, referral_count, referral_earned 
                        FROM users 
                        WHERE referral_count > 0 
                        ORDER BY referral_count DESC 
                        LIMIT 10
                    """)
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
            # اشتراک‌گذاری
            # ===========================
            if cb_data == "menu_share":
                bot_username = BOT_USERNAME
                share_text = f"""🌟 <b>ربات کانون قرآن و عترت</b>

✨ همراه همیشگی تو در مسیر نور و معرفت

📖 جستجوی هوشمند قرآن با ترجمه و تفسیر
🧠 موتور دانش اسلامی (Islamic Knowledge Engine)
🤖 هوش مصنوعی پاسخ‌گو
🕊️ حدیث و ذکر روزانه با تفسیر
🏆 لیگ قرآنی
🎯 کوئست‌های روزانه
🤝 سیستم دعوت و پاداش

💚 با ما همراه شو:
https://ble.ir/{bot_username}"""
                
                send_message(chat_id, share_text, share_keyboard(lang))
                return "OK", 200

            # ===========================
            # کپی لینک
            # ===========================
            if cb_data == "copy_link":
                bot_username = BOT_USERNAME
                send_message(
                    chat_id,
                    f"📋 <b>لینک ربات:</b>\n\nhttps://ble.ir/{bot_username}\n\n💚 این لینک رو با دوستانت به اشتراک بذار!",
                    share_keyboard(lang)
                )
                return "OK", 200

            # ===========================
            # یادآوری
            # ===========================
            if cb_data == "menu_reminder":
                send_message(
                    chat_id,
                    "⏰ <b>سیستم یادآوری</b>\n\n📝 متن یادآوری خود را بنویسید.\n\n💡 مثال: «تلاوت قرآن ساعت ۸ صبح»",
                    reminder_keyboard(lang)
                )
                update_user(chat_id, state="waiting_reminder")
                return "OK", 200

            if cb_data == "reminder_daily":
                send_message(
                    chat_id,
                    "🕐 <b>یادآوری روزانه</b>\n\n📝 لطفاً متن یادآوری خود را بنویسید.\n\n⏰ این یادآوری هر روز در همین ساعت به شما نمایش داده می‌شود.",
                    back_menu_keyboard(lang)
                )
                update_user(chat_id, state="waiting_reminder")
                return "OK", 200

            if cb_data == "reminder_weekly":
                send_message(
                    chat_id,
                    "📅 <b>یادآوری هفتگی</b>\n\n📝 لطفاً متن یادآوری خود را بنویسید.\n\n⏰ این یادآوری هر هفته در همین روز و ساعت به شما نمایش داده می‌شود.",
                    back_menu_keyboard(lang)
                )
                update_user(chat_id, state="waiting_reminder")
                return "OK", 200

            if cb_data == "reminder_list":
                try:
                    conn = db_conn()
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT reminder_text, remind_at 
                        FROM reminders 
                        WHERE user_id = ? AND is_done = 0
                        ORDER BY remind_at 
                        LIMIT 5
                    """, (chat_id,))
                    reminders = cur.fetchall()
                    conn.close()
                    
                    if reminders:
                        msg = "📋 <b>یادآوری‌های شما:</b>\n\n"
                        for r in reminders:
                            msg += f"📝 {r[0]}\n⏰ {r[1]}\n\n"
                        send_message(chat_id, msg, reminder_keyboard(lang))
                    else:
                        send_message(chat_id, "📋 هیچ یادآوری فعالی ندارید.\n\n💡 با دکمه «تنظیم یادآوری» یکی ثبت کن.", reminder_keyboard(lang))
                except Exception as e:
                    logger.error(f"خطا در دریافت یادآوری‌ها: {e}")
                    send_message(chat_id, "⚠️ خطا در دریافت یادآوری‌ها.", reminder_keyboard(lang))
                return "OK", 200

            # ===========================
            # راهنما
            # ===========================
            if cb_data == "menu_help":
                if lang == "fa":
                    help_text = """❓ <b>راهنمای استفاده از ربات</b>

📖 <b>جستجوی هوشمند قرآن:</b>
• عبارت مورد نظر را وارد کنید
• نتایج شامل متن، ترجمه و تفسیر نمایش داده می‌شود
• با کلمات کلیدی مانند «صبر»، «امید»، «استرس» جستجوی معنایی انجام می‌شود

🧠 <b>موتور دانش اسلامی:</b>
• جستجو در قرآن، نهج‌البلاغه، صحیفه سجادیه، احادیث و مقالات
• تشخیص خودکار موضوع و مترادف‌ها
• نمایش نتایج دسته‌بندی شده

🤖 <b>هوش مصنوعی:</b>
• هر سوال قرآنی یا دینی دارید بپرسید
• پاسخ‌های دقیق و مفید دریافت کنید

📚 <b>مقالات علمی:</b>
• جستجوی مقالات از گوگل اسکالر
• اولویت با مقالات قرآن، عترت و پزشکی

🕊️ <b>حدیث و ذکر:</b>
• دریافت حدیث روزانه با تفسیر
• ذکر مخصوص هر روز

✨ <b>قرآن در لحظه:</b>
• دریافت آیه‌های کوتاه و پرمعنا
• مناسب برای لحظات کوتاه

🏆 <b>لیگ قرآنی:</b>
• رقابت با سایر کاربران
• کسب امتیاز از طریق فعالیت‌ها

🎯 <b>کوئست‌های روزانه:</b>
• انجام کوئست‌های مختلف
• کسب امتیاز اضافی

🤝 <b>سیستم دعوت:</b>
• دعوت از دوستان با لینک اختصاصی
• ۱۰ امتیاز هدیه برای شما و دوستتان

🏅 <b>بهترین کاربران:</b>
• بهترین کاربر روز (هر شب ساعت ۲۳:۵۹)
• بهترین کاربر هفته (هر جمعه)

📝 <b>پیشنهاد/انتقاد:</b>
• ارسال پیشنهادات سازنده
• کسب امتیاز برای پیشنهادات خوب

🌍 <b>زبان‌های پشتیبانی:</b>
• فارسی 🇮🇷 (با تاریخ شمسی)
• English 🇬🇧
• العربية 🇸🇦

💚 همراه همیشگی تو در مسیر نور"""
                else:
                    help_text = safe_text(lang, "help_text", default="📚 Help Guide\n\nUse /start to begin.")
                
                send_message(chat_id, help_text, main_menu(chat_id, lang))
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
                    if lang == "fa":
                        msg = f"""📖 <b>جستجوی هوشمند در منابع اسلامی</b>

🔍 کلمه یا موضوع مورد نظر خود را وارد کنید:

💡 <b>نکته:</b> اگر موضوعی مانند «صبر»، «امید»، «استرس» وارد کنید، موتور دانش اسلامی تمام منابع را جستجو می‌کند.

📚 <b>منابع جستجو:</b>
• قرآن کریم با تفسیر 📖
• نهج‌البلاغه 📜
• صحیفه سجادیه 🤲
• احادیث 🕊️
• مقالات علمی 📚

📝 لطفاً عبارت خود را ارسال کنید:"""
                    else:
                        msg = safe_text(lang, "search_quran_prompt")
                    send_message(chat_id, msg, back_menu_keyboard(lang))
                
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
                    interpretation = item.get('interpretation', '')
                    if not interpretation or len(interpretation) < 10:
                        interpretation = get_daily_interpretation(item['hadith'], lang)
                    
                    topics = ', '.join(item.get('topics', ['عمومی']))
                    
                    msg = f"""🕊️ <b>حدیث روز</b>

{item['hadith']}

🔹 <b>ذکر روزانه:</b>
{item['dhikr']}

💡 <b>تفسیر:</b> {interpretation}

🏷️ دسته: {item['category']}
🏷️ موضوعات: {topics}

💚 با یاد خدا دل‌ها آرام می‌گیرد."""
                    send_message(chat_id, msg, main_menu(chat_id, lang))
                    update_user(chat_id, score=1)
                    update_user_score(chat_id, "hadith_read", user)
                
                elif action == "instant_quran":
                    if not FEATURES["instant_quran"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    
                    item = random.choice(INSTANT_QURAN_FULL)
                    interpretation = get_daily_interpretation(item['arabic'], lang)
                    
                    msg = f"""📖 <b>قرآن در لحظه</b>

<b>{item['surah']} (آیه {item['verse']})</b>

{item['arabic']}

✨ {item['trans']}

💡 <b>تفسیر:</b> {interpretation}

💚 هر لحظه با قرآن، هر لحظه با نور."""
                    send_message(chat_id, msg, main_menu(chat_id, lang))
                    update_user(chat_id, score=1)
                    update_user_score(chat_id, "instant_quran", user)
                
                elif action == "events":
                    send_message(chat_id, safe_text(lang, "events_text"), main_menu(chat_id, lang))
                
                elif action == "feedback":
                    if not FEATURES["feedback_system"]:
                        send_message(chat_id, "🔧 این ویژگی در حال حاضر غیرفعال است.", main_menu(chat_id, lang))
                        return "OK", 200
                    update_user(chat_id, state="waiting_feedback")
                    if lang == "fa":
                        msg = "📝 <b>پیشنهاد یا انتقاد خود را بنویسید</b>\n\n💡 نکات برای دریافت امتیاز بیشتر:\n• پیشنهاد خود را دقیق و تأثیرگذار بنویسید\n• از کلمات کلیدی مناسب استفاده کنید\n• پیشنهاد سازنده و عملی ارائه دهید\n\n⭐ حداکثر امتیاز: ۵ (کمتر از جستجوی قرآن)"
                    else:
                        msg = safe_text(lang, "feedback_prompt", default="📝 Write your suggestion or critique:")
                    send_message(chat_id, msg, back_menu_keyboard(lang))
                
                elif action == "admin_msg":
                    update_user(chat_id, state="waiting_admin_msg")
                    send_message(chat_id, safe_text(lang, "admin_msg_prompt"), back_menu_keyboard(lang))
                
                elif action == "stats":
                    latest_user = get_user(chat_id)
                    title = get_user_title(latest_user.get("score", 0))
                    send_message(
                        chat_id,
                        safe_text(lang, "stats", 
                            name=first_name,
                            score=latest_user["score"],
                            search_count=latest_user["search_count"],
                            streak=latest_user["streak"],
                            feedback_score=latest_user["feedback_score"],
                            join_date=latest_user["join_date"],
                            title=title,
                            visits=latest_user["total_visits"],
                            quests=latest_user["total_quests_completed"],
                            referrals=latest_user["referral_count"],
                            referral_earned=latest_user["referral_earned"]
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
                        for i, user_data in enumerate(top_users, 1):
                            if len(user_data) >= 5:
                                name, score, visits, streak, referrals = user_data[0], user_data[1], user_data[2], user_data[3], user_data[4]
                            elif len(user_data) >= 4:
                                name, score, visits, streak = user_data[0], user_data[1], user_data[2], user_data[3]
                                referrals = 0
                            elif len(user_data) >= 3:
                                name, score, visits = user_data[0], user_data[1], user_data[2]
                                streak, referrals = 0, 0
                            else:
                                name, score = user_data[0], user_data[1]
                                visits, streak, referrals = 0, 0, 0
                            
                            if i <= 3:
                                leaderboard += f"{medals[i-1]} {name} — {score} امتیاز (🔥 {streak} روز، 🤝 {referrals} دعوت)\n"
                            else:
                                leaderboard += f"{i}. {name} — {score} امتیاز (🔥 {streak} روز، 🤝 {referrals} دعوت)\n"
                    else:
                        leaderboard = "🌟 <b>لیگ قرآنی هنوز شروع نشده!</b>\n\n💡 اولین نفر باش و با استفاده از ربات امتیاز جمع کن:\n• جستجوی قرآن 📖\n• ارسال پیشنهاد 📝\n• بازدید روزانه 🌅\n• مطالعه حدیث 🕊️\n• دعوت از دوستان 🤝"
                    
                    send_message(
                        chat_id,
                        safe_text(lang, "league_text", leaderboard=leaderboard),
                        main_menu(chat_id, lang)
                    )
                
                elif action == "scorecard":
                    rank = get_user_rank(chat_id)
                    latest_user = get_user(chat_id)
                    title = get_user_title(latest_user.get("score", 0))
                    send_message(
                        chat_id,
                        safe_text(lang, "scorecard_text",
                            name=first_name,
                            score=latest_user["score"],
                            rank=rank,
                            search_count=latest_user["search_count"],
                            streak=latest_user["streak"],
                            feedback_score=latest_user["feedback_score"],
                            title=title,
                            quests=latest_user["total_quests_completed"],
                            referrals=latest_user["referral_count"],
                            referral_earned=latest_user["referral_earned"]
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
                
                elif action == "quests":
                    if lang == "fa":
                        msg = "🎯 <b>کوئست‌های روزانه</b>\n\nبا انجام هر کوئست، امتیاز بگیر و در لیگ قرآنی بدرخش! 🌟"
                    else:
                        msg = safe_text(lang, "quests_info", default="🎯 Daily Quests")
                    send_message(chat_id, msg, quest_keyboard(lang))
                
                elif action == "best_users":
                    if lang == "fa":
                        msg = "🏅 <b>بهترین کاربران</b>\n\nهر شب ساعت ۲۳:۵۹ بهترین کاربر روز\nهر جمعه ساعت ۲۳:۵۹ بهترین کاربر هفته\n\nبرای مشاهده انتخاب کن:"
                    else:
                        msg = safe_text(lang, "best_users_info", default="🏅 Best Users")
                    send_message(chat_id, msg, best_users_keyboard(lang))
                
                elif action == "referral":
                    referral_code = user.get("referral_code", "")
                    if not referral_code:
                        referral_code = generate_referral_code()
                        update_user(chat_id, referral_code=referral_code)
                    
                    msg = f"""🤝 <b>سیستم دعوت از دوستان</b>

🌟 کد دعوت شما: <code>{referral_code}</code>

🎁 با دعوت از دوستان:
• به شما و دوستتان ۱۰ امتیاز هدیه داده می‌شود
• با هر دعوت، یک کوئست جدید فعال می‌شود
• پس از ۵ دعوت، عنوان «🥉 دعوت‌کننده برنزی» دریافت می‌کنید

📊 تعداد دعوت‌های شما: {user.get('referral_count', 0)}
💰 امتیاز کسب شده از دعوت‌ها: {user.get('referral_earned', 0)}

📤 لینک دعوت خود را با دوستان به اشتراک بگذارید:"""
                    
                    send_message(chat_id, msg, referral_keyboard(lang, referral_code))
                
                elif action == "islamic_engine":
                    if lang == "fa":
                        msg = """🧠 <b>موتور دانش اسلامی (Islamic Knowledge Engine)</b>

این موتور هوشمند، جستجوی شما را در تمام منابع اسلامی انجام می‌دهد:

📖 <b>قرآن کریم</b> - آیات مرتبط با تفسیر
📜 <b>نهج‌البلاغه</b> - خطبه‌ها، نامه‌ها و حکمت‌ها
🤲 <b>صحیفه سجادیه</b> - دعاهای نورانی
🕊️ <b>احادیث</b> - روایات معصومین
📚 <b>مقالات علمی</b> - از گوگل اسکالر

🔍 <b>چگونه کار می‌کند؟</b>
• هر کلمه یا موضوعی را وارد کنید
• ربات مترادف‌ها و کلمات کلیدی را تشخیص می‌دهد
• در همه منابع جستجو می‌کند
• نتایج را به صورت دسته‌بندی شده نمایش می‌دهد

💡 <b>مثال‌ها:</b>
• «صبر» → آیات صبر، روایات صبر، مقالات مرتبط
• «استرس» → آیات آرامش، دعاهای مرتبط، مقالات روانشناسی
• «امید» → آیات امید، حکمت‌های امید، مقالات امیدواری

📝 <b>کافی است موضوع مورد نظر خود را در بخش «جستجوی قرآن» وارد کنید.</b>

🌟 این موتور، ربات را از یک جستجوگر به یک دستیار پژوهشی اسلامی تبدیل می‌کند."""
                    else:
                        msg = safe_text(lang, "islamic_engine_info", default="🧠 Islamic Knowledge Engine")
                    
                    send_message(chat_id, msg, main_menu(chat_id, lang))
                
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
# ۲۵. کیبوردهای اینلاین (توسعه‌یافته)
# =========================================================
def lang_keyboard():
    """کیبورد انتخاب زبان با پشتیبانی از عربی"""
    return {
        "inline_keyboard": [
            [{"text": "🇮🇷 فارسی", "callback_data": "setlang_fa"}],
            [{"text": "🇬🇧 English", "callback_data": "setlang_en"}],
            [{"text": "🇸🇦 العربية", "callback_data": "setlang_ar"}]
        ]
    }

def join_keyboard():
    """کیبورد عضویت در کانال"""
    channel_username = CHANNEL_ID.replace("@", "")
    return {
        "inline_keyboard": [
            [{"text": "📢 ورود به کانال", "url": f"https://ble.ir/{channel_username}"}],
            [{"text": "✅ تایید عضویت", "callback_data": "check_join"}]
        ]
    }

def back_menu_keyboard(lang):
    """کیبورد بازگشت به منو"""
    text = safe_text(lang, "back_to_menu")
    return {"inline_keyboard": [[{"text": text, "callback_data": "back_main"}]]}

def quest_keyboard(lang):
    """کیبورد کوئست‌های روزانه"""
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
    """کیبورد بهترین کاربران"""
    return {
        "inline_keyboard": [
            [{"text": "🏅 بهترین کاربر روز", "callback_data": "show_best_daily"}],
            [{"text": "🏆 بهترین کاربر هفته", "callback_data": "show_best_weekly"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def referral_keyboard(lang, referral_code):
    """کیبورد دعوت از دوستان برای بله"""
    bot_username = BOT_USERNAME
    # لینک دعوت برای بله
    referral_link = f"https://ble.ir/{bot_username}?start=ref_{referral_code}"
    
    return {
        "inline_keyboard": [
            [{"text": "📤 اشتراک‌گذاری لینک دعوت", "url": f"https://ble.ir/share?url={referral_link}&text=🌸 به ربات کانون قرآن و عترت بپیوند! \nبا این لینک عضو شو و ۱۰ امتیاز هدیه بگیر! 🎁"}],
            [{"text": "📋 کپی لینک", "callback_data": "copy_referral"}],
            [{"text": "📊 آمار دعوت‌ها", "callback_data": "referral_stats"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def main_menu(chat_id, lang):
    """منوی اصلی با ۱۸ دکمه"""
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
        [{"text": labels["help"], "callback_data": "menu_help"},
         {"text": labels["reminder"], "callback_data": "menu_reminder"}],
        [{"text": labels["share"], "callback_data": "menu_share"},
         {"text": labels["quests"], "callback_data": "menu_quests"}],
        [{"text": labels["best_users"], "callback_data": "menu_best_users"},
         {"text": labels["referral"], "callback_data": "menu_referral"}],
        [{"text": labels["islamic_engine"], "callback_data": "menu_islamic_engine"}]
    ]
    
    # اضافه کردن پنل ادمین برای ادمین
    if chat_id == ADMIN_ID and FEATURES["admin_panel"]:
        buttons.append([{"text": safe_text(lang, "admin_panel"), "callback_data": "admin_panel"}])
    
    return {"inline_keyboard": buttons}

def admin_menu(chat_id, lang="fa"):
    """پنل ادمین با ۱۱ گزینه"""
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
            [{"text": safe_text(lang, "admin_back"), "callback_data": "back_main"}]
        ]
    }

def share_keyboard(lang):
    """کیبورد اشتراک‌گذاری"""
    return {
        "inline_keyboard": [
            [{"text": "📤 اشتراک‌گذاری ربات", "switch_inline_query": "ربات قرآن و عترت"}],
            [{"text": "📋 کپی لینک", "callback_data": "copy_link"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

def reminder_keyboard(lang):
    """کیبورد تنظیم یادآوری"""
    return {
        "inline_keyboard": [
            [{"text": "🕐 تنظیم یادآوری روزانه", "callback_data": "reminder_daily"}],
            [{"text": "🔔 تنظیم یادآوری هفتگی", "callback_data": "reminder_weekly"}],
            [{"text": "📋 مشاهده یادآوری‌ها", "callback_data": "reminder_list"}],
            [{"text": safe_text(lang, "back_to_menu"), "callback_data": "back_main"}]
        ]
    }

# =========================================================
# ۲۶. عضویت اجباری کانال بله (با کش)
# =========================================================
MEMBERSHIP_CACHE = {}
CACHE_DURATION = 300  # 5 دقیقه

def check_membership(chat_id):
    """بررسی عضویت کاربر با استفاده از کش"""
    if not CHANNEL_ID or not FEATURES["force_join"]:
        return True
    
    # چک کردن کش
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
            
            # ذخیره در کش
            MEMBERSHIP_CACHE[cache_key] = (is_member, time.time())
            return is_member
        
        MEMBERSHIP_CACHE[cache_key] = (False, time.time())
        return False
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت {chat_id}: {e}")
        # در صورت خطا، اجازه دسترسی بده (احتیاط)
        return True

# =========================================================
# ۲۷. اتصال هوش مصنوعی DeepSeek (با پشتیبانی از خطا و رفع باگ)
# =========================================================
def ask_deepseek(question, lang):
    """ارسال سوال به DeepSeek با مدیریت کامل خطا"""
    if not FEATURES["deepseek_ai"]:
        return "🔧 این ویژگی در حال حاضر غیرفعال است."
    
    if not DEEPSEEK_KEY or len(DEEPSEEK_KEY) < 10:
        logger.warning("کلید DeepSeek نامعتبر است")
        return "🔑 کلید API هوش مصنوعی تنظیم نشده است. لطفاً با ادمین تماس بگیرید."
    
    language_name = {"fa": "Persian", "en": "English", "ar": "Arabic"}.get(lang, "Persian")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": f"You are a warm, respectful, accurate assistant for a Quranic student bot at Shiraz University of Medical Sciences. Reply in {language_name}. Keep the answer useful, friendly, and well-formatted. If you don't know something, say so clearly. Provide interpretations that are relevant to medical professionals and students."},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        # ارسال وضعیت تایپ (با چک کردن chat_id معتبر)
        try:
            send_chat_action(chat_id, "typing")
        except:
            pass
        
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
                return answer
            else:
                logger.error(f"پاسخ غیرمنتظره از DeepSeek: {data}")
                return "⚠️ پاسخ دریافتی نامعتبر بود. لطفاً دوباره تلاش کنید."
        elif res.status_code == 401:
            logger.error("کلید DeepSeek نامعتبر است (401)")
            return "🔑 کلید API نامعتبر است. لطفاً با ادمین تماس بگیرید."
        elif res.status_code == 429:
            logger.error("محدودیت درخواست DeepSeek (429)")
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
# ۲۸. اجرای استارتاپ و سرور وب (توسعه‌یافته)
# =========================================================
def startup():
    """راه‌اندازی اولیه ربات با تمام قابلیت‌ها"""
    try:
        logger.info("🚀 شروع راه‌اندازی ربات...")
        
        # راه‌اندازی دیتابیس
        init_db()
        logger.info("✅ دیتابیس راه‌اندازی شد.")
        
        # بارگذاری کتابخانه
        load_library()
        logger.info("✅ کتابخانه بارگذاری شد.")
        
        # بررسی کلید DeepSeek
        if DEEPSEEK_KEY and len(DEEPSEEK_KEY) > 10:
            logger.info("✅ کلید DeepSeek تنظیم شده است.")
            FEATURES["deepseek_ai"] = True
        else:
            logger.warning("⚠️ کلید DeepSeek وجود ندارد یا نامعتبر است.")
            FEATURES["deepseek_ai"] = False
        
        # راه‌اندازی اسکجولر روزانه
        if FEATURES["daily_posts"]:
            scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("✅ اسکژولر روزانه (۳ زمان) راه‌اندازی شد.")
        else:
            logger.info("ℹ️ اسکژولر روزانه غیرفعال است.")
        
        # راه‌اندازی اسکجولر بهترین کاربران
        if FEATURES["best_user_daily"] or FEATURES["best_user_weekly"]:
            best_user_thread = threading.Thread(target=schedule_best_users, daemon=True)
            best_user_thread.start()
            logger.info("✅ اسکژولر بهترین کاربران راه‌اندازی شد.")
        
        # راه‌اندازی تمیزکاری کش
        def cache_cleaner():
            """پاکسازی خودکار کش هر ۶ ساعت"""
            while True:
                try:
                    time.sleep(21600)  # ۶ ساعت
                    MEMBERSHIP_CACHE.clear()
                    logger.info("🧹 کش عضویت پاکسازی شد.")
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
        logger.info(f"🔍 جستجوی معنایی: {'فعال' if FEATURES['semantic_search'] else 'غیرفعال'}")
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
