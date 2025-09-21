import os
import time
import json
import re
import sys
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
CHATS_TO_PROCESS = 5
OUTPUT_JSON_FILE = "whatsapp_archive.json"

class WhatsAppJsonArchiver:
    def __init__(self):
        self.driver = self._setup_driver()
        # Increased timeout for robustness on slower connections or machines
        self.wait = WebDriverWait(self.driver, 30)
        self.archive_data = {}

    def _setup_driver(self):
        profile_path = os.path.join(os.getcwd(), "whatsapp_automation_profile")
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--disable-dev-shm-usage")
        print(f"Using profile directory: {profile_path}")
        return webdriver.Chrome(service=service, options=options)

    def _sanitize_string(self, text):
        return re.sub(r'[\u200e\u200f\u202a-\u202e]', '', text).strip()

    def login_and_wait(self):
        self.driver.get("https://web.whatsapp.com/")
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "side")))
            print("WhatsApp Web page loaded successfully.")
            time.sleep(5)
            return True
        except TimeoutException:
            print("Failed to load WhatsApp Web. Please make sure you are logged in.")
            return False

    def _get_top_chat_elements(self, limit):
        print(f"Attempting to get the first {limit} chat elements...")
        try:
            chat_name_selector = "//div[@id='pane-side']//div[@role='gridcell']//span[@title]"
            chat_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, chat_name_selector))
            )
            print(f"Found {len(chat_elements)} total visible chats. Processing the first {limit}.")
            return chat_elements[:limit]
        except TimeoutException:
            print("Could not find chat list.")
            return []

    # ==============================================================================
    # ====== THIS IS THE DEFINITIVE, FINAL, AND CORRECT archive_chat FUNCTION ======
    # ==============================================================================
    def archive_chat(self, chat_title_element):
        contact_name = ""
        try:
            contact_name = self._sanitize_string(chat_title_element.get_attribute("title"))
            print(f"\n--- Processing Chat: {contact_name} ---")

            # Use a robust JavaScript click on the chat's container.
            chat_container = chat_title_element.find_element(By.XPATH, "./ancestor::div[@role='listitem']")
            self.driver.execute_script("arguments[0].click();", chat_container)

            # --- THE SINGLE, BULLETPROOF SYNCHRONIZATION STEP ---
            # We wait for the message input box. Its presence guarantees that the entire
            # chat pane, including #main and the scrollable area, has been created.
            print("  Waiting for chat to become fully interactive...")
            message_box_selector = "//div[@data-testid='conversation-compose-box']//div[@role='textbox']"
            self.wait.until(EC.presence_of_element_located((By.XPATH, message_box_selector)))
            print("  Chat is fully loaded.")
            # --- END OF SYNCHRONIZATION ---

            panel_selector = "//div[@id='main']//div[@tabindex='-1']"
            conv_panel = self.driver.find_element(By.XPATH, panel_selector)
            
            print("  Scrolling up to load message history...")
            last_height = -1
            while True:
                try:
                    conv_panel = self.driver.find_element(By.XPATH, panel_selector)
                    new_height = self.driver.execute_script("return arguments[0].scrollHeight", conv_panel)
                    if new_height == last_height:
                        print("  Reached the beginning of the chat history.")
                        break
                    last_height = new_height
                    self.driver.execute_script("arguments[0].scrollTop = 0", conv_panel)
                    time.sleep(3)
                except StaleElementReferenceException:
                    print("  Panel became stale during scroll, retrying...")
                    time.sleep(1)
                    continue
            
            print("  History loaded. Parsing all visible messages...")
            time.sleep(2)

            final_panel = self.driver.find_element(By.XPATH, panel_selector)
            message_bubbles_selector = ".//div[contains(@class, 'message-in') or contains(@class, 'message-out')]"
            message_bubbles = final_panel.find_elements(By.XPATH, message_bubbles_selector)
            
            print(f"  Found {len(message_bubbles)} message bubbles to process.")
            
            if len(message_bubbles) == 0:
                print("  NOTE: No message bubbles found. This chat might be empty.")
                return

            self.archive_data.setdefault(contact_name, [])
            for bubble in message_bubbles:
                parsed_message = self._parse_message_bubble(bubble, contact_name)
                if parsed_message and parsed_message.get('content') and "[Unsupported" not in parsed_message.get('content'):
                    self.archive_data[contact_name].append(parsed_message)

            print(f"  ✅ Successfully archived {len(self.archive_data.get(contact_name, []))} messages for {contact_name}.")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(f"  ❌ An error occurred while processing '{contact_name}'. Error: {e} in {fname} at line {exc_tb.tb_lineno}")

    def _parse_message_bubble(self, bubble_element, contact_name):
        # This function is correct and does not need changes.
        message_data = {'type': 'unknown', 'content': '', 'sender': '', 'timestamp': ''}
        try:
            bubble_class = bubble_element.get_attribute('class')
            if 'message-out' in bubble_class:
                message_data['sender'] = 'Me'
            elif 'message-in' in bubble_class:
                try:
                    copyable_text_div = bubble_element.find_element(By.XPATH, ".//div[contains(@class, 'copyable-text')]")
                    raw_sender_text = copyable_text_div.get_attribute("data-pre-plain-text")
                    sender_match = re.search(r'\]\s(.*?):', raw_sender_text)
                    if sender_match:
                        message_data['sender'] = sender_match.group(1).strip()
                    else:
                        message_data['sender'] = contact_name
                except (NoSuchElementException, AttributeError):
                    message_data['sender'] = contact_name
            else:
                return None

            time_element = bubble_element.find_element(By.XPATH, ".//span[@data-testid='message-meta']")
            message_data['timestamp'] = time_element.find_element(By.XPATH, ".//span").text

            try:
                media_msg = bubble_element.find_element(By.XPATH, ".//div[@data-testid='image-message' or @data-testid='video-message']")
                message_data['type'] = 'image' if media_msg.get_attribute('data-testid') == 'image-message' else 'video'
                try:
                    message_data['content'] = bubble_element.find_element(By.XPATH, ".//span[contains(@class, 'selectable-text')]").text
                except NoSuchElementException:
                    message_data['content'] = f"[{message_data['type'].capitalize()}]"
            except NoSuchElementException:
                try:
                    doc_element = bubble_element.find_element(By.XPATH, ".//div[@aria-label='Document message']")
                    message_data['type'] = 'document'
                    message_data['content'] = doc_element.find_element(By.XPATH, ".//span[@dir='auto']").text
                except NoSuchElementException:
                    try:
                        text_element = bubble_element.find_element(By.XPATH, ".//span[contains(@class, 'selectable-text')]")
                        message_data['type'] = 'text'
                        message_data['content'] = text_element.text
                    except NoSuchElementException:
                        message_data['content'] = "[Unsupported or Empty Message]"
            
            message_data['content'] = self._sanitize_string(message_data['content'])
            return message_data
        except (NoSuchElementException, StaleElementReferenceException):
            return None

    def run_archiver(self):
        if not self.login_and_wait():
            return
        
        chat_elements_to_process = self._get_top_chat_elements(limit=CHATS_TO_PROCESS)
        
        for element in chat_elements_to_process:
            self.archive_chat(element)
        
        self.save_to_json()
        print("\n--- Archiving process complete! ---")

    def save_to_json(self):
        print(f"\nSaving all collected data to '{OUTPUT_JSON_FILE}'...")
        try:
            with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.archive_data, f, ensure_ascii=False, indent=4)
            print("✅ Successfully saved data.")
        except Exception as e:
            print(f"❌ Failed to save data to JSON file. Error: {e}")

    def cleanup(self):
        print("Closing browser.")
        self.driver.quit()

if __name__ == "__main__":
    archiver = WhatsAppJsonArchiver()
    try:
        archiver.run_archiver()
    finally:
        archiver.cleanup()