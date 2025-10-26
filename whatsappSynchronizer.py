#!/usr/bin/env python3
import utility
utility.install_missing_libs()
import time
import threading
import random
import api_client as db
import selenium_handler as sh
import config  # Import the new configuration file


from tqdm import tqdm
from selenium.webdriver.support import expected_conditions as EC
from api_routes import app

# ==============================================================================
# --- WORKER FUNCTIONS ---
# These are the individual tasks that the scheduler will run.
# ==============================================================================

def run_api_server(whatsapp_name):
    """Function to run the Flask API server in a separate thread."""
    print("🚀 Starting API server on http://127.0.0.1:5001...")
    app.config['YOUR_WHATSAPP_NAME'] = whatsapp_name
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(port=5001)

def process_unreplied_queue():
    """
    Checks DB for unreplied messages and triggers the API to send a reply for each.
    This function is self-contained and does not need a browser instance.
    """
    print("   Checking database for unreplied messages...")
    try:
        unreplied_convos = db.get_all_unreplied_conversations()
        if not unreplied_convos:
            print("   ✔️ No unreplied conversations found.")
            return

        print(f"   📩 Found {len(unreplied_convos)} conversation(s) needing a reply. Processing now via API.")
        for conv in unreplied_convos:
            number = conv.get('phone_number')
            title = conv.get('title')
            
            if not number:
                print(f"   ⚠️ Skipping '{title}' as it has no phone number.")
                continue

            reply_text = random.choice(config.SIMULATED_AI_REPLIES)
            print(f"   🤖 Triggering API reply for {title} ({number})...")
            
            db.send_message_via_api(number, reply_text)
            
            time.sleep(config.REPLY_API_TASK_DELAY_SECONDS) 
            
        print("   ✅ Finished processing unreplied queue.")
    except Exception as e:
        print(f"\n   ❌ An error occurred during queue processing: {e}")

def run_sync_task():
    """
    Opens a browser, syncs all unread messages, and then closes the browser,
    releasing the profile lock for other tasks.
    """
    driver = None
    try:
        driver = sh.open_whatsapp()
        unread_button = sh.get_element(driver, "unread_filter_button", wait_condition=sh.EC.element_to_be_clickable, timeout=5, suppress_error=True)
        if not unread_button:
            print("   ✔️ No 'Unread' filter button found on main screen. Nothing to sync.")
            return

        unread_button.click()
        print("   'Unread' filter activated.")
        time.sleep(2)
        
        unread_contacts_snapshot = sh.get_all_contacts(driver)
        if unread_contacts_snapshot:
            print(f"   Found {len(unread_contacts_snapshot)} unread chat(s) to sync.")
            processed_in_batch = set()
            for contact_name in unread_contacts_snapshot:
                if contact_name in processed_in_batch: continue
                print(f"\n   --- Syncing '{contact_name}' ---")
                name, number = sh.open_chat(driver, contact_name, processed_in_batch)
                if not name: continue
                
                processed_in_batch.add(number if number else name)
                last_msg = db.get_last_message_from_db(number, name, config.YOUR_WHATSAPP_NAME)
                new_data = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg)
                db.save_messages_to_db(name, number, new_data)
                sh.close_current_chat(driver)
            
            try: sh.get_element(driver, "unread_filter_button", timeout=2).click()
            except: pass
        else:
            print("   ✔️ No unread chats found in UI.")
            try: unread_button.click()
            except: pass
    finally:
        if driver:
            print("   Closing sync browser to release profile lock.")
            driver.quit()

# ==============================================================================
# --- NEW PARALLEL TASK SCHEDULER ---
# ==============================================================================

def run_parallel_tasks():
    """
    The main scheduler loop. It runs sync and reply tasks on independent timers,
    giving the appearance of parallel execution while safely managing the
    single browser profile resource.
    """
    print("\n--- 🤖 Starting Parallel Bot Operations (Press Ctrl+C to stop) ---")
    print(f"    - Syncing new messages every {config.SYNC_INTERVAL_SECONDS} seconds.")
    print(f"    - Replying to messages every {config.REPLY_INTERVAL_SECONDS} seconds.")
    
    last_sync_time = 0
    last_reply_time = 0

    try:
        while True:
            now = time.time()

            

            # --- Check if it's time to run the SYNC task ---
            if (now - last_sync_time) > config.SYNC_INTERVAL_SECONDS:
                print("\n" + "─"*15 + " [SYNC TASK TRIGGERED] " + "─"*16)
                run_sync_task()
                last_sync_time = now # Reset timer after task runs
                print("─"*15 + " [SYNC TASK COMPLETE] " + "─"*17)

            # A short sleep to prevent the loop from consuming 100% CPU

            # --- Check if it's time to run the REPLY task ---
            if (now - last_reply_time) > config.REPLY_INTERVAL_SECONDS:
                print("\n" + "─"*15 + " [REPLY TASK TRIGGERED] " + "─"*15)
                process_unreplied_queue()
                last_reply_time = now # Reset timer after task runs
                print("─"*15 + " [REPLY TASK COMPLETE] " + "─"*16)

            time.sleep(5)
            
            
    except KeyboardInterrupt:
        print("\n🛑 Bot operations stopped by user.")

# ==============================================================================
# --- UTILITY AND MENU FUNCTIONS ---
# ==============================================================================

def run_full_update(driver):
    """Performs a one-time, full scan of all contacts to build the database."""
    print("\n--- Starting Full Database Update ---")
    contacts_to_process = sh.get_all_contacts(driver)
    processed_this_session = set()
    for contact_name in tqdm(contacts_to_process, desc="📂 Processing contacts", unit="contact"):
        name, number = sh.open_chat(driver, contact_name, processed_this_session)
        if not name:
            print(f"Skipping '{contact_name}' as it could not be opened."); sh.close_current_chat(driver); continue
        unique_id = number if number else name
        processed_this_session.add(unique_id)
        last_msg = db.get_last_message_from_db(number, name, config.YOUR_WHATSAPP_NAME)
        new_data = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg)
        db.save_messages_to_db(name, number, new_data)
        sh.close_current_chat(driver)
    print("\n🎉 Full update complete!")

def run_api_tools():
    """Provides a command-line interface for interacting with the database via API."""
    while True:
        print("\n" + "-"*20 + " Database API Tools " + "-"*20)
        print("1. Get conversation summary by title")
        print("2. Get last messages from a conversation")
        print("3. List all unreplied conversations")
        print("4. Send Manual Reply via API")
        print("5. Back to Main Menu")
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            title = input("Enter contact's title: ")
            print("\n--- Summary ---\n" + db.get_summary_by_title(title))
        elif choice == '2':
            title = input("Enter contact's title: ")
            messages = db.get_last_messages(title, count=5)
            print(f"\n--- Last 5 Messages for '{title}' ---")
            for msg in messages: print(f"[{msg['sending_date'][:16]}] {msg['role']}: {msg['content']}")
        elif choice == '3':
            conversations = db.get_all_unreplied_conversations()
            print("\n--- Unreplied Conversations ---")
            for conv in conversations: print(f"  - {conv['title']} ({conv.get('phone_number', 'N/A')}) | Last updated: {conv['updated'][:16]}")
        elif choice == '4':
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
            db.send_message_via_api(number, text)
            time.sleep(2) 
        elif choice == '5':
            break
        else:
            print("❌ Invalid choice.")

# ==============================================================================
# --- MAIN EXECUTION BLOCK ---
# ==============================================================================
if __name__ == "__main__":
    api_thread = threading.Thread(target=run_api_server, args=(config.YOUR_WHATSAPP_NAME,), daemon=True)
    api_thread.start()
    time.sleep(2) # Give the API server time to initialize

    db.init_db()
    
    while True:
        print("\n" + "="*40 + "\n       WhatsApp Automation Menu\n" + "="*40)
        print("1. Start Bot (Continuous Sync & Reply)")
        print("2. Update Database (One-Time Full Scan)")
        print("3. Database API Tools")
        print("4. Exit")
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            run_parallel_tasks()
        
        elif choice == '2': 
            driver = None
            try:
                driver = sh.open_whatsapp()
                run_full_update(driver)
            finally:
                if driver:
                    driver.quit()
        
        elif choice == '3':
            run_api_tools()

        elif choice == '4': 
            print("👋 Exiting program."); break
        else: 
            print("❌ Invalid choice.")