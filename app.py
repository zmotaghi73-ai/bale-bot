import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)

# توکن ربات بله
BOT_TOKEN = "1649912283:atESusXoVB3YgzqKiQ7sJg9Jn9oqLLl5TxY"

# آدرس API بله
BASE_API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"


def call_api(method, params):
    url = f"{BASE_API_URL}/{method}"

    data = json.dumps(params).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def send_message(chat_id, text):
    call_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


@app.route("/")
def home():
    return "Bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    print(update)

    if "message" in update:

        message = update["message"]

        chat_id = message["chat"]["id"]

        if "text" in message:

            text = message["text"]

            # دستور استارت
            if text == "/start":

                send_message(
                    chat_id,
                    "سلام 🌱\nربات بله با موفقیت فعال شد 😎"
                )

            else:

                send_message(
                    chat_id,
                    f"پیام شما:\n{text}"
                )

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

