# main.py — Render-ready Selenium messenger sender (Debug Mode)
import os
import time
import threading
from flask import Flask
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

load_dotenv()

# Config (Render Env Variables)
FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASS = os.getenv("FB_PASS", "")
FILE_PATH = os.getenv("FILE_PATH", "file.txt")
TARGETS_PATH = os.getenv("TARGETS_PATH", "targets.txt")
DELAY = float(os.getenv("DELAY", "8"))  # seconds between messages
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
PORT = int(os.getenv("PORT", "4000"))

app = Flask(__name__)

def read_lines(path):
    if not os.path.exists(path):
        print(f"[ERROR] File not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    print(f"[INFO] Loaded {len(lines)} lines from {path}")
    return lines

def detect_bins():
    chrome_bins = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    driver_bins = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromium-driver",
    ]
    chrome = next((p for p in chrome_bins if os.path.exists(p)), None)
    driver = next((p for p in driver_bins if os.path.exists(p)), None)
    print(f"[DEBUG] chrome_bin={chrome}, chromedriver_bin={driver}")
    return chrome, driver

def create_driver():
    chrome_bin, chromedriver_bin = detect_bins()
    if not chrome_bin or not chromedriver_bin:
        raise RuntimeError("Chrome or Chromedriver not found in container!")

    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    if chrome_bin:
        options.binary_location = chrome_bin

    service = Service(chromedriver_bin)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    print("[INFO] ChromeDriver started successfully")
    return driver

def login_messenger(driver):
    try:
        print("[INFO] Navigating to Messenger login...")
        driver.get("https://www.messenger.com/login")
        time.sleep(2)
        email = driver.find_element(By.ID, "email")
        password = driver.find_element(By.ID, "pass")
        email.clear(); email.send_keys(FB_EMAIL)
        password.clear(); password.send_keys(FB_PASS)
        btn = driver.find_element(By.NAME, "login")
        btn.click()
        time.sleep(6)
        print("[INFO] Login attempt done, current URL:", driver.current_url)
        return True
    except Exception as e:
        print("[ERROR] Login failed:", e)
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
            return driver.find_element(By.CSS_SELECTOR, sel)
        except:
            continue
    return None

def send_messages_worker():
    print("[WORKER] Worker thread started")
    if not FB_EMAIL or not FB_PASS:
        print("[FATAL] FB_EMAIL / FB_PASS not set in env variables.")
        return

    try:
        driver = create_driver()
    except Exception as e:
        print("[FATAL] Could not start webdriver:", e)
        return

    if not login_messenger(driver):
        print("[FATAL] Login failed. Exiting worker.")
        driver.quit()
        return

    messages = read_lines(FILE_PATH)
    targets = read_lines(TARGETS_PATH)
    if not messages:
        print("[FATAL] No messages found, quitting.")
        driver.quit()
        return
    if not targets:
        print("[FATAL] No targets found, quitting.")
        driver.quit()
        return

    print(f"[INFO] Starting loop: {len(messages)} messages x {len(targets)} targets")
    try:
        while True:
            for t in targets:
                url = f"https://www.messenger.com/t/{t}"
                try:
                    driver.get(url)
                    print(f"[INFO] Opened chat with {t}")
                    time.sleep(4)
                except Exception as e:
                    print("[ERROR] Failed to open thread", t, e)
                    continue

                input_box = find_input_box(driver)
                if not input_box:
                    print("[ERROR] Input box not found for", t)
                    continue

                for msg in messages:
                    try:
                        input_box.click()
                        try: input_box.clear()
                        except: pass
                        input_box.send_keys(msg + "\n")
                        print(f"[SENT] To {t}: {msg[:80]}")
                    except Exception as e:
                        print("[ERROR] Sending to", t, "->", e)
                    time.sleep(DELAY)
                time.sleep(2)
            print("[LOOP] Cycle complete, sleeping 5s")
            time.sleep(5)
    except Exception as e:
        print("[EXCEPTION] Worker crashed:", e)
    finally:
        try:
            driver.quit()
        except:
            pass

# 🚀 Worker auto start
t = threading.Thread(target=send_messages_worker, daemon=True)
t.start()

@app.route("/")
def index():
    return "✅ Bot running (check Render logs for debug info)"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
