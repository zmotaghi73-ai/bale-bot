import os
from flask import Flask, request

app = Flask(__name__)

# مسیر اصلی برای تست در مرورگر
@app.route("/")
def home():
    return "Robot is Alive and Healthy!"

# مسیر اصلی که بله به آن پیام می‌فرستد
@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.get_json()
    print("پیام جدید دریافت شد:", data) # این در لاگ‌ها چاپ می‌شود
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
