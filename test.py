import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

def find_unread_chats():
    """
    Opens WhatsApp Web, waits for login, and then scans the chat
    list to find and display all contacts/groups with unread messages.
    """
    try:
        # --- 1. Setup WebDriver ---
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        # Optional: Run in headless mode (without a visible browser window)
        # options.add_argument("--headless")
        # options.add_argument("--window-size=1920,1080")
        # options.add_argument("--user-agent=Mozilla/5.0...") # To look like a real browser
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 60) # Long timeout for manual QR scan

        # --- 2. Open WhatsApp Web and Wait for Login ---
        driver.get("https://web.whatsapp.com/")
        print("Please scan the QR code with your phone to log in.")

        # Wait until the main chat list panel is loaded as a sign of successful login.
        side_panel_xpath = "//div[@id='side']"
        wait.until(EC.presence_of_element_located((By.XPATH, side_panel_xpath)))
        print("Login successful! Searching for unread messages...")
        
        # Give a few seconds for all chat elements to fully load
        time.sleep(5)

        # --- 3. Find All Unread Chats ---
        # The unread message indicator is a span with an aria-label like "1 unread message".
        # We will find the parent container of these indicators to get the chat info.
        # This XPath finds the main div for each chat list item that CONTAINS an unread indicator span.
        unread_chats_xpath = "//div[@id='pane-side']//div[.//span[contains(@aria-label, 'unread message')]]"
        
        # We use find_elements (plural) to get a list of all matching chats
        unread_chat_elements = driver.find_elements(By.XPATH, unread_chats_xpath)

        if not unread_chat_elements:
            print("\n✅ No unread chats found.")
        else:
            print(f"\n🔥 Found {len(unread_chat_elements)} chat(s) with unread messages:")
            print("------------------------------------------")

            # --- 4. Extract and Display Information for Each Unread Chat ---
            for chat in unread_chat_elements:
                try:
                    # Within each chat element, find the name and the unread count
                    # The name is in a span with a 'title' attribute
                    name_element = chat.find_element(By.XPATH, ".//span[@title]")
                    contact_name = name_element.get_attribute("title")
                    
                    # The unread count is in the span with the specific aria-label
                    unread_count_element = chat.find_element(By.XPATH, ".//span[contains(@aria-label, 'unread message')]")
                    unread_count = unread_count_element.text

                    print(f"👤 Contact/Group: {contact_name}")
                    print(f"💬 Unread Count:  {unread_count}\n")

                except StaleElementReferenceException:
                    # This can happen if the chat list updates while we are iterating.
                    print("Chat list updated, some data might have been missed. Re-run if necessary.")
                    continue
                except NoSuchElementException:
                    # In case the structure of a specific chat item is different (e.g., an announcement)
                    print("Could not parse one of the chat items.")
                    continue

            print("------------------------------------------")


    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # --- 5. Cleanup ---
        print("Script finished. The browser will close in 15 seconds.")
        time.sleep(15)
        driver.quit()

# --- Main Execution ---
if __name__ == "__main__":
    find_unread_chats()