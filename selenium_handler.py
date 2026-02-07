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
from tqdm import tqdm
from uuid import uuid4
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException,NoSuchWindowException, WebDriverException,ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from database_manager import normalize_phone_number

import base64
from io import BytesIO
from PIL import Image

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
    Opens WhatsApp Web with high-precision driver detection to fix WinError 193.
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    session_dir = os.path.join(BASE_DIR, "whatsapp_automation_profile")
    attachments_dir = os.path.join(BASE_DIR, "attachments")

    if not os.path.exists(attachments_dir):
        os.makedirs(attachments_dir)

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir={session_dir}")

    # --- Step 4: High-Precision Driver Setup ---
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        print("🌐 Resolving ChromeDriver...")
        # 1. Get path from manager
        raw_path = ChromeDriverManager().install()
        
        # 2. Path Cleanup Logic
        driver_path = raw_path
        if os.path.isdir(driver_path):
            # If it gave us a folder, look for the exe inside
            for root, dirs, files in os.walk(driver_path):
                for file in files:
                    if file == "chromedriver.exe":
                        driver_path = os.path.join(root, file)
                        break

        # 3. Final verification
        if not driver_path.lower().endswith(".exe"):
            driver_path += ".exe"

        print(f"📂 Attempting to launch: {driver_path}")
        
        if not os.path.exists(driver_path):
            raise Exception(f"Driver file does not exist at {driver_path}")
            
        if os.path.getsize(driver_path) < 1000:
            raise Exception(f"Driver file at {driver_path} is corrupted (too small).")

        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        print("📱 Navigating to WhatsApp Web...")
        driver.get("https://web.whatsapp.com")
        
        print("... Please scan the QR code if not already logged in...")
        if not get_element(driver, "login_check", timeout=60):
            print("❌ Login timed out."); driver.quit(); return None
        
        print("✅ Login successful."); return driver

    except Exception as e:
        print(f"\n❌ DRIVER ERROR: {e}")
        print("💡 TIP: Delete your 'C:\\Users\\YourName\\.wdm' folder and try again.")
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
    Scrolls upward, loads all messages, and stops once the last stored message is found.
    Handles duplicate attachment cleanup after collection.
    """
    chat_container = get_element(driver, "chat_container", timeout=10)
    if not chat_container:
        return []

    print("   --- Pass 1: Scrolling and collecting raw HTML for all messages ---")
    final_data = []
    seen_html = set()
    found_stop_point = False
    consecutive_no_new = 0
    index = 0

    while not found_stop_point and consecutive_no_new < 3:
        dismiss_photo_unavailable(driver)  # auto-dismiss popup
        elements = get_element(driver, "all_messages", find_all=True, suppress_error=True)
        new_found_this_scroll = False

        for element in reversed(elements):
            try:
                html = element.get_attribute('outerHTML')
                if not html or html in seen_html:
                    continue

                soup = BeautifulSoup(html, 'html.parser')
                doc_container = soup.find(
                    'div', {'role': 'button', 'title': lambda t: t and t.startswith('Download')}
                )

                # Check for duplicate files before parsing
                if doc_container:
                    full_title = doc_container.get('title')
                    filename = full_title.removeprefix("Download").strip().strip('"').strip("'")
                    existing_files = [f.lower().strip() for f in os.listdir(config.ATTACHMENTS_DIR)]
                    if filename.lower() in existing_files:
                        print(f"⚠️ Skipping duplicate file: {filename}")
                        seen_html.add(html)
                        continue

                parsed = parse_message_from_html(driver, html)
                try:
                    dismiss_photo_unavailable(driver)  # auto-dismiss popup
                except Exception:
                    pass

                if not parsed:
                    seen_html.add(html)
                    continue

                # --- STOP CONDITION ---
                meta_text = parsed.get('meta_text')
                if stop_at_last and meta_text and stop_at_last in meta_text:
                    print("⏹️ Reached previously stored last message during scroll.")
                    found_stop_point = True
                    break

                final_data.append(parsed)
                seen_html.add(html)
                index += 1
                print(f"   ...processing message element {index}")

                new_found_this_scroll = True

            except StaleElementReferenceException:
                continue

        # --- Handle "no new messages" condition ---
        if found_stop_point:
            break

        if not new_found_this_scroll:
            consecutive_no_new += 1
            print(f"   ⚠️ No new messages found ({consecutive_no_new}/3). Trying to load older messages...")
            try:
                load_btn = get_element(driver, "load_older_messages_button", timeout=3, suppress_error=True)
                if load_btn:
                    print("   🔄 Clicking 'Load older messages' button...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", load_btn)
                    time.sleep(2)
                    consecutive_no_new = 0
                    continue
            except Exception as e:
                print(f"   ⚠️ Couldn't click 'Load older messages' button: {e}")
        else:
            consecutive_no_new = 0

        driver.execute_script("arguments[0].scrollTop = 0;", chat_container)
        time.sleep(2)

    # --- Clean up duplicate files in attachments folder ---
    duplicate_pattern = re.compile(r"^(.*)\s\((\d+)\)(\.[^.]+)$")
    files = os.listdir(config.ATTACHMENTS_DIR)
    files.sort()
    for filename in files:
        match = duplicate_pattern.match(filename)
        if match:
            base_name = match.group(1) + match.group(3)
            full_path = os.path.join(config.ATTACHMENTS_DIR, filename)
            original_path = os.path.join(config.ATTACHMENTS_DIR, base_name)
            if os.path.exists(original_path):
                print(f"🗑️ Removing duplicate: {filename}")
                os.remove(full_path)
            else:
                print(f"↪️ Renaming {filename} → {base_name}")
                os.rename(full_path, original_path)

    print("✅ Duplicate cleanup complete.")

    # --- Remove duplicates from final_data by attachment filename ---
    final_data = remove_duplicates_by_filename(final_data)

    # --- Reverse to get oldest-to-newest order ---
    final_data.reverse()
    return final_data


def remove_duplicates_by_filename(final_data):
    seen_files = set()
    cleaned_data = []

    for entry in final_data:
        fname = entry.get("attachment_filename")
        if fname:
            # Normalize filename by removing copy suffixes like (1), (2)
            normalized_fname = re.sub(r'\s*\(\d+\)(?=\.\w+$)', '', fname).lower().strip()
            if normalized_fname in seen_files:
                continue
            seen_files.add(normalized_fname)
        cleaned_data.append(entry)

    return cleaned_data

def dismiss_photo_unavailable(driver):
    try:
        # The popup container
        popup = driver.find_element('xpath', '//div[@aria-label="Photo unavailable Can\'t view this photo because it\'s no longer on your phone."]')
        if popup:
            # Find the OK button inside the popup
            ok_button = popup.find_element('xpath', './/span[text()="OK"]')
            ok_button.click()
            print("🗑️ Dismissed 'Photo unavailable' popup.")
            time.sleep(1)  # small delay for UI update
            return True
    except (NoSuchElementException, ElementClickInterceptedException):
        return False
    return False

def parse_message_from_html(driver, html_snippet):
    """
    Parses a static HTML snippet using a hybrid re-find strategy and now
    gracefully handles special message types like "deleted message".
    """
    soup = BeautifulSoup(html_snippet, 'html.parser')
    message_container = soup.find('div', class_=lambda c: c and 'message-' in c)
    if not message_container: return None

    # --- NEW: Check for special message types FIRST ---
    # Check for "You deleted this message" bubble, which has a unique icon.
    deleted_icon = soup.find('span', {'data-icon': 'recalled'})
    if deleted_icon:
        # We can identify it, but we don't need to save it. Silently skip.
        print("   - Info: Skipping a 'deleted message' bubble.")
        return None

    # --- Stage 1: Basic Metadata ---
    sender, time_str, date_str, role, meta_text_raw = "Unknown", "", "", "user", ""
    
    meta_div = soup.find('div', {'data-pre-plain-text': True})
    has_meta_text = meta_div and meta_div.get('data-pre-plain-text')
    
    if has_meta_text:
        meta_text_raw = meta_div['data-pre-plain-text']
        match = re.match(r"\[(.*?), (.*?)\] (.*?):", meta_text_raw)
        if match:
            time_str, date_str, sender = [s.strip() for s in match.groups()]
    else:
        sender_span = soup.find('span', {'aria-label': True})
        if sender_span: sender = sender_span['aria-label'].replace(":", "").strip()
        time_span = soup.find('span', {'dir': 'auto', 'class': 'x16dsc37'})
        if time_span: time_str = time_span.text.strip()
        date_str = datetime.now().strftime("%d/%m/%Y")
        
    role = 'me' if sender == "You" or (sender and config.YOUR_WHATSAPP_NAME in sender) else 'user'
    if sender == "You": sender = config.YOUR_WHATSAPP_NAME
    
    content = None
    attachment_filename = None

    # --- Stage 2: Identify and Process by Message Type ---
    
    doc_container = soup.find('div', {'role': 'button', 'title': lambda t: t and t.startswith('Download')})
    image_container = soup.find('div', {'role': 'button', 'aria-label': 'Open picture'})
    video_container = soup.select_one("div:has(div span[data-icon='media-play'])")


    if doc_container:
        full_title = doc_container.get('title')
        filename = full_title.removeprefix("Download").strip()
        print(f"   - Found document attachment: {filename}")
        
        
        
        try:    
            element_to_click_xpaths = f"//div[@role='button' and contains(@title, 'Download {filename}')]"
            element_to_click_xpath = driver.find_element(By.XPATH, element_to_click_xpaths)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_to_click_xpath)
            time.sleep(0.5)
            download_start_time = time.time()
            driver.execute_script("arguments[0].click();", element_to_click_xpath)
            attachment_filename = _wait_for_newest_file(config.ATTACHMENTS_DIR, download_start_time)
            if attachment_filename: 
                content = f"📎 Document: {attachment_filename}"
            else:
                content = f"📎 Document: download failed"
        except Exception as e:
            print(f"  - Warning (Doc Download): Could not click element for {attachment_filename}. Reason: {e}")

        # if attachment_filename:
        #     expected_filename = attachment_filename
        #     content = f"📎 Document: {expected_filename}"
        #     try:
        #         # Use a precise XPath to re-find the element to click
        #         if has_meta_text:
        #             element_to_click_xpath = f"//div[@data-pre-plain-text=\"{meta_text_raw}\"]//span[text()=\"{expected_filename}\"]/ancestor::div[@role='button'][1]"
        #         else: # Fallback for attachments without meta-text
        #             element_to_click_xpath = f"//span[text()='{time_str}']/ancestor::div[contains(@class, 'message-')][1]//div[@role='button' and contains(@title, 'Download')]"
                
        #         element_to_click = driver.find_element(By.XPATH, element_to_click_xpath)
        #         driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_to_click)
        #         time.sleep(0.5)
        #         driver.execute_script("arguments[0].click();", element_to_click)
        #         attachment_filename = _wait_for_download_and_get_filename(expected_filename)
        #         if attachment_filename: content = f"📎 Document: {attachment_filename}"
        #     except Exception as e:
        #         print(f"  - Warning (Doc Download): Could not click element for {expected_filename}. Reason: {e}")

    elif soup.find('button', {'aria-label': 'Play voice message'}):
        content = "🎤 Voice Message"

    elif soup.find('a', href=lambda h: h and 'maps.google.com' in h):
        content = f"📍 Location: {soup.find('a')['href']}"

    elif image_container:
        media_type = "📷 Image"
        try:
            # if has_meta_text:
            #     element_to_click_xpath = f"//div[@data-pre-plain-text=\"{meta_text_raw}\"]/ancestor::div[contains(@class, 'message-')][1]//div[@role='button']"
            # else:
            #     element_to_click_xpath = f"//span[text()='{time_str}']/ancestor::div[contains(@class, 'message-')][1]//div[@role='button']"
            element_to_click_xpath_image = f"//div[@role='button' and (@aria-label='Open picture' or @aria-label='Play video')]"
            element_to_click = driver.find_element(By.XPATH, element_to_click_xpath_image)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_to_click)
            time.sleep(0.5)
            
            viewer_opened = False
            try:
                driver.execute_script("arguments[0].click();", element_to_click)
                viewer_opened = True
                download_button = get_element(driver, "media_viewer_download_button", timeout=5)
                if download_button:
                    download_start_time = time.time()
                    driver.execute_script("arguments[0].click();", download_button)
                    attachment_filename = _wait_for_newest_file(config.ATTACHMENTS_DIR, download_start_time)
                content = f"{media_type} ({attachment_filename or 'download failed'})"
            finally:
                if viewer_opened:
                    close_button = get_element(driver, "media_viewer_close_button", timeout=3, suppress_error=True)
                    if close_button: driver.execute_script("arguments[0].click();", close_button)
                    time.sleep(1)
        except Exception as e:
            content = f"{media_type} (Error during download action)"
            print(f"  - Warning (Media Download): {e}")
    elif video_container:
        media_type="🎥 Video"
        element_to_click_xpath_video = f"//div[div/span[@data-icon='media-play']]"
        element_to_click = driver.find_element(By.XPATH, element_to_click_xpath_video)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_to_click)
        time.sleep(0.5)
        
        viewer_opened = False
        try:
            driver.execute_script("arguments[0].click();", element_to_click)
            viewer_opened = True
            download_button = get_element(driver, "media_viewer_download_button", timeout=5)
            if download_button:
                download_start_time = time.time()
                driver.execute_script("arguments[0].click();", download_button)
                attachment_filename = _wait_for_newest_file(config.ATTACHMENTS_DIR, download_start_time)
            content = f"{media_type} ({attachment_filename or 'download failed'})"
        finally:
            if viewer_opened:
                close_button = get_element(driver, "media_viewer_close_button", timeout=3, suppress_error=True)
                if close_button: driver.execute_script("arguments[0].click();", close_button)
                time.sleep(1)
    else:
        text_span = soup.find('span', class_='selectable-text')
        if text_span:
            content = text_span.text.strip()
        else:
            content = "Unsupported or Empty Message"

    # --- Stage 3: Finalize ---
    meta_text_reconstructed = f"[{time_str}, {date_str}] {sender}: "
    unique_meta_text = f"{meta_text_reconstructed}{content}"

    try:
        dismiss_photo_unavailable(driver)  # auto-dismiss popup
    except Exception:
        pass

    return {"date": date_str, "time": time_str, "sender": sender, "content": content, "meta_text": unique_meta_text, "role": role, "attachment_filename": attachment_filename}


def _wait_for_newest_file(download_dir, download_start_time, timeout=45):
    """
    Waits for a download to complete and returns the filename of the newest file
    in the directory created after a specific start time.
    """
    print("   ...waiting for a new file to finish downloading...")
    time.sleep(1) # A brief initial pause
    
    # --- Part 1: Wait for the download to actually finish ---
    wait_start_time = time.time()
    while time.time() - wait_start_time < timeout:
        # Check if any .crdownload (Chrome) or .tmp (Firefox) files exist
        temp_files = [f for f in os.listdir(download_dir) if f.endswith(('.crdownload', '.tmp'))]
        if not temp_files:
            print("   -> No temporary download files found. Proceeding to find the newest file.")
            break # Exit the loop if no downloads are in progress
        time.sleep(1) # Wait a second before checking again
    else: # This 'else' belongs to the 'while' loop
        print("   -> ⚠️ Timeout: Download in progress file (.crdownload) still present after timeout.")
        return None

    # --- Part 2: Find the most recent file created after the download was initiated ---
    try:
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
        
        # Filter files created *after* the download button was clicked
        new_files = [f for f in files if os.path.getmtime(f) > download_start_time]

        if not new_files:
            print("   -> ⚠️ Error: Could not find any new file created after the download started.")
            return None
            
        # Get the absolute newest file from the list of new files
        newest_file_path = max(new_files, key=os.path.getmtime)
        newest_filename = os.path.basename(newest_file_path)
        
        print(f"   -> 📥 Download identified: {newest_filename}")
        return newest_filename
    except Exception as e:
        print(f"   -> ⚠️ Error while finding the newest file: {e}")
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


#-------------------- DEBUGGING TOOLS --------------------#

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



#---------------------

def find_element_if_exists(parent_element: WebElement, by: By, value: str):
    """
    Safely finds a child element within a parent WebElement.
    Returns the element if found, otherwise returns None.
    """
    try:
        return parent_element.find_element(by, value)
    except NoSuchElementException:
        return None
    

def _handle_document_download(driver, doc_container: WebElement, downloaded_files_set: set):
    """
    Workflow for downloading a document. It checks against the provided set of 
    downloaded files before initiating a click to prevent duplicates.
    
    Args:
        driver: The Selenium WebDriver instance.
        doc_container: The specific WebElement for the document's clickable area.
        downloaded_files_set: A set of filenames already logged in the database.
        
    Returns:
        A tuple of (content_string, attachment_filename).
    """
    try:
        full_title = doc_container.get_attribute('title')
        if not full_title:
            return "📎 Document (Title not found)", None
            
        expected_filename = full_title.removeprefix("Download").strip()

        # --- CHECK IF ALREADY DOWNLOADED ---
        if expected_filename in downloaded_files_set:
            print(f"   -> Skipping download: Document '{expected_filename}' already in DB.")
            return f"📎 Document: {expected_filename}", expected_filename

        # --- PROCEED WITH DOWNLOAD ---
        print(f"   - Found new document: '{expected_filename}'. Initiating download...")
        
        # Record time just before the click
        download_start_time = time.time()
        driver.execute_script("arguments[0].click();", doc_container)
        
        # Wait for the file to appear in the downloads folder
        actual_filename = _wait_for_newest_file(config.ATTACHMENTS_DIR, download_start_time)
        
        if actual_filename:
            # Add to the set for the current session to avoid re-downloading if encountered again
            downloaded_files_set.add(actual_filename)
            return f"📎 Document: {actual_filename}", actual_filename
        else:
            return "📎 Document: download failed", None
        
    except Exception as e:
        print(f"  - Error (Doc Download): An exception occurred. Reason: {e}")
        return "📎 Document (Error during download action)", None
    

def _handle_media_viewer_download(driver, media_container: WebElement, media_type: str, downloaded_files_set: set):
    """
    Robust workflow for downloading images/videos via the media viewer.
    It opens the viewer, attempts to find a specific filename to check against the DB,
    downloads the file, and reliably closes the viewer.
    """
    # Define selectors for elements inside the media viewer for clarity
    viewer_panel_selector = (By.CSS_SELECTOR, "div[data-testid='media-viewer']")
    download_button_selector = (By.CSS_SELECTOR, "span[data-icon='download']")
    close_button_selector = (By.CSS_SELECTOR, "span[data-icon='x-viewer']")
    filename_selector = (By.CSS_SELECTOR, "div[data-testid='media-info-title-text']")
    
    wait = WebDriverWait(driver, 15) # Wait up to 15 seconds for elements to appear
    viewer_was_opened = False

    try:
        # 1. Open the media viewer
        driver.execute_script("arguments[0].click();", media_container)
        viewer_panel = wait.until(EC.visibility_of_element_located(viewer_panel_selector))
        viewer_was_opened = True
        print(f"   - {media_type} viewer opened.")

        # 2. Try to find a specific filename in the viewer
        expected_filename = None
        try:
            # Use a shorter timeout here as the filename is not always present
            filename_element = WebDriverWait(driver, 3).until(EC.visibility_of_element_located(filename_selector))
            expected_filename = filename_element.text
            
            # --- CHECK IF ALREADY DOWNLOADED (if we found a name) ---
            if expected_filename and expected_filename in downloaded_files_set:
                print(f"   -> Skipping download: Media '{expected_filename}' already in DB.")
                return f"{media_type} ({expected_filename})", expected_filename
        except Exception:
            # This is common for images that are just pasted into chat
            print("   - Info: No specific filename found in media viewer. Proceeding with download.")

        # 3. Download the file
        download_button = wait.until(EC.element_to_be_clickable(download_button_selector))
        download_start_time = time.time()
        driver.execute_script("arguments[0].click();", download_button)
        
        actual_filename = _wait_for_newest_file(config.ATTACHMENTS_DIR, download_start_time)
        
        if actual_filename:
            downloaded_files_set.add(actual_filename) # Add to session set
        
        return f"{media_type} ({actual_filename or 'download failed'})", actual_filename

    except Exception as e:
        print(f"  - Error (Media Download): An exception occurred during viewer interaction. Reason: {e}")
        return f"{media_type} (Error during download action)", None
        
    finally:
        # 4. ALWAYS attempt to close the media viewer to prevent the script from getting stuck
        if viewer_was_opened:
            try:
                close_button = wait.until(EC.element_to_be_clickable(close_button_selector))
                driver.execute_script("arguments[0].click();", close_button)
                # Confirm it has closed before proceeding
                wait.until(EC.invisibility_of_element_located(viewer_panel_selector))
                print("   - Media viewer closed successfully.")
            except Exception:
                print("  - WARNING: Could not auto-close media viewer. The script might be stuck. A page refresh might be needed if errors persist.")


# (Keep your helper functions: get_element, _wait_for_newest_file, etc.)

# In whatsappSynchronizer.py (or wherever this function lives)

def collect_message_identifiers(driver, stop_at_last_meta_text=None):
    """
    PASS 1: Scrolls to the top of the chat, collecting unique message identifiers
    until it either reaches the top or finds the 'stop_at_last_meta_text'.
    """
    print("   --- Pass 1: Scrolling to collect all message identifiers ---")
    chat_container = get_element(driver, "chat_container", timeout=10)
    if not chat_container: return []
    
    all_meta_texts = set()
    stop_point_reached = False
    consecutive_no_new_scrolls = 0

    while not stop_point_reached and consecutive_no_new_scrolls < 4: # Increased patience
        # Find all divs that contain a message's unique identifier
        meta_elements = driver.find_elements(By.XPATH, "//div[@data-pre-plain-text]")
        
        if not meta_elements:
            consecutive_no_new_scrolls += 1
            time.sleep(1)
            continue

        new_identifiers_found_this_scroll = False
        # Process from bottom-up of the current view
        for element in reversed(meta_elements):
            try:
                meta_text = element.get_attribute('data-pre-plain-text')
                
                # --- CORRECTED LOGIC ---
                # Check for the stop point first. If we find it, we stop the entire process.
                if stop_at_last_meta_text and stop_at_last_meta_text == meta_text:
                    print("⏹️ Reached previously stored last message. Stopping collection.")
                    stop_point_reached = True
                    break # Break the inner for-loop

                # If it's not the stop point, check if it's new and add it.
                if meta_text not in all_meta_texts:
                    new_identifiers_found_this_scroll = True
                    all_meta_texts.add(meta_text)

            except StaleElementReferenceException:
                continue
        
        # If the inner loop was broken by finding the stop point, break the outer loop too.
        if stop_point_reached:
            break

        # If we didn't find any new identifiers on this screen, increment counter.
        if not new_identifiers_found_this_scroll:
            consecutive_no_new_scrolls += 1
            print(f"   - No new messages on this scroll ({consecutive_no_new_scrolls}/4).")
        else:
            consecutive_no_new_scrolls = 0 # Reset if we find new messages
            
        # Scroll to the top to load older messages
        driver.execute_script("arguments[0].scrollTop = 0;", chat_container)
        time.sleep(2.5) # Wait for older messages to lazy-load

    # Sort the collected identifiers to ensure they are processed chronologically
    sorted_identifiers = sorted(list(all_meta_texts))
    print(f"   -> Collected {len(sorted_identifiers)} new message identifiers.")
    return sorted_identifiers


def process_messages_by_identifier(driver, identifiers, downloaded_files_set):
    """
    PASS 2: Iterates through a list of unique message identifiers, finds each live
    element, and passes it to the processing function for interaction and downloading.
    """
    print(f"\n   --- Pass 2: Processing {len(identifiers)} messages for content and downloads ---")
    final_data = []
    if not identifiers: return []

    for meta_text in tqdm(identifiers, desc="   Parsing messages", unit="msg"):
        try:
            # This XPath is precise: it finds the exact message we want to process
            xpath = f"//div[@data-pre-plain-text=\"{meta_text}\"]/ancestor::div[contains(@class, 'message-')][1]"
            message_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            # Scroll the specific element into view just before processing
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", message_element)
            time.sleep(0.5)

            # Pass the LIVE WebElement and the set of downloaded files to the processor
            parsed_data = process_live_message_element(driver, message_element, downloaded_files_set)
            
            if parsed_data:
                final_data.append(parsed_data)
        except Exception as e:
            print(f"\n  - Error processing message with meta '{meta_text[:30]}...': {e}")
            continue
            
    return final_data


def process_live_message_element(driver, message_element: WebElement, downloaded_files_set: set):
    """
    Parses a LIVE Selenium WebElement. All find operations are scoped within this element,
    making them stable and accurate.
    """
    # ... (Keep your metadata extraction from the old function, but get HTML from the live element)
    html_snippet = message_element.get_attribute('innerHTML')
    soup = BeautifulSoup(html_snippet, 'html.parser')
    
    meta_div = soup.find('div', {'data-pre-plain-text': True})
    if not meta_div: return None
    
    meta_text_raw = meta_div['data-pre-plain-text']
    match = re.match(r"\[(.*?), (.*?)\] (.*?):", meta_text_raw)
    if not match: return None
    
    time_str, date_str, sender = [s.strip() for s in match.groups()]
    role = 'me' if sender == "You" or (sender and config.YOUR_WHATSAPP_NAME in sender) else 'user'
    if sender == "You": sender = config.YOUR_WHATSAPP_NAME

    content, attachment_filename = None, None

    # --- THIS IS THE KEY CHANGE ---
    # Find elements WITHIN the message_element, not the global driver
    doc_container = find_element_if_exists(message_element, By.CSS_SELECTOR, "div[role='button'][title^='Download']")
    image_container = find_element_if_exists(message_element, By.CSS_SELECTOR, "div[role='button'][aria-label='Open picture']")
    video_container = find_element_if_exists(message_element, By.CSS_SELECTOR, "span[data-icon='media-play']")

    if doc_container:
        content, attachment_filename = _handle_document_download(driver, doc_container, downloaded_files_set)

    elif image_container or video_container:
        media_type = "🎥 Video" if video_container else "📷 Image"
        element_to_click = video_container.find_element(By.XPATH, "./ancestor::div[@role='button'][1]") if video_container else image_container
        content, attachment_filename = _handle_media_viewer_download(driver, element_to_click, media_type, downloaded_files_set)

    # ... (your other elifs for voice, location etc.) ...

    else:
        text_span = soup.find('span', class_='selectable-text')
        content = text_span.text.strip() if text_span else None

    if not content: return None

    unique_meta_text = f"[{time_str}, {date_str}] {sender}: {content}"
    return {"date": date_str, "time": time_str, "sender": sender, "content": content, "meta_text": unique_meta_text, "role": role, "attachment_filename": attachment_filename}

# You will also need find_element_if_exists, _handle_document_download, 
# and _handle_media_viewer_download from the previous answers.




# Add these imports at the top
import base64
from io import BytesIO
from PIL import Image

def open_whatsapp(headless=True):
    # Try to restore session from cloud first
    from storage_manager import download_session
    download_session()

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080") # Critical for QR screenshots
    options.add_argument(f"--user-data-dir={os.path.abspath('whatsapp_automation_profile')}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://web.whatsapp.com")
    return driver

def get_qr_base64(driver):
    """Captures the QR code element and returns it as Base64 string."""
    try:
        # Wait for QR code canvas to appear
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
        qr_element = driver.find_element(By.TAG_NAME, "canvas")
        
        # Take a screenshot of the whole page, then crop to the QR
        location = qr_element.location
        size = qr_element.size
        png = driver.get_screenshot_as_png()
        
        img = Image.open(BytesIO(png))
        left = location['x']
        top = location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']
        
        img = img.crop((left, top, right, bottom))
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except:
        return None