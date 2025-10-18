#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
import re
import platform

# --- Import custom and third-party libraries ---
import database_manager as db

# Auto-install missing libraries
required_libs = [
    "selenium",
    "webdriver-manager",
    "tqdm",
    "google-generativeai" # Gemini API library
]

def install_missing_libs():
    for lib in required_libs:
        try:
            if lib == "google-generativeai":
                __import__("google.generativeai")
            else:
                __import__(lib.replace("-", "_"))
        except ImportError:
            print(f"📦 Installing missing library: {lib} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_missing_libs()

# Now that we've ensured they are installed, we can import them
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
import google.generativeai as genai

# ==============================================================================
# --- CONFIGURATION SECTION ---
# ==============================================================================

# Set your name as it appears in WhatsApp
# This is CRUCIAL for the database to correctly identify your messages as 'me' vs 'user'.
YOUR_WHATSAPP_NAME = "AHBAB SAKALAN"  # <--- IMPORTANT: CHANGE THIS TO YOUR NAME

# --- Gemini API Configuration ---
USE_GEMINI_REPLIES = True  # Set to False to use the old static reply
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_SYSTEM_PROMPT = (
    "You are AHBAB SAKALAN's personal AI assistant, managing his WhatsApp messages. "
    "The messages you receive are from various contacts and they might use Banglish word like typed in english alphabet but actually meaning bengali words. "
    "Your tone should be professional, friendly, and concise. "
    "Your main goal is to acknowledge the user's message and inform them that AHBAB SAKALAN has received it and will get back to them soon. "
    "Do not invent information or make promises. "
    "Analyze the last message from the 'user' to provide a relevant, short acknowledgment. "
    "For example, if the user asks 'Can we meet tomorrow?', a good reply would be 'Hello! AHBAB SAKALAN has received your message about the meeting and will get back to you shortly.' "
    "If it's a simple greeting, a simple acknowledgment is fine. "
    "Keep replies to 1-2 sentences."
    "Try to use some Banglish words where appropriate based on the user's message."
    "Always end with a polite closing."
    "try to understand the context of the message and reply accordingly."
    "if they ask greetings like how are you or any other, reply accordingly."
    "CRITICAL: Your entire output must ONLY be the final message to be sent to the user. Do NOT include your reasoning, analysis, drafts, or any other text."
)

# Safety settings for Gemini
GEMINI_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# ==============================================================================
# --- HELPER & API FUNCTIONS ---
# ==============================================================================

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

def generate_gemini_reply(conversation_history):
    if not GEMINI_API_KEY:
        print("❌ Gemini API Key not found. Falling back to static reply.")
        return "I have received your message and will reply soon."
    try:
        # --- NEW: Trim trailing 'model' messages to satisfy API requirements ---
        while conversation_history and conversation_history[-1]['role'] == 'me':
            conversation_history.pop()
        
        if not conversation_history:
            print("⚠️ Conversation history only contains 'me' messages. Cannot generate reply.")
            return "Thank you for your message. I'll get back to you."

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=GEMINI_SYSTEM_PROMPT, safety_settings=GEMINI_SAFETY_SETTINGS)
        prompt_history = [{'role': 'user' if msg['role'] != 'me' else 'model', 'parts': [{'text': msg['content']}]} for msg in conversation_history]
        
        print(f"🧠 Asking Gemini 2.5 Pro for a reply based on {len(prompt_history)} messages...")
        response = model.generate_content(prompt_history)
        
        if response.parts:
            raw_reply = response.text.strip()
            final_reply = raw_reply.split('\n\n')[-1].strip()
            print(f"🤖 Cleaned Gemini Suggestion: '{final_reply}'")
            return final_reply
        else:
            print("⚠️ Gemini returned no content. This might be due to a safety filter. Falling back to a static reply.")
            if response.prompt_feedback: print(f"   - Prompt Feedback: {response.prompt_feedback}")
            return "Thank you for your message. AHBAB will get back to you shortly."
    except Exception as e:
        print(f"❌ An error occurred with the Gemini API: {e}")
        return "Thank you for your message. I will get back to you shortly."

# ==============================================================================
# --- SELENIUM & SCRAPING FUNCTIONS ---
# ==============================================================================

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
    session_dir = ensure_session_dir()
    options = Options()
    options.add_argument(f"--user-data-dir={os.path.abspath(session_dir)}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://web.whatsapp.com")
    print("📱 Please scan the QR code if not already logged in...")
    login_element = get_element(driver, "login_check", timeout=60, context_message="Wait for main chat page to load.")
    if not login_element:
        print("❌ Login timed out. Exiting.")
        driver.quit()
        sys.exit(1)
    print("✅ Login successful.")
    return driver

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

def open_chat(driver, contact_name, processed_numbers, retries=3):
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
            print(f"⚠️ Attempt {attempt+1}: No results for '{contact_name}'. Retrying...")
            time.sleep(2)
            continue
        for result_index in range(len(chat_results)):
            current_result_list = get_element(driver, "search_result_contact_template", find_all=True, format_args=[contact_name])
            if not current_result_list or len(current_result_list) <= result_index: continue
            current_result_list[result_index].click(); time.sleep(1)
            actual_contact_name, phone_number = get_details_from_header(driver)
            if not phone_number:
                print(f"⚠️ Could not determine a valid phone number for '{actual_contact_name}'. Skipping this search result.")
                continue
            if phone_number in processed_numbers: continue
            return actual_contact_name, phone_number
    return None, None

def get_details_from_header(driver):
    """Helper function to get name and number from the header of an OPEN chat."""
    phone_number, actual_contact_name = "", ""
    contact_header = get_element(driver, "chat_header_name", context_message="Read contact's name from header.")
    if not contact_header: return None, None
    actual_contact_name = contact_header.text
    contact_header.click(); time.sleep(1)
    phone_element = get_element(driver, "contact_info_phone_number", timeout=5, context_message=f"Find phone number for '{actual_contact_name}'.")
    if phone_element:
        phone_number = phone_element.text
    elif re.match(r'^\+[\d\s()-]+$', actual_contact_name.strip()):
        phone_number = actual_contact_name.strip()
    body_element = get_element(driver, "body_tag_name")
    if body_element: body_element.send_keys(Keys.ESCAPE); time.sleep(1)
    return actual_contact_name, phone_number

def scroll_chat(driver):
    chat_container = get_element(driver, "chat_container", timeout=30)
    if not chat_container: return
    last_height, consecutive_no_change = -1, 0
    while consecutive_no_change < 2:
        driver.execute_script("arguments[0].scrollTop = 0;", chat_container)
        time.sleep(3)
        new_height = driver.execute_script("return arguments[0].scrollHeight", chat_container)
        if new_height == last_height:
            try:
                driver.find_element(By.XPATH, SELECTORS["load_older_messages_button"]).click()
                consecutive_no_change = 0; time.sleep(4)
            except (NoSuchElementException, StaleElementReferenceException): consecutive_no_change += 1
        else:
            consecutive_no_change, last_height = 0, new_height


def parse_message(msg):
    try:
        meta_div = msg.find_element(By.CSS_SELECTOR, SELECTORS["message_meta_data"])
        # --- MODIFIED: We capture the raw meta_text ---
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
            
        # --- MODIFIED: We return the meta_text along with other data ---
        return {"date": date_str.strip(), "time": time_str.strip(), "sender": sender.strip(), "content": content.strip(), "meta_text": meta_text}
    except (NoSuchElementException, StaleElementReferenceException): return None

def collect_messages(driver, stop_at_last=None):
    messages = get_element(driver, "all_messages", find_all=True, suppress_error=True)
    data = []
    for msg in reversed(messages):
        parsed = parse_message(msg)
        if parsed:
            # --- MODIFIED: The comparison is now a foolproof string match ---
            if stop_at_last and parsed['meta_text'] == stop_at_last:
                print(f"⏹️ Reached previously stored last message. Stopping collection.")
                break
            data.append(parsed)
    return data[::-1]

def send_reply(driver, reply_text):
    message_box = get_element(driver, "reply_message_box")
    if not message_box:
        print("❌ Could not find message box to send reply.")
        return
    message_box.click()
    message_box.send_keys(reply_text)
    message_box.send_keys(Keys.ENTER)
    print(f"💬 Replied to chat.")
    time.sleep(1)

def close_current_chat(driver):
    """
    Closes the current chat using the explicit Menu -> Close chat action.
    """
    try:
        # Step 1: Find and click the three-dots Menu button in the chat header
        menu_button = get_element(driver, "chat_menu_button", timeout=5, context_message="Find chat menu (three dots).")
        if not menu_button:
            print("⚠️ Could not find chat menu button to close chat.")
            return

        menu_button.click()
        time.sleep(0.5) # Wait for the dropdown to appear

        # Step 2: Find and click the "Close chat" option in the menu
        close_option = get_element(driver, "chat_close_option", wait_condition=EC.element_to_be_clickable, context_message="Find 'Close chat' option in menu.")
        if not close_option:
            print("⚠️ Could not find 'Close chat' option in the menu.")
            # Press escape to close the menu as a fallback
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return
            
        close_option.click()
        print("✅ Chat closed successfully via menu.")
        time.sleep(1) # Allow UI to update

    except Exception as e:
        print(f"❌ An error occurred while trying to close the chat: {e}")

# ==============================================================================
# --- MAIN WORKFLOW FUNCTIONS ---
# ==============================================================================

def monitor_and_reply_to_unread(driver):
    print("\n--- Starting Unread Message Monitor (Press Ctrl+C to stop) ---")
    try:
        while True:
            print("\n L  Checking for unread messages...")
            unread_button = get_element(driver, "unread_filter_button", wait_condition=EC.element_to_be_clickable, timeout=5)
            if not unread_button: print("✔️ No 'Unread' filter button. Waiting..."); time.sleep(15); continue
            
            unread_button.click(); print(" L  'Unread' filter activated."); time.sleep(2)
            
            unread_chats_snapshot = get_element(driver, "chat_list_titles", find_all=True, suppress_error=True, timeout=3)
            if not unread_chats_snapshot:
                print("✔️ No unread chats found. Deactivating filter and waiting...")
                try: get_element(driver, "unread_filter_button", timeout=2).click()
                except: pass
                time.sleep(15); continue
            
            print(f"📩 Found {len(unread_chats_snapshot)} unread chat(s) in this batch. Processing now...")

            for chat_element in unread_chats_snapshot:
                try:
                    contact_name = sanitize_contact_name(chat_element.get_attribute("title"))
                    if not contact_name: continue
                    print(f"\n--- Processing '{contact_name}' ---")
                    chat_element.click(); time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Could not click on chat for '{contact_name}'. Skipping. Error: {e}"); continue
                
                name, number = get_details_from_header(driver)
                if not all([name, number]):
                    print(f"Skipping '{contact_name}' as details could not be retrieved."); continue

                # --- NEW LOGIC TO FETCH ONLY NEW MESSAGES ---
                # 1. Ask the DB for the last message we have for this contact
                last_msg = db.get_last_message_from_db(number, YOUR_WHATSAPP_NAME)
                
                scroll_chat(driver)
                
                # 2. Pass that last message to the collector, which will stop when it sees it
                new_data = collect_messages(driver, stop_at_last=last_msg)
                # --- END OF NEW LOGIC ---
                
                db.save_messages_to_db(name, number, new_data, YOUR_WHATSAPP_NAME)
                
                # Only reply if there are actually new messages
                if USE_GEMINI_REPLIES and new_data:
                    history = list(db.get_recent_messages_for_prompt(number, count=10))
                    reply_text = generate_gemini_reply(history) if history else "Hello! I've received your first message and will get back to you shortly."
                    send_reply(driver, reply_text)
                
                close_current_chat(driver)
            
            print("\n✅ Finished processing batch. Waiting before next check..."); time.sleep(10)

    except KeyboardInterrupt: print("\n🛑 Monitoring stopped.")


def run_full_update(driver):
    print("\n--- Starting Full Database Update ---")
    contacts_to_process = get_all_contacts(driver)
    processed_this_session = set()
    for contact_name in tqdm(contacts_to_process, desc="📂 Processing contacts", unit="contact"):
        name, number = open_chat(driver, contact_name, processed_this_session)
        if not all([name, number]):
            print(f"Skipping '{contact_name}'."); close_current_chat(driver); continue
        
        final_name, final_number = (number, name) if re.match(r'^\+[\d\s-]+$', name) else (name, number)
        processed_this_session.add(final_number)
        
        # We now pass YOUR_WHATSAPP_NAME to this function call as well for consistency
        last_msg = db.get_last_message_from_db(final_number, YOUR_WHATSAPP_NAME)
        
        scroll_chat(driver)
        new_data = collect_messages(driver, stop_at_last=last_msg)
        db.save_messages_to_db(final_name, final_number, new_data, YOUR_WHATSAPP_NAME)
        close_current_chat(driver)
    print("\n🎉 Full update complete!")



def run_api_tools():
    while True:
        print("\n" + "-"*20 + " Database API Tools " + "-"*20)
        print("1. Get conversation summary by title\n2. Get last messages from a conversation\n3. List all unreplied conversations\n4. Back to Main Menu")
        choice = input("Enter your choice: ").strip()
        if choice == '1':
            title = input("Enter contact's title: ")
            print("\n--- Summary ---\n" + db.get_summary_by_title(title))
        elif choice == '2':
            title = input("Enter contact's title: ")
            messages = db.get_last_messages(title, count=5)
            print(f"\n--- Last 5 Messages for '{title}' ---")
            for msg in messages: print(f"[{msg['created_date'][:16]}] {msg['role']}: {msg['content']}")
        elif choice == '3':
            conversations = db.get_all_unreplied_conversations()
            print("\n--- Unreplied Conversations ---")
            for conv in conversations: print(f"  - {conv['title']} ({conv['phone_number']}) | Last updated: {conv['updated'][:16]}")
        elif choice == '4': break
        else: print("❌ Invalid choice.")

# ==============================================================================
# --- MAIN EXECUTION BLOCK ---
# ==============================================================================

if __name__ == "__main__":
    db.init_db()
    if USE_GEMINI_REPLIES and not GEMINI_API_KEY:
        print("\n" + "="*50 + "\n⚠️ WARNING: `USE_GEMINI_REPLIES` is True, but the\n           `GEMINI_API_KEY` environment variable is not set.\n           The bot will fall back to static replies.\n" + "="*50)
    while True:
        print("\n" + "="*40 + "\n       WhatsApp Automation Menu\n" + "="*40)
        print("1. Update Database (Full Scan)\n2. Monitor and Reply to Unread Messages (with AI)\n3. Database API Tools\n4. Exit")
        choice = input("Enter your choice (1/2/3/4): ").strip()
        if choice in ['1', '2']:
            driver = None
            try:
                driver = open_whatsapp()
                if choice == '1': run_full_update(driver)
                else: monitor_and_reply_to_unread(driver)
            except Exception as e:
                print(f"\n❌ An unexpected error occurred: {e}")
                import traceback
                traceback.print_exc()
            finally:
                if driver:
                    print("↪️  Closing the browser...")
                    driver.quit()
        elif choice == '3': run_api_tools()
        elif choice == '4': print("👋 Exiting program."); break
        else: print("❌ Invalid choice.")