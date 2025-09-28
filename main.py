# main.py — Messenger bot using Selenium + cookies.json
import os
import time
import threading
import json
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# Config
FILE_PATH = os.getenv("FILE_PATH", "file.txt")
TARGETS_PATH = os.getenv("TARGETS_PATH", "targets.txt")
DELAY = float(os.getenv("DELAY", "8"))  # seconds between messages
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
    if chrome_bin:
        options.binary_location = chrome_bin

    service = Service(chromedriver_bin) if chromedriver_bin else None
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def load_cookies(driver):
    try:
        with open("cookies.json", "r", encoding="utf-8") as f:
            cookies = json.load(f)
        driver.get("https://www.messenger.com")
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print("Cookie inject fail:", cookie.get("name"), e)
        driver.refresh()
        print("✅ Cookies injected, session refreshed.")
    except Exception as e:
        print("Cookie load error:", e)

def find_input_box(driver):
    selectors = [
        "div[contenteditable='true']",
        "textarea",
        "input[placeholder='Aa']",
        "div._1mf._1mj",
    ]
    for sel in selectors:
        try:
            return driver.find_element(By.CSS_SELECTOR, sel)
        except:
            continue
    return None

def send_messages_worker():
    time.sleep(3)

    try:
        driver = create_driver()
    except Exception as e:
        print("Could not start webdriver:", e)
        return

    load_cookies(driver)

    messages = read_lines(FILE_PATH)
    targets = read_lines(TARGETS_PATH)

    if not messages:
        print("No messages (file.txt empty).")
        driver.quit()
        return
    if not targets:
        print("No targets (targets.txt empty).")
        driver.quit()
        return

    print(f"Starting loop: {len(messages)} messages x {len(targets)} targets.")
    try:
        while True:
            for t in targets:
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
                        input_box.click()
                        try:
                            input_box.clear()
                        except:
                            pass
                        input_box.send_keys(msg + "\n")
                        print("✅ Sent to", t, "->", msg[:80])
                    except Exception as e:
                        print("Send error to", t, e)
                    time.sleep(DELAY)
                time.sleep(2)
            time.sleep(5)
    except Exception as e:
        print("Worker loop exception:", e)
    finally:
        try:
            driver.quit()
        except:
            pass

# Start worker automatically
t = threading.Thread(target=send_messages_worker, daemon=True)
t.start()

@app.route("/")
def index():
    return "Bot running with cookies.json (Selenium worker). Check logs."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
