# main.py (debug-ready)
import os, time, threading, sys, traceback
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# Environment
FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASS = os.getenv("FB_PASS", "")
FILE_PATH = os.getenv("FILE_PATH", "file.txt")
TARGETS_PATH = os.getenv("TARGETS_PATH", "targets.txt")
DELAY = float(os.getenv("DELAY", "8"))
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1","true","yes")
PORT = int(os.getenv("PORT", "10000"))

# Optional explicit paths (set these in Render env if needed)
CHROME_BIN = os.getenv("CHROME_BIN")      # e.g. /usr/bin/chromium-browser
CHROMEDRIVER_BIN = os.getenv("CHROMEDRIVER_BIN")  # e.g. /usr/bin/chromedriver

app = Flask(__name__)

def log(*a, **k):
    print("[BOT]", *a, **k)
    sys.stdout.flush()

def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

def detect_bins():
    chrome_bins = [CHROME_BIN, "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"]
    driver_bins = [CHROMEDRIVER_BIN, "/usr/bin/chromedriver", "/usr/local/bin/chromedriver", "/usr/bin/chromium-driver"]
    chrome = next((p for p in chrome_bins if p and os.path.exists(p)), None)
    driver = next((p for p in driver_bins if p and os.path.exists(p)), None)
    return chrome, driver

def create_driver():
    chrome_bin, chromedriver_bin = detect_bins()
    log("DEBUG: chrome_bin=", chrome_bin, " chromedriver_bin=", chromedriver_bin)
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-extensions")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100 Safari/537.36")
    if chrome_bin:
        options.binary_location = chrome_bin

    service = Service(chromedriver_bin) if chromedriver_bin else None
    try:
        if service:
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
    except Exception as e:
        log("FATAL: Could not start webdriver:", e)
        traceback.print_exc()
        raise
    driver.set_page_load_timeout(30)
    return driver

def login_messenger(driver):
    try:
        log("Opening messenger login page...")
        driver.get("https://www.messenger.com/login")
        time.sleep(2)
        # selectors
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
        log("After login, current_url:", driver.current_url)
        # quick check: are we logged in?
        if "login" in driver.current_url.lower():
            log("Login seems to have failed or is stuck on login page.")
            return False
        return True
    except Exception as e:
        log("Login error:", e)
        traceback.print_exc()
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
    log("Worker starting - checking envs...")
    log("FB_EMAIL set:", bool(FB_EMAIL), " FB_PASS set:", bool(FB_PASS))
    messages = read_lines(FILE_PATH)
    targets = read_lines(TARGETS_PATH)
    log("Found messages:", len(messages), " targets:", len(targets))
    if not FB_EMAIL or not FB_PASS:
        log("FB_EMAIL/FB_PASS missing. Exiting worker.")
        return
    if not messages or not targets:
        log("Missing file.txt or targets.txt content. Exiting worker.")
        return

    try:
        driver = create_driver()
    except Exception:
        log("Driver init failed — worker exiting.")
        return

    try:
        if not login_messenger(driver):
            log("Login failed (maybe 2FA or checkpoint). Quitting driver.")
            driver.quit()
            return

        log("Starting send loop")
        while True:
            for t in targets:
                try:
                    url = f"https://www.messenger.com/t/{t}"
                    log("Opening thread:", url)
                    driver.get(url)
                    time.sleep(4)
                except Exception as e:
                    log("Failed to open thread:", t, e)
                    continue

                input_box = find_input_box(driver)
                if not input_box:
                    log("Input box not found for target", t, "— maybe messenger layout changed or blocked")
                    continue

                for msg in messages:
                    try:
                        input_box.click()
                        try: input_box.clear()
                        except: pass
                        input_box.send_keys(msg + "\n")
                        log("Sent to", t, "->", msg[:80])
                    except Exception as e:
                        log("Error sending to", t, e)
                    time.sleep(DELAY)
                time.sleep(2)
            time.sleep(5)

    except Exception as e:
        log("Worker loop exception:", e)
        traceback.print_exc()
    finally:
        try:
            driver.quit()
        except:
            pass

# start worker thread (force-start)
t = threading.Thread(target=send_messages_worker, daemon=True)
t.start()
log("Main: worker thread started (daemon).")

@app.route("/")
def index():
    return "Bot running (Selenium worker). Check logs."

if __name__ == "__main__":
    log("Starting Flask on port", PORT)
    app.run(host="0.0.0.0", port=PORT)
