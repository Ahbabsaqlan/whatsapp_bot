import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
# The name of the contact or group you want to read messages from.
# Must be an exact match to the name in your chat list.
CONTACT_NAME = "Faisal" # <--- IMPORTANT: CHANGE THIS TO YOUR TARGET CONTACT/GROUP

def read_whatsapp_messages(contact_name):
    """
    Opens WhatsApp Web, finds a specific chat, and prints the last few messages.
    """
    try:
        # --- 1. Setup WebDriver ---
        # Automatically downloads and manages the correct ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        wait = WebDriverWait(driver, 60) # Long timeout for manual QR scan

        # --- 2. Open WhatsApp Web and Wait for Login ---
        driver.get("https://web.whatsapp.com/")
        print("Please scan the QR code with your phone to log in.")

        # We wait until the main chat list panel is loaded.
        # This is a good indicator that the user has successfully logged in.
        side_panel_xpath = "//div[@id='side']"
        wait.until(EC.presence_of_element_located((By.XPATH, side_panel_xpath)))
        print("Login successful!")

        # --- 3. Find and Open the Target Chat ---
        # We search for the chat by its title, which is the contact's name.
        print(f"Searching for chat with '{contact_name}'...")
        chat_xpath = f"//span[@title='{contact_name}']"
        target_chat = wait.until(EC.element_to_be_clickable((By.XPATH, chat_xpath)))
        target_chat.click()
        print(f"Successfully opened chat with '{contact_name}'.")

        # Wait a moment for the messages to load in the chat panel
        time.sleep(2)

        # --- 4. Read the Messages ---
        # WhatsApp message elements have complex and changing class names.
        # This XPath targets the text content within the message bubbles.
        # The class 'selectable-text' is commonly used for the message text.
        message_elements_xpath = "//div[contains(@class, 'message-in')]//span[contains(@class, 'selectable-text')]"
        message_elements = driver.find_elements(By.XPATH, message_elements_xpath)

        if not message_elements:
            print("No messages found. The selectors might be outdated or there are no messages.")
        else:
            print("\n--- RECENT MESSAGES ---")
            # Get the last 10 messages to avoid printing too much
            for message in message_elements[-10:]:
                # .text attribute gets the visible text of the element
                print(f"- {message.text}")
            print("------------------------\n")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # --- 5. Keep Browser Open and Cleanup ---
        print("Script finished. The browser will close in 30 seconds.")
        time.sleep(30) # Keep the browser open for a while
        driver.quit()

# --- Main Execution ---
if __name__ == "__main__":
    # You MUST change "John Doe" to the exact name of the contact or group.
    read_whatsapp_messages(CONTACT_NAME)