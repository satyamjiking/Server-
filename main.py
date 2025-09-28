# main.py  — Render-ready Selenium messenger sender
import os
import time
import threading
from flask import Flask
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, WebDriverException

load_dotenv()

# Config (set these via Render Environment)
FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASS = os.getenv("FB_PASS", "")
FILE_PATH = os.getenv("FILE_PATH", "file.txt")
TARGETS_PATH = os.getenv("TARGETS_PATH", "targets.txt")
DELAY = float(os.getenv("DELAY", "8"))       # seconds between messages
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1","true","yes")
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
    ]
    driver_bins = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromium-driver",
    ]
    chrome = next((p for p in chrome_bins if os.path.exists(p)), None)
    driver = next((p for p in driver_bins if os.path.exists(p)), None)
    return chrome, driver

def create_driver():
    chrome_bin, chromedriver_bin = detect_bins()
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

    service = Service(chromedriver_bin) if chromedriver_bin else None
    try:
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        # Try without explicit service (let webdriver try)
        print("webdriver start failed:", e)
        raise
    driver.set_page_load_timeout(30)
    return driver

def login_messenger(driver):
    try:
        driver.get("https://www.messenger.com/login")
        time.sleep(2)
        # find email/pass fields (selectors may change; update if needed)
        email = driver.find_element(By.ID, "email")
        password = driver.find_element(By.ID, "pass")
        email.clear(); email.send_keys(FB_EMAIL)
        password.clear(); password.send_keys(FB_PASS)
        try:
            btn = driver.find_element(By.NAME, "login")
            btn.click()
        except Exception:
            password.submit()
        time.sleep(6)
        print("Login attempt, current_url:", driver.current_url)
        return True
    except Exception as e:
        print("Login error:", e)
        return False

def find_input_box(driver):
    # try several selectors for message input
    candidates = [
        "div[contenteditable='true']",
        "textarea",
        "input[placeholder='Aa']",
        "div._1mf._1mj",   # older facebook selector (may vary)
    ]
    for sel in candidates:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            return el
        except Exception:
            continue
    return None

def send_messages_worker():
    # small startup delay
    time.sleep(3)

    # validate credentials
    if not FB_EMAIL or not FB_PASS:
        print("FB_EMAIL / FB_PASS not set in environment. Exiting worker.")
        return

    try:
        driver = create_driver()
    except Exception as e:
        print("Could not start webdriver:", e)
        return

    if not login_messenger(driver):
        print("Login failed. Quitting driver.")
        driver.quit()
        return

    messages = read_lines(FILE_PATH)
    targets = read_lines(TARGETS_PATH)
    if not messages:
        print("No messages to send (file.txt empty). Quitting.")
        driver.quit()
        return
    if not targets:
        print("No targets (targets.txt empty). Quitting.")
        driver.quit()
        return

    print(f"Starting send loop: {len(messages)} messages x {len(targets)} targets.")
    try:
        while True:
            for t in targets:
                # open thread (may need to adapt format if target is cid or fbid)
                url = f"https://www.messenger.com/t/{t}"
                try:
                    driver.get(url)
                    time.sleep(4)
                except Exception as e:
                    print("Failed to open thread", t, e)
                    continue

                input_box = find_input_box(driver)
                if not input_box:
                    print("Input box not found for target", t)
                    continue

                for msg in messages:
                    try:
                        try:
                            input_box.click()
                        except Exception:
                            pass
                        # try clear
                        try:
                            input_box.clear()
                        except Exception:
                            pass
                        input_box.send_keys(msg)
                        # press Enter to send
                        try:
                            input_box.send_keys("\n")
                        except Exception:
                            # fallback: try clicking send button
                            try:
                                send_btn = driver.find_element(By.XPATH, "//button[contains(., 'Send') or contains(., 'send')]")
                                send_btn.click()
                            except Exception:
                                pass
                        print("Sent to", t, "->", msg[:80])
                    except Exception as e:
                        print("Error sending to", t, e)
                    time.sleep(DELAY)
                # small pause between targets
                time.sleep(2)
            # pause before repeating full cycle
            time.sleep(5)
    except Exception as e:
        print("Worker loop exception:", e)
    finally:
        try:
            driver.quit()
        except:
            pass

worker_started = False
# Worker ko direct start kar do jab app launch ho
if not worker_started:
    t = threading.Thread(target=send_messages_worker, daemon=True)
    t.start()
    worker_started = True
        worker_started = True

@app.route("/")
def index():
    return "Bot running (Selenium worker). Check service logs."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
