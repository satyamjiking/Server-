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
# --- COOKIE-BASED AUTOMATION के लिए ज़रूरी ---
COOKIE_FILE = os.environ.get("COOKIE_FILE", "cookie.json") 
MESSAGES_FILE = os.environ.get("MESSAGES_FILE", "file.txt")
TARGETS_FILE = os.environ.get("TARGETS_FILE", "targets.txt")
DELAY = float(os.environ.get("DELAY", "40")) # 40 सेकंड का डिफ़ॉल्ट विलंब
PORT = int(os.environ.get("PORT", "10000")) 

# --------------------------
# Load cookie.json
# --------------------------
def load_cookies_from_file(path: str) -> List[Dict]:
    """cookie.json फ़ाइल से कुकीज़ लोड करता है।"""
    if not os.path.exists(path):
        logger.error("Cookie file missing: %s. Automation will fail.", path)
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
    """कुकीज़ से requests.Session बनाता है।"""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    })
    for c in cookies:
        name = c.get("name")
        val = c.get("value")
        domain = c.get("domain", None)
        if name and val:
            if domain:
                s.cookies.set(name, val, domain=domain)
            else:
                s.cookies.set(name, val)
    return s

# --------------------------
# Helpers to read files
# --------------------------
def read_lines_strip(path: str) -> List[str]:
    """टेक्स्ट फ़ाइल से मैसेज/टारगेट पढ़ता है।"""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

# --------------------------
# Fetch form tokens (fb_dtsg, jazoest, etc.)
# --------------------------
def fetch_form_tokens(session: requests.Session, target_id: str) -> Dict[str, str]:
    """mbasic conversation page से सभी आवश्यक छिपे हुए फ़ील्ड्स को एक्सट्रेक्ट करता है।"""
    url = f"https://mbasic.facebook.com/messages/thread/{target_id}"
    tokens = {}
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            logger.warning("Could not fetch thread page %s status=%s", url, r.status_code)
            return {}
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # सभी hidden inputs को कैप्चर करें
        for el in soup.find_all("input", {"type": "hidden"}):
            name = el.get("name")
            value = el.get("value")
            if name and value:
                tokens[name] = value

        # fallback: fb_dtsg के लिए regex
        if "fb_dtsg" not in tokens:
            m = re.search(r'name="fb_dtsg"\s+value="([^"]+)"', r.text)
            if m:
                tokens["fb_dtsg"] = m.group(1)

        logger.debug("Tokens found for %s: %s", target_id, list(tokens.keys()))
        
        # यदि 'body' फ़ील्ड मौजूद है, तो उसे हटाएं क्योंकि हम इसे मैसेज बॉडी से ओवरराइट करेंगे
        if 'body' in tokens:
            del tokens['body'] 
            
        return tokens
    except Exception as e:
        logger.exception("Token fetch failed for %s: %s", target_id, e)
        return {}

# --------------------------
# send_message (Cookie-Based)
# --------------------------
def send_message(session: requests.Session, target_id: str, message: str) -> bool:
    """Cookie-backed session का उपयोग करके मैसेज भेजने का प्रयास करता है।"""
    tokens = fetch_form_tokens(session, target_id)
    if not tokens:
        logger.warning("Tokens missing for target %s — cannot send.", target_id)
        return False

    # mbasic message send endpoint
    send_url = f"https://mbasic.facebook.com/messages/send/?ids[{target_id}]=1"

    # सभी कैप्चर किए गए टोकन और मैसेज बॉडी को पेलोड में शामिल करें
    payload = {
        "body": message,
        **tokens 
    }
    
    # mbasic post request में 'Send' बटन का नाम अक्सर 'Send' या 'send' होता है
    # सुनिश्चित करें कि आपके कैप्चर किए गए फॉर्म में यह फ़ील्ड मौजूद हो, 
    # या इसे hardcode करें यदि 'tokens' में नहीं मिला
    if 'send' not in payload and 'Send' not in payload:
        payload['send'] = 'Send' 

    headers = {
        "Referer": f"https://mbasic.facebook.com/messages/thread/{target_id}",
        "Origin": "https://mbasic.facebook.com",
        "Content-Type": "application/x-www-form-urlencoded" # Mbasic form submission
    }

    try:
        # POST request भेजें
        r = session.post(send_url, data=payload, headers=headers, allow_redirects=False, timeout=20)
        
        # Success criteria: 302 Redirection (मैसेज भेजने के बाद पेज रीडायरेक्ट होता है)
        if r.status_code == 302:
            logger.info("Message posted to %s (Status: 302 Redirect)", target_id)
            return True
        else:
             # यदि 200 आता है, तो HTML में त्रुटि की जाँच करें
            if "Something Went Wrong" in r.text or "Error" in r.text:
                logger.warning("Send failed status=%s. Server returned error page for %s", r.status_code, target_id)
                return False
            logger.warning("Send failed status=%s for %s. Unexpected response.", r.status_code, target_id)
            return False
    except Exception as e:
        logger.exception("Exception sending to %s: %s", target_id, e)
        return False

# --------------------------
# Worker loop (background thread) - Continuous Loop
# --------------------------
def worker_loop():
    cookies = load_cookies_from_file(COOKIE_FILE)
    if not cookies:
        logger.error("Cookie nahi mili. Worker exit.")
        return
    session = build_session_from_cookies(cookies)

    messages = read_lines_strip(MESSAGES_FILE)
    targets = read_lines_strip(TARGETS_FILE)

    if not messages:
        logger.error("No messages in %s", MESSAGES_FILE)
        return
    if not targets:
        logger.error("No targets in %s", TARGETS_FILE)
        return

    logger.info("Worker started: %d messages x %d targets. Delay: %s sec", len(messages), len(targets), DELAY)

    try:
        # अनंत लूप (Infinite Loop) - ताकि मैसेज खत्म होने के बाद भी चलता रहे
        while True:
            logger.info("Starting new cycle of messages...")
            for t in targets:
                for m in messages:
                    logger.info("Sending message to %s: %s", t, (m[:120] + '...') if len(m)>120 else m)
                    ok = send_message(session, t, m)
                    if ok:
                        logger.info("Message sent to %s", t)
                    else:
                        logger.warning("Failed to send to %s", t)
                    
                    # 40 सेकंड का विलंब
                    time.sleep(DELAY) 
            
            # एक चक्र पूरा होने के बाद थोड़ा विराम
            logger.info("Cycle complete. Restarting loop after 60 seconds...")
            time.sleep(60) 

    except Exception as e:
        logger.exception("Worker loop crashed: %s", e)

# --------------------------
# Flask app (Render expects a web process)
# --------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot running. Check logs for status. Mode: Cookie-Based (M-Basic)"

if __name__ == "__main__":
    # start worker thread
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    # run flask
    app.run(host="0.0.0.0", port=PORT)
