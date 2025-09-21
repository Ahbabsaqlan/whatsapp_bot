import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def run_discovery():
    """
    This script's only goal is to open the first chat and print the HTML
    structure of the message list so we can find the correct selectors.
    """
    driver = None
    try:
        # --- Standard Setup ---
        profile_path = os.path.join(os.getcwd(), "whatsapp_profile")
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile_path}")
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 20)
        
        driver.get("https://web.whatsapp.com/")
        wait.until(EC.presence_of_element_located((By.ID, "side")))
        print("WhatsApp loaded.")
        time.sleep(5)

        # --- Get the first chat element ---
        print("Finding the first chat...")
        chat_name_selector = "//div[@id='pane-side']//div[@role='gridcell']//span[@title]"
        first_chat_element = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, chat_name_selector))
        )[0]
        contact_name = first_chat_element.get_attribute("title")
        print(f"Opening chat with '{contact_name}'...")
        
        # --- Click the first chat ---
        chat_container = first_chat_element.find_element(By.XPATH, "./ancestor::div[@role='listitem']")
        ActionChains(driver).move_to_element(chat_container).click().perform()

        # --- Wait for the message panel to load ---
        print("Waiting for message panel...")
        message_panel_selector = "//div[@id='main']//div[@tabindex='-1']"
        conv_panel = wait.until(EC.presence_of_element_located((By.XPATH, message_panel_selector)))
        print("Message panel found.")
        time.sleep(2) # Let messages render

        # --- THE DISCOVERY STEP ---
        print("\n" + "="*50)
        print("DISCOVERY MODE: PRINTING HTML OF MESSAGE LIST CHILDREN")
        print("Please copy everything from this point to the end and paste it in the response.")
        print("="*50 + "\n")

        # Get the direct children of the message panel
        children_of_panel = conv_panel.find_elements(By.XPATH, "./div")
        
        for i, child in enumerate(children_of_panel):
            try:
                # Get the outerHTML which includes the element itself and everything inside
                html_structure = child.get_attribute('outerHTML')
                print(f"--- ELEMENT {i+1} ---\n{html_structure}\n")
            except Exception as e:
                print(f"--- ELEMENT {i+1} (Could not get HTML) ---\nError: {e}\n")

    except Exception as e:
        print(f"\nAn error occurred during discovery: {e}")
    finally:
        if driver:
            print("="*50)
            print("Discovery complete. Closing browser in 15 seconds.")
            print("="*50)
            time.sleep(15)
            driver.quit()

if __name__ == "__main__":
    run_discovery()