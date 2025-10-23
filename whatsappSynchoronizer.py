#!/usr/bin/env python3
import time
import threading
import utility
import api_client as db
import selenium_handler as sh
from queue import Queue

# --- Create a shared command queue ---
COMMAND_QUEUE = Queue()

utility.install_missing_libs()

from tqdm import tqdm
from api_routes import app

# ==============================================================================
# --- CONFIGURATION SECTION ---
# ==============================================================================

YOUR_WHATSAPP_NAME = "AHBAB SAKALAN"

# ==============================================================================
# --- Command Queue Processor (Unchanged) ---
# ==============================================================================
def process_command_queue(driver):
    """Checks the command queue and executes any pending browser actions."""
    if not COMMAND_QUEUE.empty():
        command = COMMAND_QUEUE.get()
        action = command.get('action')
        number = command.get('number')
        text = command.get('text')
        
        print(f"▶️  Executing command: '{action}' for {number}")

        if action == 'send_reply' and number and text:
            try:
                sanitized_number = ''.join(filter(str.isdigit, number))
                driver.get(f"https://web.whatsapp.com/send?phone={sanitized_number}")
                
                reply_box = sh.get_element(driver, "reply_message_box", timeout=15, context_message=f"Wait for chat to open for {number}.")
                
                if reply_box:
                    sh.send_reply(driver, text)
                    time.sleep(2)
                    sh.close_current_chat(driver)
                else:
                    print(f"⚠️  Could not find message box for {number}. Skipping reply.")
                    body = sh.get_element(driver, "body_tag_name")
                    if body:
                        body.send_keys(sh.Keys.ESCAPE)
            except Exception as e:
                print(f"❌ An error occurred during command execution: {e}")
        else:
            print(f"⚠️ Invalid or incomplete command received: {command}")
            
        COMMAND_QUEUE.task_done()

# ==============================================================================
# --- MAIN WORKFLOW FUNCTIONS (Modified) ---
# ==============================================================================

# --- MODIFIED: The function now accepts the name to configure the server ---
def run_api_server(queue, whatsapp_name):
    """Function to run the Flask API server, giving it access to the queue and config."""
    print("🚀 Starting API server on http://127.0.0.1:5001...")
    app.config['COMMAND_QUEUE'] = queue
    app.config['YOUR_WHATSAPP_NAME'] = whatsapp_name # Set the name in the config
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(port=5001)

def monitor_and_reply_to_unread(driver):
    # This function's internal logic is correct and remains unchanged.
    print("\n--- Starting Unread Message Monitor (Press Ctrl+C to stop) ---")
    try:
        while True:
            print("\n L  Checking for unread messages...")
            unread_button = sh.get_element(driver, "unread_filter_button", wait_condition=sh.EC.element_to_be_clickable, timeout=5, suppress_error=True)
            if unread_button:
                unread_button.click()
                print(" L  'Unread' filter activated.")
                time.sleep(2)
                unread_contacts_snapshot = sh.get_all_contacts(driver)
                if unread_contacts_snapshot:
                    print(f"📩 Found {len(unread_contacts_snapshot)} unread chat(s).")
                    processed_in_batch = set()
                    for contact_name in unread_contacts_snapshot:
                        if contact_name in processed_in_batch: continue
                        print(f"\n--- Processing '{contact_name}' ---")
                        name, number = sh.open_chat(driver, contact_name, processed_in_batch)
                        if not name: continue
                        processed_in_batch.add(number if number else name)
                        last_msg = db.get_last_message_from_db(number, name, YOUR_WHATSAPP_NAME)
                        new_data = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg)
                        db.save_messages_to_db(name, number, new_data, YOUR_WHATSAPP_NAME)
                        if new_data and number:
                            print(f"🤖 Triggering API-based reply for {name} ({number})")
                            db.trigger_reply(number)
                        sh.close_current_chat(driver)
                    try: sh.get_element(driver, "unread_filter_button", timeout=2).click()
                    except: pass
                else:
                    print("✔️ No unread chats found.")
                    try: unread_button.click()
                    except: pass
            else:
                print("✔️ No 'Unread' filter button found.")
            print("   ...checking for API commands to execute...")
            process_command_queue(driver)
            print("...waiting before next cycle...")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped.")

def run_full_update(driver):
    # This function remains unchanged.
    print("\n--- Starting Full Database Update ---")
    contacts_to_process = sh.get_all_contacts(driver)
    processed_this_session = set()
    for contact_name in tqdm(contacts_to_process, desc="📂 Processing contacts", unit="contact"):
        name, number = sh.open_chat(driver, contact_name, processed_this_session)
        if not name:
            print(f"Skipping '{contact_name}' as it could not be opened."); sh.close_current_chat(driver); continue
        unique_id = number if number else name
        processed_this_session.add(unique_id)
        last_msg = db.get_last_message_from_db(number, name, YOUR_WHATSAPP_NAME)
        new_data = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg)
        db.save_messages_to_db(name, number, new_data, YOUR_WHATSAPP_NAME)
        sh.close_current_chat(driver)
    print("\n🎉 Full update complete!")

def run_api_tools():
    while True:
        print("\n" + "-"*20 + " Database API Tools " + "-"*20)
        print("1. Get conversation summary by title")
        print("2. Get last messages from a conversation")
        print("3. List all unreplied conversations")
        print("4. Send Manual Reply via API") # This is the option you wanted
        print("5. Back to Main Menu")
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
            for conv in conversations: print(f"  - {conv['title']} ({conv.get('phone_number', 'N/A')}) | Last updated: {conv['updated'][:16]}")
        
        elif choice == '4':
            # --- THIS IS THE NEW, CLEAN "CLIENT" LOGIC ---
            print("\nThis tool will send a request to the API server to perform a full")
            print("'Sync & Send' operation in a new, dedicated browser session.")
            
            number = input("Enter the full phone number WITH country code (e.g., +880123...): ")
            if not number.startswith('+'):
                print("\n❌ FORMAT ERROR: The phone number must start with a '+' and country code.")
                continue

            text = input("Enter the message text to send: ")
            if not text:
                print("❌ ERROR: The message text cannot be empty.")
                continue

            # This single function call is all that's needed.
            # It tells the API server to do all the heavy lifting.
            db.send_message_via_api(number, text)
            time.sleep(2) # Give user time to read the confirmation message

        elif choice == '5':
            break
        else:
            print("❌ Invalid choice.")

# ==============================================================================
# --- MAIN EXECUTION BLOCK (Modified) ---
# ==============================================================================

if __name__ == "__main__":
    # --- MODIFIED: Pass the configuration to the thread ---
    api_thread = threading.Thread(target=run_api_server, args=(COMMAND_QUEUE, YOUR_WHATSAPP_NAME), daemon=True)
    api_thread.start()
    time.sleep(2)

    db.init_db()
    
    while True:
        print("\n" + "="*40 + "\n       WhatsApp Automation Menu\n" + "="*40)
        print("1. Update Database (Full Scan)")
        print("2. Monitor and Reply (API-Based Auto-Reply)")
        print("3. Database API Tools")
        print("4. Exit")
        choice = input("Enter your choice (1/2/3/4): ").strip()
        if choice in ['1', '2']:
            driver = None
            try:
                driver = sh.open_whatsapp()
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