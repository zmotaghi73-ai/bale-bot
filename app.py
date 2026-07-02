import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# توکن رو حتماً چک کن که درست باشه
BOT_TOKEN = os.environ.get("BOT_TOKEN", "توکن_خودت_را_اینجا_بگذار")
BALE_API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

def send_message(chat_id, text):
    url = BALE_API_URL + "sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Response from Bale: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

@app.route('/', methods=['GET'])
def index():
    return "Bot is Running! 🚀", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    print(f"Received update: {update}") # برای دیدن پیام‌های دریافتی در لاگ
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "سلام زندگی جان! من دوباره زنده شدم 🩺💪\nچطور می‌تونم کمکت کنم؟")
        elif "آیه روز" in text:
            send_message(chat_id, "🌙 در حال استخراج آیه روز برای شما...")
        elif "راهنمای ربات" in text:
            send_message(chat_id, "🕌 راهنمای ربات: به زودی دکمه‌های منو فعال می‌شوند.")
        else:
            send_message(chat_id, f"پیام شما دریافت شد: {text}")
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
