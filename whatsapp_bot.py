import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import database as db

# --- BOT CONFIGURATION ---
class BotConfig:
    # Keywords and their corresponding simple replies
    AUTO_REPLIES = {
        "hello": "Hi there! I'm a bot. How can I help?",
        "how are you": "I'm a bot, I'm doing great! Thanks for asking.",
        "help": "This is an automated response. The user will get back to you soon.",
        "default": "Thanks for your message! This is an automated reply. I will get back to you shortly."
    }
    # Time to wait (in seconds) between checking for new messages
    CHECK_INTERVAL = 10

class WhatsAppBot:
    def __init__(self):
        self.config = BotConfig()
        db.init_db()
        self.driver = self._setup_driver()
        self.wait = WebDriverWait(self.driver, 20)

    # ==============================================================================
    # ====== REPLACE THE OLD _setup_driver FUNCTION WITH THIS NEW ONE ============
    # ==============================================================================
    def _setup_driver(self):
        """Sets up the Chrome WebDriver with a persistent user profile."""
        
        # --- NEW: Define a path for the user profile ---
        # This will create a 'whatsapp_profile' folder in the same directory as your script
        profile_path = os.path.join(os.getcwd(), "whatsapp_profile")

        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()

        # --- NEW: Tell Chrome to use our profile path ---
        # This is the magic line that saves your session
        options.add_argument(f"--user-data-dir={profile_path}")

        # This option can help with stability on some systems
        options.add_argument("--disable-dev-shm-usage")
        
        print(f"Using profile directory: {profile_path}")
        return webdriver.Chrome(service=service, options=options)

    def login(self):
        """Opens WhatsApp Web and waits for the user to log in via QR code."""
        self.driver.get("https://web.whatsapp.com/")
        print("Please scan the QR code with your phone to log in.")
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='side']"))
            )
            print("Login successful!")
            return True
        except TimeoutException:
            print("Login failed. Timed out waiting for QR scan.")
            return False

    # ==============================================================================
    # ====== REPLACE THE OLD FUNCTION IN whatsapp_bot.py WITH THIS NEW ONE =======
    # ==============================================================================

    def find_and_process_chats(self):
        """Finds both unread chats and chats needing a reply from the DB, then processes them."""
        print("\n--- Checking for messages ---")
        
        # 1. Get chats marked as 'unread' on WhatsApp Web
        unread_contacts = set()
        try:
            # Find the unread markers first
            unread_markers = self.driver.find_elements(By.XPATH, "//span[contains(@aria-label, 'unread message')]")
            
            print(f"Found {len(unread_markers)} unread chat markers.")

            # For each marker, find its parent chat item and extract the contact name
            # This is more robust than the previous single-XPath approach.
            for marker in unread_markers:
                try:
                    # The 'role="listitem"' is a much more stable way to find the parent chat container
                    parent_chat = marker.find_element(By.XPATH, "./ancestor::div[@role='listitem']")
                    # From that container, find the span with the title (contact name)
                    name_element = parent_chat.find_element(By.XPATH, ".//span[@title]")
                    contact_name = name_element.get_attribute("title")
                    if contact_name:
                        unread_contacts.add(contact_name)
                except NoSuchElementException:
                    # This can happen for non-standard chats like "Community announcements"
                    print("  Could not parse name for one of the unread chats. Skipping it.")
                    continue

        except Exception as e:
            print(f"An error occurred while searching for unread chats: {e}")
        
        # 2. Get chats that we haven't replied to from our database
        db_unreplied = set(db.get_chats_needing_reply())
        
        # 3. Combine both sets to get a unique list of contacts to process
        all_chats_to_process = list(unread_contacts.union(db_unreplied))
        
        if not all_chats_to_process:
            print("No new messages or pending replies.")
            return

        print(f"Found {len(all_chats_to_process)} unique chats to process: {', '.join(all_chats_to_process)}")
        
        for contact_name in all_chats_to_process:
            # Before processing, click somewhere neutral to avoid stale elements
            try:
                self.driver.find_element(By.XPATH, "//header").click()
                time.sleep(0.5)
            except:
                pass # Ignore if it fails, just a precaution
                
            self.process_chat(contact_name)

    # ==============================================================================
    # ====== REPLACE THE OLD process_chat FUNCTION WITH THIS NEW ONE =============
    # ==============================================================================
    def process_chat(self, contact_name):
        """Opens a chat, reads new messages, logs them, and sends a reply."""
        try:
            print(f"Processing chat with: {contact_name}")
            
            # Find the chat element using its title
            chat_xpath = f"//span[@title='{contact_name}']"
            chat_element = self.wait.until(EC.presence_of_element_located((By.XPATH, chat_xpath)))
            
            # Use JavaScript to click the parent container of the chat element. This is robust.
            # It finds the ancestor div with role="listitem" (the whole chat row) and clicks it.
            chat_container = chat_element.find_element(By.XPATH, "./ancestor::div[@role='listitem']")
            self.driver.execute_script("arguments[0].click();", chat_container)
            print(f"  Successfully clicked on chat: {contact_name}")
            time.sleep(2) # Wait for messages to load

            # Get contact ID from DB
            contact_id = db.get_or_create_contact(contact_name)

            # Scrape last few incoming messages
            # Using a more robust selector for the message bubble
            message_bubbles = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'message-in')]")
            
            new_messages_found = False
            last_message_text = ""

            for bubble in message_bubbles[-5:]: # Check last 5 incoming messages
                try:
                    # Find the selectable-text span within the bubble
                    msg_element = bubble.find_element(By.XPATH, ".//span[contains(@class, 'selectable-text')]")
                    msg_text = msg_element.text.strip().lower()
                    
                    if msg_text and not db.check_if_message_exists(contact_id, msg_text):
                        new_messages_found = True
                        last_message_text = msg_text
                        print(f"  New message from {contact_name}: '{msg_text}'")
                        db.log_message(contact_id, contact_name, msg_text)

                except NoSuchElementException:
                    # This can happen with messages that are just emojis, stickers, or images
                    continue

            if new_messages_found:
                reply = self._get_reply(last_message_text)
                self._send_message(reply)
                db.log_message(contact_id, "Me", reply, is_from_me=True)
                db.mark_chat_as_replied(contact_name)

        except (TimeoutException, NoSuchElementException):
            print(f"  Could not process chat with '{contact_name}'. Maybe it's no longer on the screen or the name is incorrect.")
        except Exception as e:
            print(f"  An error occurred while processing {contact_name}: {e}")

    def _get_reply(self, message):
        """Generates a reply based on the message content."""
        for keyword, response in self.config.AUTO_REPLIES.items():
            if keyword in message:
                return response
        return self.config.AUTO_REPLIES["default"]

    # ==============================================================================
    # ====== REPLACE THE OLD _send_message FUNCTION WITH THIS NEW ONE ============
    # ==============================================================================
    def _send_message(self, message):
        """Types and sends a message in the currently open chat."""
        try:
            # This is the new, more stable selector for the message input box
            # It targets the div with role="textbox"
            message_box_xpath = "//div[@role='textbox' and @contenteditable='true']"
            message_box = self.wait.until(EC.presence_of_element_located((By.XPATH, message_box_xpath)))
            
            message_box.send_keys(message)
            
            # The send button selector is usually stable
            send_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']")))
            send_button.click()
            print(f"  Replied with: '{message}'")
            time.sleep(1) # Wait a moment after sending
        except TimeoutException:
            print("  Could not find message box or send button. The chat might not allow replies (e.g., official announcements).")

    def run(self):
        """Main loop to continuously check for and respond to messages."""
        if not self.login():
            self.cleanup()
            return
            
        print("Bot is running... Press Ctrl+C to stop.")
        while True:
            try:
                self.find_and_process_chats()
                time.sleep(self.config.CHECK_INTERVAL)
            except KeyboardInterrupt:
                print("\nStopping bot.")
                break
            except Exception as e:
                print(f"A critical error occurred in the main loop: {e}")
                # Optional: Add screenshot on error
                # self.driver.save_screenshot('error_screenshot.png')
                time.sleep(60) # Wait a bit before retrying

    def cleanup(self):
        """Closes the browser."""
        print("Closing browser.")
        self.driver.quit()


# --- Main Execution ---
if __name__ == "__main__":
    bot = WhatsAppBot()
    try:
        bot.run()
    finally:
        bot.cleanup()