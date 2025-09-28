import json
import time
import os
import logging
import threading
from flask import Flask

# ------------------------------
# Logging setup
# ------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BOT")

# ------------------------------
# Load cookie
# ------------------------------
COOKIE_FILE = "cookie.json"
if not os.path.exists(COOKIE_FILE):
    logger.error("❌ Cookie file not found! => cookie.json missing")
    exit(1)

with open(COOKIE_FILE, "r", encoding="utf-8") as f:
    try:
        cookies = json.load(f)

        # Agar file ek list hai (Kiwi/Chrome export jaisa)
        cookie_dict = {}
        if isinstance(cookies, list):
            for c in cookies:
                if "name" in c and "value" in c:
                    cookie_dict[c["name"]] = c["value"]
        else:
            cookie_dict = cookies

        logger.info(f"✅ Cookies loaded successfully: {list(cookie_dict.keys())}")

    except Exception as e:
        logger.error(f"❌ Error loading cookie.json: {e}")
        exit(1)

# ------------------------------
# Dummy message sending function
# ------------------------------
def send_message(target_id, message):
    logger.info(f"📩 Sending message to {target_id}: {message}")
    # yaha real request/session code lagana hai
    time.sleep(2)
    logger.info(f"✅ Message sent to {target_id}")

# ------------------------------
# Worker thread
# ------------------------------
def worker():
    targets = ["123456789", "987654321"]  # apni target IDs dalna
    with open("file.txt", "r", encoding="utf-8") as f:
        messages = f.readlines()

    while True:
        for msg in messages:
            for tid in targets:
                send_message(tid, msg.strip())
        time.sleep(40)  # repeat after 40 sec

# ------------------------------
# Flask server (Render requirement)
# ------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 Server is running with cookie.json ✅"

if __name__ == "__main__":
    # Background worker thread
    t = threading.Thread(target=worker, daemon=True)
    t.start()

    # Flask run (Render will check this)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
