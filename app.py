# فقط بخش webhook را با این جایگزین کن:

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
        # دریافت اطلاعات کاربر و چک کردن امنیت زبان
        user_data = get_user(chat_id)
        lang, score, state = user_data if user_data else ('fa', 0, 'none')
        
        # اگر زبان تعریف نشده بود، اجباراً فارسی کن
        if lang not in LANGS:
            lang = 'fa'

        # بررسی عضویت اجباری
        if not check_membership(chat_id) and text != "/start":
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": LANGS[lang].get('force_join', "لطفا عضو کانال شوید").format(channel=CHANNEL_ID),
                "reply_markup": join_keyboard(lang)
            })
            return "OK", 200

        if text == "/start":
            update_user(chat_id, name=first_name, state='none')
            # استفاده از .get برای جلوگیری از KeyError
            welcome_text = LANGS[lang].get('select_lang', "لطفا زبان را انتخاب کنید")
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": welcome_text,
                "reply_markup": lang_keyboard()
            })
            return "OK", 200

        # ... (بقیه کدهای هوش مصنوعی و ادمین مثل قبل)
        if state == "waiting_ai":
            send_bale("sendMessage", {"chat_id": chat_id, "text": LANGS[lang].get('ai_wait', "در حال پردازش...")})
            ai_res = ask_deepseek(text, lang)
            send_bale("sendMessage", {
                "chat_id": chat_id,
                "text": f"🤖 **پاسخ هوشمند:**\n\n{ai_res}",
                "reply_markup": main_menu(chat_id, lang)
            })
            update_user(chat_id, state='none')
            return "OK", 200
