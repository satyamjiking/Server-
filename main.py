# main.py
import os
import json
import time
import logging
import threading
import re
from typing import List, Dict
from flask import Flask
import requests
from bs4 import BeautifulSoup

# --------------------------
# Logging
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("BOT")

# --------------------------
# Config (env or defaults)
# --------------------------
COOKIE_FILE = os.environ.get("COOKIE_FILE", "cookie.json")
MESSAGES_FILE = os.environ.get("MESSAGES_FILE", "file.txt")
TARGETS_FILE = os.environ.get("TARGETS_FILE", "targets.txt")
DELAY = float(os.environ.get("DELAY", "8"))
PORT = int(os.environ.get("PORT", "10000"))  # Render may override PORT env

# --------------------------
# Load cookie.json
# cookie.json should be an array of cookie objects:
# [
#   {"name": "c_user", "value": "1000xxxxx", "domain": ".facebook.com"},
#   {"name": "xs", "value": "xxx", "domain": ".facebook.com"}
# ]
# --------------------------
def load_cookies_from_file(path: str) -> List[Dict]:
    if not os.path.exists(path):
        logger.error("Cookie load nahi ho payi: file missing -> %s", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.error("Cookie file format incorrect: expecting JSON array")
                return []
            logger.info("Cookie loaded from %s (%d items)", path, len(data))
            return data
    except Exception as e:
        logger.exception("Cookie load error: %s", e)
        return []

def build_session_from_cookies(cookies: List[Dict]) -> requests.Session:
    s = requests.Session()
    # set some headers default
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    })
    for c in cookies:
        name = c.get("name")
        val = c.get("value")
        domain = c.get("domain", None)
        if name and val:
            # requests.Session cookies.set accepts domain optional
            if domain:
                s.cookies.set(name, val, domain=domain)
            else:
                s.cookies.set(name, val)
    return s

# --------------------------
# Helpers to read files
# --------------------------
def read_lines_strip(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

# --------------------------
# Fetch fb tokens from conversation page (example using mbasic)
# NOTE: You must confirm the correct url & fields by inspecting network in browser
# --------------------------
def fetch_form_tokens(session: requests.Session, target_id: str) -> Dict[str, str]:
    """
    Try to open conversation compose page and extract fb_dtsg/jazoest or other hidden fields.
    This is a heuristic: you MUST verify correct inputs using browser devtools for your account.
    """
    # Example URL pattern for mobile/basic:
    url = f"https://mbasic.facebook.com/messages/thread/{target_id}"
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            logger.warning("Could not fetch thread page %s status=%s", url, r.status_code)
            return {}
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        tokens = {}
        # Common hidden inputs
        for name in ("fb_dtsg", "jazoest", "composer_session_id", "av"):
            el = soup.find("input", {"name": name})
            if el and el.get("value"):
                tokens[name] = el.get("value")

        # fallback: try regex for fb_dtsg in page
        if "fb_dtsg" not in tokens:
            m = re.search(r'name="fb_dtsg"\s+value="([^"]+)"', html)
            if m:
                tokens["fb_dtsg"] = m.group(1)

        logger.debug("Tokens found for %s: %s", target_id, list(tokens.keys()))
        return tokens
    except Exception as e:
        logger.exception("Token fetch failed for %s: %s", target_id, e)
        return {}

# --------------------------
# send_message - PLACEHOLDER
# You must change payload/url according to the exact request you capture from browser.
# --------------------------
def send_message(session: requests.Session, target_id: str, message: str) -> bool:
    """
    Attempt to send message using cookie-backed `session`.
    IMPORTANT: This is a template. Inspect network requests in browser when you manually send a message,
    then copy that request's URL and form fields here.
    """
    # Step1: fetch tokens
    tokens = fetch_form_tokens(session, target_id)
    if not tokens:
        logger.warning("Tokens missing for target %s — cannot send.", target_id)
        return False

    # TODO: Replace this URL with exact endpoint captured from browser devtools
    # Example (not guaranteed): mbasic message send endpoint:
    send_url = f"https://mbasic.facebook.com/messages/send/?ids[{target_id}]=1"

    # TODO: Replace payload keys with those the real request used (body, fb_dtsg, jazoest, ...)
    payload = {
        "body": message,
        # include tokens if present
        **({k: tokens[k] for k in ("fb_dtsg", "jazoest") if k in tokens})
    }

    headers = {
        "Referer": f"https://mbasic.facebook.com/messages/thread/{target_id}",
        "Origin": "https://mbasic.facebook.com",
    }

    try:
        r = session.post(send_url, data=payload, headers=headers, timeout=20)
        # success criteria: 200/302 or check response content for "message sent" indication
        if r.status_code in (200, 302):
            logger.info("Message posted to %s (status=%s)", target_id, r.status_code)
            return True
        else:
            logger.warning("Send failed status=%s for %s", r.status_code, target_id)
            return False
    except Exception as e:
        logger.exception("Exception sending to %s: %s", target_id, e)
        return False

# --------------------------
# Worker loop (background thread)
# --------------------------
def worker_loop():
    # load cookies and build session
    cookies = load_cookies_from_file(COOKIE_FILE)
    if not cookies:
        logger.error("Cookie nahi mili. Worker exit.")
        return
    session = build_session_from_cookies(cookies)

    # sanity check - visit homepage to ensure cookies working
    try:
        r = session.get("https://mbasic.facebook.com/", timeout=15)
        logger.info("Session GET mbasic status=%s", r.status_code)
    except Exception as e:
        logger.exception("Session test failed: %s", e)

    messages = read_lines_strip(MESSAGES_FILE)
    targets = read_lines_strip(TARGETS_FILE)

    if not messages:
        logger.error("No messages in %s", MESSAGES_FILE)
        return
    if not targets:
        logger.error("No targets in %s", TARGETS_FILE)
        return

    logger.info("Worker started: %d messages x %d targets", len(messages), len(targets))

    try:
        while True:
            for t in targets:
                for m in messages:
                    logger.info("Sending message to %s: %s", t, (m[:120] + '...') if len(m)>120 else m)
                    ok = send_message(session, t, m)
                    if ok:
                        logger.info("Message sent to %s", t)
                    else:
                        logger.warning("Failed to send to %s", t)
                    time.sleep(DELAY)
            # small pause after full cycle
            time.sleep(5)
    except Exception as e:
        logger.exception("Worker loop crashed: %s", e)

# --------------------------
# Flask app (Render expects a web process)
# --------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot running. Check logs."

if __name__ == "__main__":
    # start worker thread
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    # run flask
    app.run(host="0.0.0.0", port=PORT)
