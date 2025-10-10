#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
import re

# Auto-install missing libraries
required_libs = [
    "selenium",
    "webdriver-manager",
    "tqdm"
]

def install_missing_libs():
    for lib in required_libs:
        try:
            __import__(lib.replace("-", "_"))
        except ImportError:
            print(f"📦 Installing missing library: {lib} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_missing_libs()

from tqdm import tqdm
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def open_whatsapp():
    """Open WhatsApp Web with persistent session."""
    session_dir = ensure_session_dir()

    options = Options()
    options.add_argument(f"--user-data-dir={os.path.abspath(session_dir)}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://web.whatsapp.com")

    print("📱 Please scan the QR code if not already logged in...")

    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        print("✅ Login successful.")
    except TimeoutException:
        print("❌ Login timed out. Please run the script again.")
        driver.quit()
        sys.exit(1)

    return driver


def ensure_session_dir():
    """Make sure session/profile directory exists."""
    session_dir = "whatsapp_automation_profile"
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        print("📂 Created session directory for WhatsApp Web.")
    return session_dir


def get_all_contacts(driver):
    chat_list_selector = (By.ID, "pane-side")
    chat_list = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(chat_list_selector)
    )
    contacts_set = set()
    last_height, consecutive_no_change = -1, 0

    while consecutive_no_change < 3:
        try:
            chat_title_elements = driver.find_elements(
                By.XPATH, "//div[@id='pane-side']//div[@role='gridcell']//span[@title]"
            )
            for el in chat_title_elements:
                try:
                    name = sanitize_contact_name(el.get_attribute("title"))
                    if name:
                        contacts_set.add(name.strip())
                except StaleElementReferenceException:
                    continue
        except Exception as e:
            print(f"⚠️ Error while fetching contacts: {e}")

        driver.execute_script("arguments[0].scrollTop += 300;", chat_list)
        time.sleep(1)
        new_height = driver.execute_script("return arguments[0].scrollTop", chat_list)
        max_height = driver.execute_script("return arguments[0].scrollHeight", chat_list)

        if new_height == last_height:
            consecutive_no_change += 1
        else:
            consecutive_no_change = 0
            last_height = new_height

        if new_height >= max_height:
            break

    return list(contacts_set)


def sanitize_contact_name(name):
    return re.sub(r'[^\u0000-\uFFFF]', '', name)


def open_chat(driver, contact_name, processed_numbers, retries=3):
    """
    Searches for a contact, handles multiple results, and fetches the phone number.
    Returns (name, "") for saved contacts where the number can't be found.
    """
    for attempt in range(retries):
        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
            )
            search_box.click()
            time.sleep(0.5)
            search_box.send_keys(Keys.COMMAND + "a")
            search_box.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            search_box.send_keys(contact_name)
            time.sleep(2)

            search_results_xpath = f"//div[@id='pane-side']//span[@title='{contact_name}']"
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, search_results_xpath))
            )
            chat_results = driver.find_elements(By.XPATH, search_results_xpath)
            print(chat_results)

            for result_index in range(len(chat_results)):
                current_result = driver.find_elements(By.XPATH, search_results_xpath)[result_index]
                current_result.click()
                time.sleep(1)

                phone_number = ""
                actual_contact_name = ""
                
                try:
                    contact_header_selector = "div#main header div[role='button'][tabindex='0'] span[dir='auto']"
                    contact_header = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, contact_header_selector))
                    )
                    actual_contact_name = contact_header.text

                    contact_header.click()
                    time.sleep(1)
                    phone_number_selector = "header:has(div[title='Contact info']) + div span.selectable-text.copyable-text[dir='auto'] div"
                    phone_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, phone_number_selector))
                    )
                    phone_number = phone_element.text
                    
                except (TimeoutException, NoSuchElementException):
                    print(f"⚠️ Could not find a phone number for '{actual_contact_name}'. Proceeding without it.")
                    phone_number = ""
                
                finally:
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except: pass
                
                # --- DUPLICATE CHECKING LOGIC ---
                unique_id = phone_number if phone_number else actual_contact_name
                if unique_id in processed_numbers:
                    print(f"⏭️ Skipping '{actual_contact_name}' as it's already processed.")
                    continue
                else:
                    print(f"✅ Found new contact '{actual_contact_name}'.")
                    return actual_contact_name, phone_number

            return None, None

        except TimeoutException:
            print(f"⚠️ Attempt {attempt+1}: No results found for '{contact_name}'. Retrying...")
            time.sleep(2)

    print(f"❌ Could not open a new chat for '{contact_name}' after {retries} attempts. Skipping...")
    return None, None


def scroll_chat(driver):
    chat_pane_selector = (By.CSS_SELECTOR, "div#main div.copyable-area div[tabindex='0']")
    try:
        chat_container = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(chat_pane_selector)
        )
    except TimeoutException:
        print("❌ Could not find the chat message container.")
        return

    last_height = -1
    consecutive_no_change = 0
    while consecutive_no_change < 2:
        driver.execute_script("arguments[0].scrollTop = 0;", chat_container)
        time.sleep(3)
        new_height = driver.execute_script("return arguments[0].scrollHeight", chat_container)

        if new_height == last_height:
            button_was_clicked = False
            try:
                load_more_button_xpath = "//button[.//div[contains(text(), 'Click here to get older messages')]]"
                button = driver.find_element(By.XPATH, load_more_button_xpath)
                print("\n🖱️ 'Load older messages' button found. Clicking it...")
                button.click()
                button_was_clicked = True
                time.sleep(4)
            except (NoSuchElementException, StaleElementReferenceException):
                pass
            if button_was_clicked:
                consecutive_no_change = 0
            else:
                consecutive_no_change += 1
        else:
            consecutive_no_change = 0
            last_height = new_height


def collect_messages(driver, stop_at_last=None):
    messages = driver.find_elements(By.CSS_SELECTOR, "div.message-in, div.message-out")
    data = []
    for msg in reversed(messages):
        parsed = parse_message(msg)
        if parsed:
            if stop_at_last and parsed == stop_at_last:
                print("⏹️ Reached previously stored last message. Stopping collection.")
                break
            data.append(parsed)
    return data[::-1]


def parse_message(msg):
    try:
        meta_div = msg.find_element(By.CSS_SELECTOR, "div[data-pre-plain-text]")
        meta_text = meta_div.get_attribute("data-pre-plain-text")
        match = re.match(r"\[(.*?), (.*?)\] (.*?):", meta_text)
        if not match: return None
        time_str, date_str, sender = match.groups()
        msg_type, content = "text", ""
        try: msg.find_element(By.XPATH, ".//div[@role='button' and @aria-label='Open picture']"); msg_type, content = "image", "📎 Image"
        except NoSuchElementException: pass
        try: msg.find_element(By.XPATH, ".//button[@aria-label='Play voice message']"); msg_type, content = "voice", "📎 Voice Message"
        except NoSuchElementException: pass
        try: msg.find_element(By.XPATH, ".//div[starts-with(@title, 'Download ')]"); msg_type, content = "document", "📎 Document"
        except NoSuchElementException: pass
        try: msg.find_element(By.XPATH, ".//div[@aria-label='Video' or @aria-label='GIF']"); msg_type, content = "video", "📎 Video/GIF"
        except NoSuchElementException: pass
        try:
            if msg.find_element(By.XPATH, ".//img[contains(@style, 'width') and contains(@style, 'height')]"): msg_type, content = "sticker", "📎 Sticker"
        except NoSuchElementException: pass
        try:
            text_element = msg.find_element(By.CSS_SELECTOR, "span.selectable-text")
            text = text_element.text.strip()
            if text: content = text if msg_type == "text" else f"{content} {text}"
        except NoSuchElementException: pass
        if not content:
            try: msg.find_element(By.XPATH, ".//span[contains(text(), 'Forwarded')]"); msg_type, content = "forwarded", "📎 Forwarded Content"
            except NoSuchElementException: msg_type, content = "unknown", ""
        return {"date": date_str.strip(), "time": time_str.strip(), "sender": sender.strip(), "type": msg_type, "content": content.strip()}
    except (NoSuchElementException, StaleElementReferenceException): return None


def save_chat_to_json(contact_name, phone_number, new_messages, output_file="whatsapp_chats.json"):
    """
    Saves new messages to a JSON file which is a list of contact objects.
    Finds contacts by phone number to update them, or adds a new contact object if not found.
    """
    all_chats_list = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                all_chats_list = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: Could not decode existing JSON file. Starting with a new list.")

    if not new_messages:
        print(f"✔️ No new messages to save for '{contact_name}'")
        return

    # Find the existing contact in the list, if it exists
    existing_contact_obj = None
    for contact in all_chats_list:
        if contact.get("contact_number") == phone_number:
            existing_contact_obj = contact
            break
    
    if existing_contact_obj:
        # Contact exists, append new messages
        existing_contact_obj["conversations"].extend(new_messages)
        # Update name in case it has changed
        existing_contact_obj["contact_name"] = contact_name
        print(f"💾 Appended {len(new_messages)} new messages for '{contact_name}' ({phone_number})")
    else:
        # New contact, create a new object and add it to the list
        new_contact = {
            "contact_name": contact_name,
            "contact_number": phone_number,
            "conversations": new_messages
        }
        all_chats_list.append(new_contact)
        print(f"💾 Saved {len(new_messages)} messages for new contact '{contact_name}' ({phone_number})")

    # Save the entire updated list back to the file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chats_list, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    driver = open_whatsapp()

    output_filename = "whatsapp_chats.json"
    processed_identifiers = set() # Will store numbers or names
    chats_by_number = {}

    if os.path.exists(output_filename):
        with open(output_filename, "r", encoding="utf-8") as f:
            try:
                all_chats_data_list = json.load(f)
                for contact in all_chats_data_list:
                    # Use number as the primary identifier, fall back to name
                    number = contact.get("contact_number")
                    name = contact.get("contact_name")
                    if number:
                        processed_identifiers.add(number)
                        chats_by_number[number] = contact
                    elif name: # For older entries or those without numbers
                        processed_identifiers.add(name)

                print(f"🔍 Found {len(processed_identifiers)} contacts in existing JSON file.")
            except json.JSONDecodeError:
                print("⚠️ Could not parse existing JSON file. A new one will be created.")

    contacts_to_process =get_all_contacts(driver)

    for contact_name_from_list in tqdm(contacts_to_process, desc="📂 Processing contacts", unit="contact"):
        name, number = open_chat(driver, contact_name_from_list, processed_identifiers)
        if name is None:
            continue
        
        final_contact_name = name
        # This regex checks if the scraped name looks like a phone number
        if re.match(r'^\+[\d\s-]+$', name):
             final_contact_name = number
             number = name
             print(f"ℹ️ Detected unsaved contact. Using '{number}' as the name.")
        
        # Add the unique ID to the processed set for this session
        unique_id = number if number else name
        processed_identifiers.add(unique_id)

        stored_last_message = None
        # Only check for last message if we have a valid number and an existing entry
        if number and number in chats_by_number and chats_by_number[number].get("conversations"):
            stored_last_message = chats_by_number[number]["conversations"][-1]

        scroll_chat(driver)
        new_data = collect_messages(driver, stop_at_last=stored_last_message)
        
        save_chat_to_json(final_contact_name, number, new_data, output_file=output_filename)

    print("\n🎉 All contacts processed!")
    driver.quit()