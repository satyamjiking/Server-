# main.py  — improved debug-friendly selenium messenger script (no cookie/token extraction)
import os
import time
import threading
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# config from env
FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASS  = os.getenv("FB_PASS", "")
FILE_PATH = os.getenv("FILE_PATH", "file.txt")
TARGETS_PATH = os.getenv("TARGETS_PATH", "targets.txt")
DELAY = float(os.getenv("DELAY", "8"))
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1","true","yes")
PORT = int(os.getenv("PORT", "4000"))

app = Flask(__name__)

def read_lines(path):
    if not os.path.exists(path):
        print(f"[WARN] file not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

def detect_bins():
    # common linux paths — adjust if your container has different paths
    chrome_bins = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chrome",
    ]
    driver_bins = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromium-driver",
    ]
    chrome = next((p for p in chrome_bins if os.path.exists(p)), None)
    driver = next((p for p in driver_bins if os.path.exists(p)), None)
    print("[DEBUG] chrome_bin=", chrome, "chromedriver_bin=", driver)
    return chrome, driver

def create_driver():
    chrome_bin, chromedriver_bin = detect_bins()
    options = webdriver.ChromeOptions()
    if HEADLESS:
        # older/new headless flags vary by chrome version
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    if chrome_bin:
        options.binary_location = chrome_bin

    service = Service(chromedriver_bin) if chromedriver_bin else None
    try:
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print("[FATAL] webdriver start failed:", e)
        raise
    driver.set_page_load_timeout(30)
    return driver

def login_messenger(driver):
    print("[INFO] opening messenger login")
    driver.get("https://www.messenger.com/login")
    try:
        wait = WebDriverWait(driver, 15)
        # wait for email field
        email_el = wait.until(EC.presence_of_element_located((By.ID, "email")))
        pass_el = driver.find_element(By.ID, "pass")
        email_el.clear(); email_el.send_keys(FB_EMAIL)
        pass_el.clear(); pass_el.send_keys(FB_PASS)
        # click login
        try:
            login_btn = driver.find_element(By.NAME, "login")
            login_btn.click()
        except:
            pass
        # wait for either login form to reappear OR for messenger thread page to load
        time.sleep(4)
        # check if login succeeded by waiting for url or an element present in logged-in messenger
        if "login" in driver.current_url.lower():
            print("[WARN] current_url still contains 'login'. Trying longer wait...")
            time.sleep(6)
        print("[DEBUG] post-login current_url:", driver.current_url)
        # try to detect message-input or inbox presence
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox'], div[contenteditable='true']"))
            )
            print("[INFO] Login appears successful (message input present).")
            return True
        except Exception:
            print("[WARN] message input not found after login. current_url:", driver.current_url)
            # save page snippet for debug
            snippet = driver.page_source[:4000]
            print("[PAGE-SOURCE-SNIPPET]\n", snippet)
            # try to take screenshot for later inspection (saved in container)
            try:
                screenshot_path = "/tmp/messenger_login_error.png"
                driver.save_screenshot(screenshot_path)
                print("[INFO] screenshot saved to", screenshot_path)
            except Exception as e:
                print("[WARN] screenshot failed:", e)
            return False
    except Exception as e:
        print("[ERROR] login flow exception:", e)
        return False

def find_input_box(driver):
    selectors = [
        "div[role='textbox']",
        "div[contenteditable='true']",
        "textarea",
        "input[placeholder='Aa']",
    ]
    for s in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, s)
            print("[DEBUG] found input selector:", s)
            return el
        except Exception:
            continue
    print("[DEBUG] no input box found; returning None")
    return None

def send_messages_worker():
    time.sleep(2)
    if not FB_EMAIL or not FB_PASS:
        print("[FATAL] FB_EMAIL/FB_PASS not set in env. Exiting worker.")
        return

    try:
        driver = create_driver()
    except Exception as e:
        print("[FATAL] Could not start webdriver; aborting worker.")
        return

    if not login_messenger(driver):
        print("[FATAL] login failed. quitting driver.")
        try: driver.quit()
        except: pass
        return

    messages = read_lines(FILE_PATH)
    targets = read_lines(TARGETS_PATH)
    print("[INFO] messages:", len(messages), "targets:", len(targets))
    if not messages or not targets:
        print("[FATAL] messages or targets empty. quitting.")
        driver.quit()
        return

    try:
        while True:
            for t in targets:
                url = f"https://www.messenger.com/t/{t}"
                print("[INFO] opening target:", t, "->", url)
                try:
                    driver.get(url)
                    # wait for input box on thread page
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox'], div[contenteditable='true']"))
                    )
                except Exception as e:
                    print("[WARN] failed to open thread or find input for target", t, "err:", e)
                    # save snippet for debugging
                    try:
                        path = f"/tmp/page_{t[:8]}.html"
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(driver.page_source[:10000])
                        print("[DEBUG] wrote page snippet to", path)
                    except Exception as ex:
                        print("[WARN] could not write page snippet:", ex)
                    continue

                input_box = find_input_box(driver)
                if not input_box:
                    print("[WARN] input box not found for", t)
                    continue

                for msg in messages:
                    try:
                        # ensure focus & send
                        input_box.click()
                        try: input_box.clear()
                        except: pass
                        input_box.send_keys(msg)
                        # send with Enter
                        input_box.send_keys("\n")
                        print("[SENT]", t, msg[:60])
                    except Exception as e:
                        print("[ERROR] send failed for", t, e)
                    time.sleep(DELAY)

                time.sleep(2)
            time.sleep(5)
    except Exception as e:
        print("[FATAL] Worker loop exception:", e)
    finally:
        try: driver.quit()
        except: pass

# start worker as daemon thread on boot
worker_thread = threading.Thread(target=send_messages_worker, daemon=True)
worker_thread.start()

@app.route("/")
def index():
    return "Bot running (Selenium worker). Check logs."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
