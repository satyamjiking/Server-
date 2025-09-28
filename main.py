# main.py -- Render-ready Selenium messenger sender
import os
import time
import base64
import json
import threading
from flask import Flask
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException, NoSuchElementException

# optional webdriver-manager fallback
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except Exception:
    WEBDRIVER_MANAGER_AVAILABLE = False

load_dotenv()

# Config (set in Render environment variables)
FB_EMAIL = os.getenv("FB_EMAIL", "").strip()
FB_PASS = os.getenv("FB_PASS", "").strip()
FB_COOKIES_B64 = os.getenv("FB_COOKIES_B64", "").strip()  # base64 encoded JSON array of cookies (preferred)
FILE_PATH = os.getenv("FILE_PATH", "file.txt")
TARGETS_PATH = os.getenv("TARGETS_PATH", "targets.txt")
DELAY = float(os.getenv("DELAY", "8"))
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
PORT = int(os.getenv("PORT", "4000"))

app = Flask(__name__)

def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f.readlines() if ln.strip()]

def detect_bins():
    chrome_bins = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
        "/opt/google/chrome/chrome",
    ]
    driver_bins = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromium-driver",
        "/snap/bin/chromedriver",
        "/opt/chromedriver/chromedriver",
    ]
    chrome = next((p for p in chrome_bins if os.path.exists(p)), None)
    driver = next((p for p in driver_bins if os.path.exists(p)), None)
    return chrome, driver

def create_driver():
    chrome_bin, chromedriver_bin = detect_bins()
    options = webdriver.ChromeOptions()
    if HEADLESS:
        try:
            options.add_argument("--headless=new")
        except Exception:
            options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    if chrome_bin:
        options.binary_location = chrome_bin

    try:
        if chromedriver_bin:
            service = Service(chromedriver_bin)
            driver = webdriver.Chrome(service=service, options=options)
            print("[INFO] Started webdriver using system chromedriver:", chromedriver_bin)
            driver.set_page_load_timeout(30)
            return driver
        if WEBDRIVER_MANAGER_AVAILABLE:
            print("[INFO] chromedriver not found; downloading with webdriver-manager.")
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            return driver
        raise RuntimeError("Chrome/Chromedriver not found and webdriver-manager unavailable.")
    except WebDriverException as e:
        print("[ERROR] webdriver start failed:", e)
        raise

def apply_cookies_from_b64(driver, b64):
    try:
        j = base64.b64decode(b64).decode("utf-8")
        cookies = json.loads(j)
        if not isinstance(cookies, list):
            print("[WARN] cookies JSON is not a list.")
            return False
    except Exception as e:
        print("[WARN] Failed to decode FB_COOKIES_B64:", e)
        return False

    # navigate to facebook domain to allow adding cookies
    driver.get("https://www.facebook.com")
    time.sleep(1)
    added = 0
    for c in cookies:
        try:
            cookie = {
                "name": c.get("name"),
                "value": c.get("value"),
                "domain": c.get("domain", ".facebook.com"),
                "path": c.get("path", "/"),
            }
            if "expiry" in c:
                cookie["expiry"] = c["expiry"]
            driver.add_cookie(cookie)
            added += 1
        except Exception as e:
            print("[WARN] add_cookie failed for", c.get("name"), e)
    if added:
        driver.refresh()
        time.sleep(2)
        print(f"[INFO] Injected {added} cookies and refreshed.")
        return True
    return False

def login_messenger(driver):
    # try cookie-based session restore first
    if FB_COOKIES_B64:
        try:
            ok = apply_cookies_from_b64(driver, FB_COOKIES_B64)
            if ok:
                driver.get("https://www.messenger.com")
                time.sleep(3)
                cur = driver.current_url.lower()
                print("[INFO] After cookie injection, url:", cur)
                if "login" not in cur and "checkpoint" not in cur:
                    return True
                print("[INFO] Cookies did not produce logged-in session.")
        except Exception as e:
            print("[WARN] cookie login failed:", e)

    # fallback to form login
    if not FB_EMAIL or not FB_PASS:
        print("[WARN] No credentials for form login provided.")
        return False
    try:
        driver.get("https://www.messenger.com/login")
        time.sleep(2)
        try:
            email = driver.find_element(By.ID, "email")
            password = driver.find_element(By.ID, "pass")
            email.clear(); email.send_keys(FB_EMAIL)
            password.clear(); password.send_keys(FB_PASS)
            try:
                btn = driver.find_element(By.NAME, "login")
                btn.click()
            except Exception:
                password.send_keys(Keys.ENTER)
        except NoSuchElementException:
            driver.get("https://www.facebook.com/login")
            time.sleep(2)
            email = driver.find_element(By.ID, "email")
            password = driver.find_element(By.ID, "pass")
            email.clear(); email.send_keys(FB_EMAIL)
            password.clear(); password.send_keys(FB_PASS)
            password.send_keys(Keys.ENTER)
        time.sleep(6)
        cur = driver.current_url.lower()
        print("[INFO] Login attempt, current_url:", cur)
        if "login" in cur or "checkpoint" in cur:
            print("[WARN] login appears unsuccessful (login/checkpoint in URL).")
            return False
        return True
    except Exception as e:
        print("[ERROR] Login error:", e)
        return False

def find_input_box(driver):
    candidates = [
        "div[contenteditable='true']",
        "textarea",
        "input[placeholder='Aa']",
        "div._1mf._1mj",
    ]
    for sel in candidates:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            return el
        except Exception:
            continue
    return None

def send_messages_worker():
    time.sleep(3)
    if not ((FB_EMAIL and FB_PASS) or FB_COOKIES_B64):
        print("[FATAL] No credentials/cookies provided. Set FB_EMAIL/FB_PASS or FB_COOKIES_B64.")
        return

    try:
        driver = create_driver()
    except Exception as e:
        print("[FATAL] Could not start webdriver:", e)
        return

    if not login_messenger(driver):
        print("[FATAL] Login failed. Quitting driver.")
        try: driver.quit()
        except: pass
        return

    messages = read_lines(FILE_PATH)
    targets = read_lines(TARGETS_PATH)
    if not messages:
        print("[FATAL] No messages found in", FILE_PATH)
        driver.quit()
        return
    if not targets:
        print("[FATAL] No targets found in", TARGETS_PATH)
        driver.quit()
        return

    print(f"[INFO] Starting send loop: {len(messages)} messages x {len(targets)} targets")
    try:
        while True:
            for t in targets:
                url = f"https://www.messenger.com/t/{t}"
                try:
                    driver.get(url)
                    time.sleep(4)
                except Exception as e:
                    print("[WARN] Failed to open thread", t, e)
                    continue

                input_box = find_input_box(driver)
                if not input_box:
                    print("[WARN] Input box not found for target", t)
                    continue

                for msg in messages:
                    try:
                        try: input_box.click()
                        except: pass
                        try: input_box.clear()
                        except: pass
                        input_box.send_keys(msg)
                        input_box.send_keys(Keys.ENTER)
                        print("[SENT]", t, "->", msg[:120])
                    except Exception as e:
                        print("[ERROR] sending to", t, e)
                    time.sleep(DELAY)
                time.sleep(2)
            time.sleep(5)
    except Exception as e:
        print("[ERROR] Worker loop exception:", e)
    finally:
        try: driver.quit()
        except: pass

# start worker thread
worker_started = False
def start_background_worker():
    global worker_started
    if not worker_started:
        t = threading.Thread(target=send_messages_worker, daemon=True)
        t.start()
        worker_started = True

start_background_worker()

@app.route("/")
def index():
    return "Selenium messenger bot running. Check logs."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
