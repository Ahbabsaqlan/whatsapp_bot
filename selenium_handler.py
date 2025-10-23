# selenium_handler.py
import os
import sys
import json
import time
import re
import platform
import random
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from database_manager import normalize_phone_number

def load_selectors(filename="selectors.json"):
    """Loads selectors from a JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            print(f"📄 Loading selectors from '{filename}'...")
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ FATAL ERROR: Selector file '{filename}' not found. Please create it next to the script.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ FATAL ERROR: Could not decode JSON from '{filename}'. Please check its format.")
        sys.exit(1)

SELECTORS = load_selectors()

def get_element(driver, key, timeout=10, find_all=False, wait_condition=EC.presence_of_element_located, format_args=None, suppress_error=False, context_message=None):
    """Safely finds elements, reporting detailed, contextual errors on failure."""
    try:
        selector_value = SELECTORS[key]
        if format_args:
            selector_value = selector_value.format(*format_args)
        by = By.XPATH if selector_value.startswith(('//', './', '(')) else By.CSS_SELECTOR
        wait = WebDriverWait(driver, timeout)
        locator = (by, selector_value)
        if find_all:
            wait_condition = EC.presence_of_all_elements_located if wait_condition == EC.presence_of_element_located else wait_condition
            return wait.until(wait_condition(locator))
        else:
            return wait.until(wait_condition(locator))
    except TimeoutException:
        if not suppress_error:
            print(f"\n- - - - - [ DIAGNOSTIC INFO ] - - - - -")
            if context_message: print(f"❗ GOAL: {context_message}")
            else: print("❗ GOAL: A required element could not be found.")
            print(f"   - FAILED SELECTOR KEY: '{key}'")
            print(f"   - SELECTOR PATH USED: '{SELECTORS.get(key, 'N/A')}'")
            print(f"- - - - - - - - - - - - - - - - - - - - -")
        return [] if find_all else None
    except StaleElementReferenceException:
        if not suppress_error: print(f"⚠️ Warning: Element for selector key '{key}' became stale.")
        return [] if find_all else None

def open_whatsapp():
    """
    Opens WhatsApp Web with a robust, cache-first ChromeDriver setup.
    """
    session_dir = ensure_session_dir()
    options = Options()
    options.add_argument(f"--user-data-dir={os.path.abspath(session_dir)}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")

    driver_path = None
    try:
        print("🌐 Checking for latest ChromeDriver...")
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
    except Exception as e:
        print(f"⚠️ Could not connect to download ChromeDriver: {e}")
        print("... Attempting to find and use a cached version of ChromeDriver.")
        
        cache_dir = os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "chromedriver")
        if os.path.exists(cache_dir):
            version_dirs = [d for d in os.listdir(cache_dir) if os.path.isdir(os.path.join(cache_dir, d))]
            if version_dirs:
                latest_version = sorted(version_dirs, reverse=True)[0]
                exe_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
                for root, dirs, files in os.walk(os.path.join(cache_dir, latest_version)):
                    if exe_name in files:
                        driver_path = os.path.join(root, exe_name)
                        break
        
        if driver_path and os.path.exists(driver_path):
            print(f"Found cached driver at: {driver_path}")
            service = Service(driver_path)
        else:
            print("❌ No cached driver found. Please connect to the internet to run the script for the first time.")
            sys.exit(1)
            
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.get("https://web.whatsapp.com")
    print("📱 Please scan the QR code if not already logged in...")
    if not get_element(driver, "login_check", timeout=60, context_message="Wait for main chat page to load."):
        print("❌ Login timed out. Exiting."); driver.quit(); sys.exit(1)
    
    print("✅ Login successful."); return driver

def ensure_session_dir():
    session_dir = "whatsapp_automation_profile"
    if not os.path.exists(session_dir): os.makedirs(session_dir)
    return session_dir

def get_all_contacts(driver):
    try: chat_list = driver.find_element(By.ID, SELECTORS["chat_list_pane_id"])
    except NoSuchElementException: return []
    contacts_set, last_height, consecutive_no_change = set(), -1, 0
    while consecutive_no_change < 3:
        for el in get_element(driver, "chat_list_titles", timeout=2, find_all=True):
            try:
                name = sanitize_contact_name(el.get_attribute("title"))
                if name: contacts_set.add(name.strip())
            except StaleElementReferenceException: continue
        driver.execute_script("arguments[0].scrollTop += 300;", chat_list)
        time.sleep(1)
        new_height = driver.execute_script("return arguments[0].scrollTop", chat_list)
        if new_height == last_height: consecutive_no_change += 1
        else: consecutive_no_change, last_height = 0, new_height
        if new_height >= driver.execute_script("return arguments[0].scrollHeight", chat_list): break
    return list(contacts_set)

def sanitize_contact_name(name):
    return re.sub(r'[^\u0000-\uFFFF]', '', name) if name else ""

def open_chat(driver, contact_name, processed_items, retries=3):
    """Modified to not require a phone number and to check a combined processed set."""
    for attempt in range(retries):
        search_box = get_element(driver, "search_box", context_message="Find main chat search box.")
        if not search_box: return None, None
        os_name = platform.system()
        search_box.click(); time.sleep(0.5)
        search_box.send_keys(Keys.COMMAND + "a" if os_name != "Windows" else Keys.CONTROL + "a")
        search_box.send_keys(Keys.BACKSPACE); time.sleep(0.5)
        search_box.send_keys(contact_name); time.sleep(2)
        chat_results = get_element(driver, "search_result_contact_template", find_all=True, format_args=[contact_name], context_message=f"Find '{contact_name}' in search results.")
        if not chat_results:
            print(f"⚠️ Attempt {attempt+1}: No results for '{contact_name}'. Retrying..."); time.sleep(2); continue
        
        for result_index in range(len(chat_results)):
            current_result_list = get_element(driver, "search_result_contact_template", find_all=True, format_args=[contact_name])
            if not current_result_list or len(current_result_list) <= result_index: continue
            current_result_list[result_index].click(); time.sleep(1)
            
            actual_contact_name, phone_number = get_details_from_header(driver)
            if not actual_contact_name:
                print("⚠️ Could not get contact name from header. Skipping search result.")
                continue

            unique_id = phone_number if phone_number else actual_contact_name
            if unique_id in processed_items: continue
            
            return actual_contact_name, phone_number
    return None, None

def get_details_from_header(driver):
    """
    Helper function to get name and number from the header of an OPEN chat.
    This now includes robust logic to handle all contact types, including swapped names.
    """
    actual_contact_name = None
    phone_number = None

    contact_header = get_element(driver, "chat_header_name", context_message="Read contact's name from header.")
    if not contact_header:
        return None, None
    
    actual_contact_name = contact_header.text.strip()
    
    contact_header.click()
    time.sleep(1)
    
    phone_element = get_element(driver, "contact_info_phone_number", timeout=5, suppress_error=True)

    if phone_element:
        phone_text = phone_element.text.strip()
        if phone_text.startswith('~'):
            print(f"ℹ️ Swapped Name/Number detected. Normalizing.")
            final_name = phone_text
            final_number = actual_contact_name
        else:
            final_name = actual_contact_name
            final_number = phone_text
    else:
        if actual_contact_name.startswith('+'):
            print(f"ℹ️ Unsaved contact detected. Using number as title.")
            final_name = actual_contact_name
            final_number = actual_contact_name
        else:
            print(f"ℹ️ Group or contact without a number detected: '{actual_contact_name}'")
            final_name = actual_contact_name
            final_number = None

    body_element = get_element(driver, "body_tag_name")
    if body_element:
        body_element.send_keys(Keys.ESCAPE)
        time.sleep(1)
    

    final_number = normalize_phone_number(final_number)

    print(f"    ↳ Final Name='{final_name}', Final Number='{final_number or 'None'}'")
    return final_name, final_number

def smart_scroll_and_collect(driver, stop_at_last=None):
    """
    Scrolls up the chat pane page by page, collecting messages as it goes.
    Stops scrolling as soon as the 'stop_at_last' message's meta_text is found.
    This is far more efficient than scrolling all the way to the top first.
    """
    chat_container = get_element(driver, "chat_container", timeout=10)
    if not chat_container:
        print("❌ Could not find chat container to scroll and collect messages.")
        return []

    all_messages_data = []
    seen_meta_texts = set()
    found_stop_point = False

    max_scrolls = 50 
    scroll_count = 0

    while not found_stop_point and scroll_count < max_scrolls:
        current_visible_messages = get_element(driver, "all_messages", find_all=True, suppress_error=True)
        
        if not current_visible_messages:
            break

        new_messages_found_this_scroll = False
        for msg_element in reversed(current_visible_messages):
            parsed = parse_message(msg_element)
            if parsed:
                if parsed['meta_text'] in seen_meta_texts:
                    continue
                
                new_messages_found_this_scroll = True
                all_messages_data.append(parsed)
                seen_meta_texts.add(parsed['meta_text'])

                if stop_at_last and parsed['meta_text'] == stop_at_last:
                    print(f"⏹️ Reached previously stored last message. Stopping scroll and collection.")
                    found_stop_point = True
                    all_messages_data.pop() 
                    break

        if found_stop_point:
            break

        if not new_messages_found_this_scroll:
            print("Reached top of chat or found no new messages on this scroll.")
            break
            
        driver.execute_script("arguments[0].scrollTop = 0;", chat_container)
        print("   ...scrolling up for older messages...")
        time.sleep(2)
        scroll_count += 1

    if scroll_count >= max_scrolls:
        print(f"⚠️ Reached maximum scroll limit of {max_scrolls}. Proceeding with collected messages.")

    return all_messages_data[::-1]


def parse_message(msg):
    try:
        meta_div = msg.find_element(By.CSS_SELECTOR, SELECTORS["message_meta_data"])
        meta_text = meta_div.get_attribute("data-pre-plain-text")
        
        match = re.match(r"\[(.*?), (.*?)\] (.*?):", meta_text)
        if not match: return None
        time_str, date_str, sender = match.groups()
        content = "📎 Media (Image/Video/Doc)"
        try:
            text_element = msg.find_element(By.CSS_SELECTOR, SELECTORS["message_text_content"])
            text = text_element.text.strip()
            if text: content = text
        except NoSuchElementException: pass
            
        return {"date": date_str.strip(), "time": time_str.strip(), "sender": sender.strip(), "content": content.strip(), "meta_text": meta_text}
    except (NoSuchElementException, StaleElementReferenceException): return None


def send_reply(driver, reply_text):
    """
    Finds the message box and types the reply word-by-word to appear more human.
    """
    # --- Humanization Settings ---
    MIN_WORD_DELAY = 0.2  # Minimum delay between words in seconds
    MAX_WORD_DELAY = 0.6  # Maximum delay between words in seconds
    
    message_box = get_element(driver, "reply_message_box")
    if not message_box:
        print("❌ Could not find message box to send reply.")
        return
        
    message_box.click()
    time.sleep(0.5) # A small initial delay after clicking

    words = reply_text.split()
    for i, word in enumerate(words):
        try:
            # Type the word
            message_box.send_keys(word)
            
            # If it's not the last word, add a space and pause
            if i < len(words) - 1:
                message_box.send_keys(' ')
                delay = random.uniform(MIN_WORD_DELAY, MAX_WORD_DELAY)
                time.sleep(delay)
        except Exception as e:
            print(f"⚠️ Error while typing word '{word}': {e}")
            # If something goes wrong, fallback to sending the rest of the message at once
            remaining_text = ' '.join(words[i:])
            message_box.send_keys(remaining_text)
            break
            
    # Press Enter to send the message
    message_box.send_keys(Keys.ENTER)
    print(f"💬 Replied to chat.")
    time.sleep(1)


def close_current_chat(driver):
    """
    Closes the current chat using the explicit Menu -> Close chat action.
    """
    try:
        menu_button = get_element(driver, "chat_menu_button", timeout=5, context_message="Find chat menu (three dots).")
        if not menu_button:
            print("⚠️ Could not find chat menu button to close chat.")
            return

        menu_button.click()
        time.sleep(0.5)

        close_option = get_element(driver, "chat_close_option", wait_condition=EC.element_to_be_clickable, context_message="Find 'Close chat' option in menu.")
        if not close_option:
            print("⚠️ Could not find 'Close chat' option in the menu.")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return
            
        close_option.click()
        print("✅ Chat closed successfully via menu.")
        time.sleep(1)

    except Exception as e:
        print(f"❌ An error occurred while trying to close the chat: {e}")