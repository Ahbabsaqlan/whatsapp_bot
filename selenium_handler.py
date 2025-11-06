# selenium_handler.py
import os
import sys
import json
import time
import re
import platform
import random
import pyperclip
import config

from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException,NoSuchWindowException, WebDriverException
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


# def open_whatsapp():
#     """
#     Opens WhatsApp Web with a robust, cache-first ChromeDriver setup.
#     Now includes error handling for network issues.
#     """
#     session_dir = ensure_session_dir()
#     options = Options()
#     options.add_argument(f"--user-data-dir={os.path.abspath(session_dir)}")
#     options.add_argument("--profile-directory=Default")
#     options.add_argument("--start-maximized")

#     driver_path = None
#     try:
#         print("🌐 Checking for latest ChromeDriver...")
#         driver_path = ChromeDriverManager().install()
#         service = Service(driver_path)
#     except Exception as e:
#         print(f"⚠️ Could not connect to download ChromeDriver: {e}")
#         # ... (offline driver finding logic is unchanged) ...
        
#     try:
#         driver = webdriver.Chrome(service=service, options=options)
        
#         print("📱 Navigating to WhatsApp Web...")
#         driver.get("https://web.whatsapp.com")
        
#         print("... Please scan the QR code if not already logged in...")
#         if not get_element(driver, "login_check", timeout=60, context_message="Wait for main chat page to load."):
#             print("❌ Login timed out. Exiting task."); driver.quit(); return None
        
#         print("✅ Login successful."); return driver

#     # --- NEW: Catch network and other web driver errors ---
#     except WebDriverException as e:
#         if "net::ERR_NAME_NOT_RESOLVED" in e.msg or "net::ERR_INTERNET_DISCONNECTED" in e.msg:
#             print("\n❌ Network Error: Could not connect to WhatsApp. Please check your internet connection.")
#         else:
#             print(f"\n❌ A WebDriver error occurred during startup: {e}")
#         return None # Return None to signal failure
#     except Exception as e:
#         print(f"\n❌ An unexpected error occurred while opening WhatsApp: {e}")
#         return None


def open_whatsapp():
    """
    Opens WhatsApp Web, now configured for automatic, non-interactive downloads.
    """
    # --- Step 1: Ensure the attachments directory exists ---
    # This reads the path from your config file.
    if not os.path.exists(config.ATTACHMENTS_DIR):
        os.makedirs(config.ATTACHMENTS_DIR)

    session_dir = ensure_session_dir()
    options = Options()
    
    # --- Step 2: Set Chrome options for automatic downloads ---
    prefs = {
        # Use an absolute path for the download directory.
        "download.default_directory": os.path.abspath(config.ATTACHMENTS_DIR),
        "download.prompt_for_download": False, # This is the key setting to disable the save dialog.
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # --- Step 3: Standard user profile and window size options ---
    options.add_argument(f"--user-data-dir={os.path.abspath(session_dir)}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")

    # --- Step 4: Robust driver installation and startup ---
    driver_path = None
    try:
        print("🌐 Checking for latest ChromeDriver...")
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
    except Exception as e:
        print(f"⚠️ Could not connect to download ChromeDriver: {e}")
        # (Your offline driver finding logic can remain here if you need it)
        
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        print("📱 Navigating to WhatsApp Web...")
        driver.get("https://web.whatsapp.com")
        
        print("... Please scan the QR code if not already logged in...")
        if not get_element(driver, "login_check", timeout=60, context_message="Wait for main chat page to load."):
            print("❌ Login timed out. Exiting task."); driver.quit(); return None
        
        print("✅ Login successful."); return driver

    except WebDriverException as e:
        if "net::ERR_NAME_NOT_RESOLVED" in e.msg or "net::ERR_INTERNET_DISCONNECTED" in e.msg:
            print("\n❌ Network Error: Could not connect to WhatsApp. Please check your internet connection.")
        else:
            print(f"\n❌ A WebDriver error occurred during startup: {e}")
        return None
    except Exception as e:
        print(f"\n❌ An unexpected error occurred while opening WhatsApp: {e}")
        return None


# def _wait_for_download_and_get_filename(expected_filename, timeout=45):
#     """
#     Waits for a specific file to appear in the download directory.
#     This is deterministic and avoids race conditions.
#     """
#     print(f"   ...waiting for '{expected_filename}' to download...")
#     start_time = time.time()
    
#     while time.time() - start_time < timeout:
#         # Check all files in the directory
#         for f in os.listdir(config.ATTACHMENTS_DIR):
#             # Check if a file exists that is NOT a temporary download file
#             if not f.endswith('.crdownload'):
#                 # Check if the downloaded filename contains the expected name.
#                 # WhatsApp sometimes adds numbers like "(1)" if the file already exists.
#                 if expected_filename.split('.')[0] in f:
#                     print(f"   📥 Download complete: {f}")
#                     return f
#         time.sleep(1)

#     print(f"   ⚠️ Download timed out for '{expected_filename}'.")
#     return None


def ensure_session_dir():
    session_dir = "whatsapp_automation_profile"
    if not os.path.exists(session_dir): os.makedirs(session_dir)
    return session_dir

# def get_all_contacts(driver):
#     try: chat_list = driver.find_element(By.ID, SELECTORS["chat_list_pane_id"])
#     except NoSuchElementException: return []
#     contacts_set, last_height, consecutive_no_change = set(), -1, 0
#     while consecutive_no_change < 3:
#         for el in get_element(driver, "chat_list_titles", timeout=2, find_all=True):
#             try:
#                 name = el.get_attribute("title")
#                 if name: contacts_set.add(name.strip())
#                 print(f"   ...found contact: '{name.strip()}'")
#             except StaleElementReferenceException: continue
#         print(f"   ...collected {len(contacts_set)} unique contacts so far...")
#         driver.execute_script("arguments[0].scrollTop += 1200;", chat_list)
#         time.sleep(1)
#         new_height = driver.execute_script("return arguments[0].scrollTop", chat_list)
#         if new_height == last_height: consecutive_no_change += 1
#         else: consecutive_no_change, last_height = 0, new_height
#         if new_height >= driver.execute_script("return arguments[0].scrollHeight", chat_list): break
#     return list(contacts_set)


def get_all_contacts(driver):
    """
    Scrolls through the chat list and scrapes all contact names, preserving duplicates.
    It is resilient to the browser window closing unexpectedly.
    """
    try:
        chat_list = driver.find_element(By.ID, SELECTORS["chat_list_pane_id"])
    except (NoSuchElementException, NoSuchWindowException):
        print("❌ Could not find chat list pane or browser window closed.")
        return []

    contacts_list = []
    seen_element_ids = set() # Use a set to track processed Selenium element IDs

    last_height = -1
    consecutive_no_change = 0

    print("--- Starting contact scraping ---")
    while consecutive_no_change < 4: # Increased for more tolerance on slow loads
        try:
            # Find all potential contact elements in the current view
            contact_elements = get_element(driver, "chat_list_titles", timeout=3, find_all=True)
            
            new_contacts_found_this_scroll = 0
            for el in contact_elements:
                element_id = el.id
                # If we haven't processed this specific element yet...
                if element_id not in seen_element_ids:
                    name = el.get_attribute("title")
                    if name:
                        contacts_list.append(name.strip())
                        new_contacts_found_this_scroll += 1
                    # Mark this element as seen, whether it had a name or not
                    seen_element_ids.add(element_id)

            if new_contacts_found_this_scroll > 0:
                 print(f"   ...found {new_contacts_found_this_scroll} new contacts. Total collected: {len(contacts_list)}")

            # --- Resilient Scrolling ---
            # Get current scroll position and max scroll height before scrolling
            current_scroll = driver.execute_script("return arguments[0].scrollTop", chat_list)
            max_scroll = driver.execute_script("return arguments[0].scrollHeight", chat_list)

            # Scroll down
            driver.execute_script("arguments[0].scrollTop += 500;", chat_list)
            time.sleep(1.5)

            new_height = driver.execute_script("return arguments[0].scrollTop", chat_list)

            # Check if we are at the bottom or if the scroll didn't work
            if new_height == last_height or new_height + driver.execute_script("return arguments[0].offsetHeight", chat_list) >= max_scroll:
                consecutive_no_change += 1
                print(f"   ...scroll position unchanged. Consecutive count: {consecutive_no_change}")
            else:
                consecutive_no_change = 0
                last_height = new_height
        
        except (StaleElementReferenceException, NoSuchWindowException) as e:
            print(f"⚠️ Browser state changed during scroll ({type(e).__name__}). Ending contact collection.")
            break # Exit the loop gracefully
        except Exception as e:
            print(f"❌ An unexpected error occurred during contact scraping: {e}")
            break

    print(f"--- Finished contact scraping. Total entries found: {len(contacts_list)} ---")
    return contacts_list


def open_chat(driver, contact_name, processed_items, retries=3):
    """Modified to use clipboard for searching, ensuring emoji compatibility."""
    for attempt in range(retries):
        search_box = get_element(driver, "search_box", context_message="Find main chat search box.")
        if not search_box: return None, None
        
        os_name = platform.system()
        control_key = Keys.COMMAND if os_name == "Darwin" else Keys.CONTROL
        
        search_box.click(); time.sleep(0.5)
        search_box.send_keys(control_key + "a")
        search_box.send_keys(Keys.BACKSPACE); time.sleep(0.5)
        
        pyperclip.copy(contact_name) 
        search_box.send_keys(control_key + "v") 
        time.sleep(2)
        
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
            

            search_box.click(); time.sleep(0.2)
            search_box.send_keys(control_key + "a")
            search_box.send_keys(Keys.BACKSPACE); time.sleep(0.2)
            return actual_contact_name, phone_number
            
    # Clear search box if search failed completely
    search_box = get_element(driver, "search_box")
    if search_box:
        os_name = platform.system()
        control_key = Keys.COMMAND if os_name == "Darwin" else Keys.CONTROL
        search_box.click(); time.sleep(0.2)
        search_box.send_keys(control_key + "a")
        search_box.send_keys(Keys.BACKSPACE); time.sleep(0.2)
        
    return None, None


def get_details_from_header(driver):
    """
    Gets contact details from the header. This version now includes a fallback
    to find phone numbers on Business Accounts.
    """
    actual_contact_name = None
    phone_number = None

    contact_header = get_element(driver, "chat_header_name", context_message="Read contact's name from header.")
    if not contact_header:
        return None, None
    
    actual_contact_name = contact_header.text.strip()
    
    contact_header.click()
    time.sleep(1.5) 
    
    # 1. Primary attempt: Try to find the number using the standard selector.
    phone_element = get_element(driver, "contact_info_phone_number", timeout=4, suppress_error=True)

    # 2. Fallback: If the primary attempt fails, try the business account selector.
    if not phone_element:
        print(f"   ...standard number not found for '{actual_contact_name}', checking for business account number.")
        contact_body=get_element(driver,"contact_info_body_container", timeout=10)
        if not contact_body:
            print(f"❌ Could not find contact info body for '{actual_contact_name}' maybe a group chat.")
            return actual_contact_name, None
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", contact_body)
        time.sleep(1)
        phone_element = get_element(driver, "contact_info_phone_number_business", timeout=3, suppress_error=True)

    if phone_element:
        phone_text = phone_element.text.strip()
        # The logic for swapped/unsaved numbers remains the same and is still valid.
        if phone_text.startswith('~'):
            print(f"ℹ️ Swapped Name/Number detected. Normalizing.")
            final_name = phone_text
            final_number = actual_contact_name
        else:
            final_name = actual_contact_name
            final_number = phone_text
    else:
        # This handles groups or contacts with no visible number
        if actual_contact_name.startswith('+'):
            print(f"ℹ️ Unsaved contact detected. Using number as title.")
            final_name = actual_contact_name
            final_number = actual_contact_name
        else:
            print(f"ℹ️ Group or contact without a number detected: '{actual_contact_name}'")
            final_name = actual_contact_name
            final_number = None

    # Close the contact info panel
    body_element = get_element(driver, "body_tag_name")
    if body_element:
        body_element.send_keys(Keys.ESCAPE)
        time.sleep(1)

    final_number = normalize_phone_number(final_number)

    print(f"    ↳ Final Name='{final_name}', Final Number='{final_number or 'None'}'")
    return final_name, final_number


def smart_scroll_and_collect(driver, stop_at_last=None):
    """
    Pass 1: Scrolls up and collects the raw HTML of every message bubble.
    Pass 2: Processes the raw HTML to extract data and trigger downloads.
    """
    chat_container = get_element(driver, "chat_container", timeout=10)
    if not chat_container: return []

    # --- PASS 1: GATHER RAW HTML ---
    print("   --- Pass 1: Scrolling and collecting raw HTML for all messages ---")
    raw_html_snippets = []
    seen_html = set()
    found_stop_point = False
    consecutive_no_new = 0

    while not found_stop_point and consecutive_no_new < 3:
        elements = get_element(driver, "all_messages", find_all=True, suppress_error=True)
        new_found_this_scroll = False
        for element in reversed(elements):
            try:
                html = element.get_attribute('outerHTML')
                if html in seen_html: continue
                
                new_found_this_scroll = True
                seen_html.add(html)
                raw_html_snippets.append(html)
                
                if stop_at_last and stop_at_last in html:
                    print("⏹️ Reached previously stored last message during scroll.")
                    found_stop_point = True
                    raw_html_snippets.pop()
                    break
            except StaleElementReferenceException:
                continue
        
        if found_stop_point: break
        if not new_found_this_scroll:
            consecutive_no_new += 1
        else:
            consecutive_no_new = 0
            
        driver.execute_script("arguments[0].scrollTop = 0;", chat_container)
        time.sleep(2) # Give more time for lazy loading

    # --- PASS 2: PROCESS RAW HTML ---
    print(f"   --- Pass 2: Parsing {len(raw_html_snippets)} collected messages ---")
    final_data = []
    for html_snippet in tqdm(raw_html_snippets[::-1], desc="   Parsing messages"):
        parsed = parse_message_from_html(driver, html_snippet)
        if parsed:
            final_data.append(parsed)
            
    return final_data


# def parse_message(msg):
#     """
#     Parses a message element, fixes the date format, and creates a more
#     reliable unique ID to prevent skipping messages sent in the same minute.
#     """
#     try:
#         msg_class = msg.get_attribute('class')
#         role = 'me' if 'message-out' in msg_class else 'user'
        
#         meta_div = msg.find_element(By.CSS_SELECTOR, SELECTORS["message_meta_data"])
#         meta_text = meta_div.get_attribute("data-pre-plain-text")
        
#         match = re.match(r"\[(.*?), (.*?)\] (.*?):", meta_text)
#         if not match: return None
        
#         time_str, date_str, sender = match.groups()
        
#         content = None
#         try:
#             text_element = msg.find_element(By.CSS_SELECTOR, SELECTORS["message_text_content"])
#             text = text_element.text.strip()
#             if text:
#                 content = text
#         except NoSuchElementException:
#             pass
#         if content is None:
#             try:
#                 body_element = msg.find_element(By.CSS_SELECTOR, "div.copyable-text")
#                 body_text = body_element.text.strip()
#                 if body_text:
#                     if re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)$', body_text):
#                         body_text = re.sub(r'\s*\d{1,2}:\d{2}\s*(?:AM|PM)$', '', body_text).strip()
#                     content = body_text
#             except NoSuchElementException:
#                 pass
#         if content is None:
#             content = "📎 Media (Image/Video/Doc/Sticker)"

#         unique_meta_text = f"{meta_text}{content[:50]}"

#         return {
#             "date": date_str.strip(), # This is 'DD/MM/YYYY'
#             "time": time_str.strip(),
#             "sender": sender.strip(),
#             "content": content.strip(),
#             "meta_text": unique_meta_text, 
#             "role": role
#         }
#     except (NoSuchElementException, StaleElementReferenceException): 
#         return None


# In selenium_handler.py

# ... (All other functions are correct and unchanged) ...

# --- THIS IS THE FINAL, RE-ENGINEERED PARSER WITH HYPER-SPECIFIC XPATHS ---
def parse_message_from_html(driver, html_snippet):
    """
    Parses a static HTML snippet using BeautifulSoup and triggers targeted,
    robust Selenium actions only for downloads. This version uses hyper-specific
    XPaths anchored by meta-text to guarantee the correct element is clicked.
    """
    soup = BeautifulSoup(html_snippet, 'html.parser')
    message_container = soup.find('div', class_=lambda c: c and 'message-' in c)
    if not message_container: return None

    # --- Stage 1: Basic Metadata ---
    sender, time_str, date_str, role, meta_text_raw = "Unknown", "", "", "user", ""
    
    meta_div = soup.find('div', {'data-pre-plain-text': True})
    if meta_div and meta_div.get('data-pre-plain-text'):
        meta_text_raw = meta_div['data-pre-plain-text']
        match = re.match(r"\[(.*?), (.*?)\] (.*?):", meta_text_raw)
        if match:
            time_str, date_str, sender = [s.strip() for s in match.groups()]
    else: # Fallback for elements without meta_text but with sender info
        sender_span = soup.find('span', {'aria-label': True})
        if sender_span: sender = sender_span['aria-label'].replace(":", "").strip()
        time_span = soup.find('span', {'dir': 'auto', 'class': 'x16dsc37'})
        if time_span: time_str = time_span.text.strip()
        date_str = datetime.now().strftime("%d/%m/%Y")
        
    role = 'me' if sender == "You" or config.YOUR_WHATSAPP_NAME in sender else 'user'
    
    content = None
    attachment_filename = None

    # --- Stage 2: Identify and Process by Message Type ---
    
    doc_container = soup.find('div', {'role': 'button', 'title': lambda t: t and t.startswith('Download')})
    if doc_container:
        filename_span = doc_container.find('span', {'dir': 'auto', 'class': 'x13faqbe'})
        if filename_span:
            expected_filename = filename_span.text
            content = f"📎 Document: {expected_filename}"
            try:
                # --- FIX: HYPER-SPECIFIC XPATH FOR DOCUMENTS ---
                # Find the element based on the unique meta_text of its parent bubble.
                element_to_click_xpath = f"//div[@data-pre-plain-text=\"{meta_text_raw}\"]//div[@role='button' and starts-with(@title, 'Download')]"
                element_to_click = driver.find_element(By.XPATH, element_to_click_xpath)
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_to_click)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", element_to_click)
                attachment_filename = _wait_for_download_and_get_filename(expected_filename)
                if attachment_filename: content = f"📎 Document: {attachment_filename}"
            except Exception as e:
                print(f"  - Warning (Doc Download): Could not click element for {expected_filename}. Reason: {e}")

    elif soup.find('button', {'aria-label': 'Play voice message'}):
        content = "🎤 Voice Message"

    elif soup.find('a', href=lambda h: h and 'maps.google.com' in h):
        content = f"📍 Location: {soup.find('a')['href']}"

    elif soup.find('div', {'role': 'button', 'aria-label': 'Open picture'}) or soup.find('span', {'data-icon': 'media-play'}):
        media_type = "🎥 Video" if soup.find('span', {'data-icon': 'media-play'}) else "📷 Image"
        try:
            # --- FIX: HYPER-SPECIFIC XPATH FOR MEDIA ---
            element_to_click_xpath = f"//div[@data-pre-plain-text=\"{meta_text_raw}\"]/ancestor::div[contains(@class, 'message-')][1]//div[@role='button']"
            element_to_click = driver.find_element(By.XPATH, element_to_click_xpath)
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_to_click)
            time.sleep(0.5)
            
            viewer_opened = False
            try:
                driver.execute_script("arguments[0].click();", element_to_click)
                if get_element(driver, "media_viewer_panel", timeout=5):
                    viewer_opened = True
                    filename_element = get_element(driver, "media_viewer_filename", timeout=5)
                    expected_filename = filename_element.text if filename_element else "media_file"
                    download_button = get_element(driver, "media_viewer_download_button", timeout=5)
                    if download_button:
                        driver.execute_script("arguments[0].click();", download_button)
                        attachment_filename = _wait_for_download_and_get_filename(expected_filename)
                    content = f"{media_type} ({attachment_filename or 'download failed'})"
                else: content = f"{media_type} (Viewer did not open)"
            finally:
                if viewer_opened:
                    close_button = get_element(driver, "media_viewer_close_button", timeout=3, suppress_error=True)
                    if close_button: driver.execute_script("arguments[0].click();", close_button)
                    time.sleep(1)
        except Exception as e:
            content = f"{media_type} (Error during download action)"
            print(f"  - Warning (Media Download): {e}")

    else:
        text_span = soup.find('span', class_='selectable-text')
        if text_span: content = text_span.text.strip()
        else: content = "Unsupported or Empty Message"

    # --- Stage 3: Finalize ---
    meta_text_reconstructed = f"[{time_str}, {date_str}] {sender}: "
    unique_meta_text = f"{meta_text_reconstructed}{content[:50]}"

    return {"date": date_str, "time": time_str, "sender": sender, "content": content, "meta_text": unique_meta_text, "role": role, "attachment_filename": attachment_filename}

# Helper for deterministic download waiting
def _wait_for_download_and_get_filename(expected_filename_part, timeout=45):
    print(f"   ...waiting for '{expected_filename_part}' to download...")
    start_time = time.time()
    # Sanitize the expected name to match what the OS saves
    sanitized_name = re.sub(r'[\\/*?:"<>|]', '_', expected_filename_part.split('.')[0])
    
    while time.time() - start_time < timeout:
        for f in os.listdir(config.ATTACHMENTS_DIR):
            if not f.endswith('.crdownload') and sanitized_name in f:
                print(f"   📥 Download complete: {f}")
                return f
        time.sleep(1)
    print(f"   ⚠️ Download timed out for '{expected_filename_part}'.")
    return None
    


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


def send_file_with_caption(driver, file_path, caption=None):
    """
    Attaches a file and sends it with an optional caption.
    This bypasses the OS file dialog for maximum reliability.
    """
    # 1. Sanity check: ensure the file exists before we start
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        print(f"❌ File not found at path: {file_path}")
        return False

    try:
        # 2. Click the attach button
        attach_btn = get_element(driver, "attach_button", timeout=10)
        if not attach_btn:
            print("❌ Could not find the 'Attach' button.")
            return False
        attach_btn.click()
        time.sleep(1)

        # 3. Find the hidden file input and send the absolute file path to it
        # This is the magic step that avoids the OS dialog.
        file_input = get_element(driver, "attach_document_option", timeout=5)
        if not file_input:
            print("❌ Could not find the file input element for documents.")
            return False
        
        print(f"   📎 Attaching file: {file_path}")
        file_input.send_keys(file_path)
        
        # 4. Wait for the file preview screen and type the caption if provided
        caption_box = get_element(driver, "caption_input", timeout=15, context_message="Wait for file preview screen to load.")
        if not caption_box:
            print("❌ Timed out waiting for file preview screen.")
            return False
            
        if caption:
            print(f"   ✍️ Adding caption: '{caption[:30]}...'")
            caption_box.click()
            caption_box.send_keys(caption)
        
        # 5. Find and click the final send button
        send_btn = get_element(driver, "send_file_button", timeout=10)
        if not send_btn:
            print("❌ Could not find the final 'Send' button.")
            return False
        
        send_btn.click()
        print("   ✅ File sent successfully.")
        time.sleep(3) # Wait a moment for the send animation to complete
        return True

    except Exception as e:
        print(f"❌ An error occurred during file sending: {e}")
        return False
    


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



def inspect_element_html(driver, selector_key, find_all=False):
    """
    A powerful debugging tool to find an element by its selector key and print its
    full outer HTML. This helps diagnose broken selectors.
    """
    print("\n" + "─"*20 + f" Inspecting: '{selector_key}' " + "─"*20)
    try:
        elements = get_element(driver, selector_key, timeout=5, find_all=find_all, suppress_error=True)

        if not elements:
            print(f"❌ RESULT: Element with key '{selector_key}' was NOT FOUND.")
            return

        # Ensure elements is always a list for consistent looping
        if not isinstance(elements, list):
            elements = [elements]

        print(f"✅ FOUND {len(elements)} ELEMENT(S). Displaying HTML structure:")
        print("─"*60)

        for i, element in enumerate(elements):
            try:
                outer_html = element.get_attribute('outerHTML')
                print(f"\n--- Element {i+1} ---\n")
                print(outer_html)
                print("\n" + "─"*60)
            except StaleElementReferenceException:
                print(f"\n--- Element {i+1} ---")
                print("Element became stale (disappeared from the page before it could be inspected).")
        
        print(f"✅ Inspection complete for '{selector_key}'.")

    except Exception as e:
        print(f"An unexpected error occurred during inspection: {e}")

def debug_parse_message_structure(msg_element):
    """
    A special parser for debugging. It extracts key attributes and content,
    and reports what it finds or why it fails in a readable dictionary.
    """
    result = {
        'outer_html_snippet': 'N/A',
        'element_class': 'N/A',
        'meta_text': 'NOT FOUND',
        'content_text': 'NOT FOUND',
        'is_image_or_video': False,
        'is_document': False,
        'parse_error': None
    }

    try:
        # Get a snippet of the HTML for identification
        result['outer_html_snippet'] = msg_element.get_attribute('outerHTML')[:250] + "..."
        result['element_class'] = msg_element.get_attribute('class')

        # 1. Try to find the critical meta_text attribute
        try:
            meta_text_element = msg_element.find_element(By.CSS_SELECTOR, SELECTORS["message_meta_data"])
            result['meta_text'] = meta_text_element.get_attribute('data-pre-plain-text')
        except NoSuchElementException:
            # This is the most common failure for non-message elements
            result['parse_error'] = "Could not find the 'data-pre-plain-text' attribute. Likely a system message or date separator."
            return result # Stop here if it's not a real message

        # 2. Try to find the text content
        try:
            content_element = msg_element.find_element(By.CSS_SELECTOR, SELECTORS["message_text_content"])
            result['content_text'] = content_element.text
        except NoSuchElementException:
            result['content_text'] = 'Text element not found.'

        # 3. Check if it's an image/video container
        try:
            msg_element.find_element(By.XPATH, SELECTORS["message_image_or_video_container"])
            result['is_image_or_video'] = True
        except NoSuchElementException:
            pass

        # 4. Check if it's a document container
        try:
            msg_element.find_element(By.XPATH, SELECTORS["message_document_container"])
            result['is_document'] = True
        except NoSuchElementException:
            pass

    except Exception as e:
        result['parse_error'] = f"An unexpected error occurred: {str(e)}"

    return result


def analyze_element_structure(msg_element):
    """
    Performs a detailed analysis of a message element, checking against all
    known selectors and reporting the outcome of each check.
    """
    report = {
        'class': msg_element.get_attribute('class'),
        'checks': {}
    }

    # 1. Meta Text (is it a real message?)
    try:
        meta_div = msg_element.find_element(By.CSS_SELECTOR, SELECTORS["message_meta_div"])
        report['checks']['meta_text'] = f"✓ Found: {meta_div.get_attribute('data-pre-plain-text')}"
    except NoSuchElementException:
        report['checks']['meta_text'] = "✗ Not Found"
        return report # Stop if it's not a message

    # 2. Document
    try:
        doc_container = msg_element.find_element(By.XPATH, SELECTORS["message_document_container"])
        filename = doc_container.find_element(By.XPATH, SELECTORS["document_filename_span"]).text
        report['checks']['document'] = f"✓ Found: {filename}"
    except NoSuchElementException:
        report['checks']['document'] = "✗ Not Found"

    # 3. Voice Note
    try:
        msg_element.find_element(By.XPATH, SELECTORS["message_voicenote_container"])
        report['checks']['voice_note'] = "✓ Found"
    except NoSuchElementException:
        report['checks']['voice_note'] = "✗ Not Found"

    # 4. Video
    try:
        msg_element.find_element(By.XPATH, SELECTORS["message_video_container"])
        report['checks']['video'] = "✓ Found"
    except NoSuchElementException:
        report['checks']['video'] = "✗ Not Found"

    # 5. Image
    try:
        msg_element.find_element(By.XPATH, SELECTORS["message_image_container"])
        report['checks']['image'] = "✓ Found"
    except NoSuchElementException:
        report['checks']['image'] = "✗ Not Found"

    # 6. Location
    try:
        link = msg_element.find_element(By.XPATH, SELECTORS["message_location_link"])
        report['checks']['location'] = f"✓ Found: {link.get_attribute('href')}"
    except NoSuchElementException:
        report['checks']['location'] = "✗ Not Found"
        
    # 7. Text
    try:
        text_span = msg_element.find_element(By.XPATH, SELECTORS["message_text_span"])
        report['checks']['text'] = f"✓ Found: '{text_span.text.strip()}'"
    except NoSuchElementException:
        report['checks']['text'] = "✗ Not Found"
        
    return report