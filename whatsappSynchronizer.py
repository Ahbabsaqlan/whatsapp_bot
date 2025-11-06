#!/usr/bin/env python3
import utility
utility.install_missing_libs()
import time
import threading
import random
import controller as db  # Using your new name
import selenium_handler as sh
import config
from datetime import datetime, timedelta
import ai_manager as ai  # Import the new AI manager
import os

from tqdm import tqdm
from selenium.webdriver.support import expected_conditions as EC
from api_routes import app

TASK_LOCK = threading.Lock()

def run_api_server(whatsapp_name, lock):
    """Function to run the Flask API server, now aware of the global lock."""
    print("🚀 Starting API server on http://127.0.0.1:5001...")
    app.config['YOUR_WHATSAPP_NAME'] = whatsapp_name
    app.config['TASK_LOCK'] = lock
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(port=5001)

# --- THIS IS THE FINAL AI-POWERED VERSION ---
def process_unreplied_queue():
    """
    Checks DB for recent unreplied messages, generates a reply using Gemini,
    and triggers the API to send it.
    """
    print("   Checking database for unreplied messages...")
    try:
        unreplied_convos = db.get_all_unreplied_conversations()
        if not unreplied_convos:
            print("   ✔️ No unreplied conversations found.")
            return

        print(f"   📩 Found {len(unreplied_convos)} unreplied conversation(s). Filtering by age...")
        time_threshold = datetime.now() - timedelta(days=config.REPLY_MAX_AGE_DAYS)
        
        for conv in unreplied_convos:
            number = conv.get('phone_number')
            title = conv.get('title')
            last_message_date_str = conv.get('last_message_date')

            if not number:
                print(f"   ⚠️ Skipping '{title}' as it has no phone number.")
                continue

            try:
                last_message_time = datetime.fromisoformat(last_message_date_str)
                if last_message_time < time_threshold:
                    print(f"   ⚪️ Skipping '{title}' as its last message is older than {config.REPLY_MAX_AGE_DAYS} days.")
                    continue
            except (ValueError, TypeError):
                print(f"   ⚠️ Skipping '{title}' due to invalid last message date: {last_message_date_str}")
                continue

            # --- GEMINI INTEGRATION LOGIC ---
            print(f"\n   Processing AI reply for '{title}'...")
            # 1. Fetch conversation history for context
            history = db.get_prompt_history(number)
            if not history:
                print(f"   Could not fetch history for '{title}'. Skipping AI reply.")
                continue

            # 2. Generate a reply using the AI manager
            reply_text = ai.generate_reply(history, config.YOUR_WHATSAPP_NAME)

            # 3. Send the AI-generated reply if it's valid
            if reply_text:
                db.send_message_via_api(number, reply_text)
                time.sleep(config.REPLY_API_TASK_DELAY_SECONDS)
            else:
                print(f"   AI did not generate a reply for '{title}'. Skipping.")
            
        print("   ✅ Finished processing unreplied queue.")
    except Exception as e:
        print(f"\n   ❌ An error occurred during queue processing: {e}")

def run_sync_task():
    """
    This scheduled task now also acquires the lock before running, ensuring it
    waits if a manual API call is in progress.
    """
    print("   Attempting to acquire lock for scheduled sync...")
    with TASK_LOCK:
        print("   ✅ Lock acquired. Starting browser for sync.")
        driver = None
        try:
            driver = sh.open_whatsapp()
            if not driver:
                raise Exception("Failed to open WhatsApp for sync.")

            unread_button = sh.get_element(driver, "unread_filter_button", wait_condition=sh.EC.element_to_be_clickable, timeout=5, suppress_error=True)
            if not unread_button:
                print("   ✔️ No 'Unread' filter button found on main screen. Nothing to sync.")
                return

            unread_button.click()
            print("   'Unread' filter activated.")
            time.sleep(2)
            
            unread_contacts_snapshot = sh.get_all_contacts(driver)
            if unread_contacts_snapshot:
                processed_in_batch = set()
                for contact_name in unread_contacts_snapshot:
                    if contact_name == "WhatsApp": continue
                    if contact_name in processed_in_batch: continue
                    name, number = sh.open_chat(driver, contact_name, processed_in_batch)
                    if not name: continue
                    processed_in_batch.add(number if number else name)
                    last_msg = db.get_last_message_from_db(number, name, config.YOUR_WHATSAPP_NAME)
                    new_data = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg)
                    db.save_messages_to_db(name, number, new_data)
                    sh.close_current_chat(driver)
            else:
                print("   ✔️ No unread chats found in UI.")
                
        except Exception as e:
            print(f"\n   ❌ An error occurred during sync task: {e}")
        finally:
            if driver:
                print("   Closing sync browser to release profile lock.")
                driver.quit()
            print("   Releasing lock.")

def run_parallel_tasks(only_sync=False):
    """
    The main scheduler loop. It runs sync and reply tasks on independent timers.
    """
    print("\n--- 🤖 Starting Parallel Bot Operations (Press Ctrl+C to stop) ---")
    if only_sync:
        print("    - Mode: Sync Only")
    else:
        print("    - Mode: Sync & Auto-Reply")
    print(f"    - Syncing new messages every {config.SYNC_INTERVAL_SECONDS} seconds.")
    if not only_sync:
        print(f"    - Replying to messages every {config.REPLY_INTERVAL_SECONDS} seconds.")
    
    last_sync_time = 0
    last_reply_time = 0

    try:
        while True:
            now = time.time()
            if (now - last_sync_time) > config.SYNC_INTERVAL_SECONDS:
                print("\n" + "─"*15 + " [SYNC TASK TRIGGERED] " + "─"*16)
                run_sync_task()
                last_sync_time = now
                print("─"*15 + " [SYNC TASK COMPLETE] " + "─"*17)

            if not only_sync:
                if (now - last_reply_time) > config.REPLY_INTERVAL_SECONDS:
                    print("\n" + "─"*15 + " [REPLY TASK TRIGGERED] " + "─"*15)
                    process_unreplied_queue()
                    last_reply_time = now
                    print("─"*15 + " [REPLY TASK COMPLETE] " + "─"*16)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Bot operations stopped by user.")

def run_full_update(driver):
    """Performs a one-time, full scan of all contacts to build the database."""
    print("\n--- Starting Full Database Update ---")
    contacts_to_process = ['Me😵‍💫']#['Me😵‍💫']sh.get_all_contacts(driver)
    processed_this_session = set()
    for contact_name in tqdm(contacts_to_process, desc="📂 Processing contacts", unit="contact"):
        if contact_name == "WhatsApp": continue
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
        print("4. Send Manual Message / File via API")
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
            for conv in conversations: print(f"  - {conv['title']} ({conv.get('phone_number', 'N/A')}) | Last message: {conv.get('last_message_date', 'N/A')[:16]}")
        elif choice == '4':
            print("\nThis tool can send a text message, or a file with an optional caption.")
            
            number = input("Enter the full phone number WITH country code (e.g., +880123...): ")
            if not number.startswith('+'):
                print("\n❌ FORMAT ERROR: The phone number must start with a '+' and country code.")
                continue

            file_path = input("Enter the FULL path to the file (or press Enter to skip): ").strip()
            text = None
            
            if file_path:
                if not os.path.exists(file_path):
                    print(f"❌ FILE NOT FOUND at '{file_path}'. Aborting.")
                    continue
                # If there's a file, the text becomes an optional caption
                text = input("Enter an optional caption for the file (or press Enter to skip): ").strip()
            else:
                # If there's no file, the text is a required message
                text = input("Enter the message text to send: ").strip()
                if not text:
                    print("❌ ERROR: You must provide a message if not sending a file.")
                    continue

            # Call the updated API client function
            db.send_message_via_api(number, text=text, file_path=file_path)
            time.sleep(2) 

        elif choice == '5':
            break
        else:
            print("❌ Invalid choice.")


def debug_ui_elements():
    """
    Opens a browser, scrapes the raw outerHTML of all 'message-in' and 'message-out'
    elements, and writes the output directly to 'debug_output.txt'.
    """
    print("\n--- 🛠️ Starting UI Debugging Mode ---")
    print("This mode will open a browser. Please navigate to the chat you want to inspect.")
    
    driver = None
    try:
        driver = sh.open_whatsapp()
        if not driver:
            print("❌ Could not open browser. Aborting debug session.")
            return

        # This input prompt gives you time to manually set up the browser state.
        input("\n✅ Browser is open. Manually open the target chat, then press Enter here to continue...")

        print("\nInspecting all visible message elements ('message-in' and 'message-out')...")
        # Use the 'all_messages' selector key which corresponds to 'div.message-in, div.message-out'
        elements = sh.get_element(driver, 'all_messages', timeout=10, find_all=True, suppress_error=True)

        if not elements:
            print("❌ No message elements were found on the screen.")
            return

        print(f"✅ Found {len(elements)} elements. Writing their HTML to debug_output.txt...")
        
        # Write the raw HTML output to a text file
        output_filename = "debug_output.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"Raw HTML Dump of {len(elements)} Message Elements\n")
            f.write("="*50 + "\n\n")

            for i, element in enumerate(elements):
                try:
                    outer_html = element.get_attribute('outerHTML')
                    f.write(f"--- Element {i+1} ---\n\n")
                    f.write(outer_html)
                    f.write("\n\n" + "="*50 + "\n\n")
                except Exception as e:
                    f.write(f"--- Element {i+1} ---\n\n")
                    f.write(f"!!! ERROR: Could not retrieve HTML for this element. Reason: {e} !!!")
                    f.write("\n\n" + "="*50 + "\n\n")

        print(f"\n✅ Report complete! Please check the file: '{output_filename}'")
        input("Press Enter to close the browser and exit debug mode.")

    except Exception as e:
        print(f"An error occurred during the debug session: {e}")
    finally:
        if driver:
            driver.quit()
        print("--- 🛠️ Exited UI Debugging Mode ---")


# def debug_ui_elements():
#     """
#     Opens a browser, runs the analysis engine on all visible message elements,
#     and writes a detailed diagnostic report to 'debug_analysis.txt'.
#     """
#     print("\n--- 🛠️ Starting UI Analysis Mode ---")
#     driver = None
#     try:
#         driver = sh.open_whatsapp()
#         if not driver:
#             return

#         input("\n✅ Browser is open. Manually open the target chat, then press Enter here to continue...")

#         print("\nAnalyzing all visible message elements ('message-in' and 'message-out')...")
#         elements = sh.get_element(driver, 'all_messages', timeout=10, find_all=True, suppress_error=True)

#         if not elements:
#             print("❌ No message elements were found on the screen.")
#             return

#         print(f"✅ Found {len(elements)} elements. Writing analysis to debug_analysis.txt...")
        
#         output_filename = "debug_analysis.txt"
#         with open(output_filename, "w", encoding="utf-8") as f:
#             f.write("WhatsApp Message Structure Analysis Report\n")
#             f.write("="*50 + "\n\n")

#             for i, element in enumerate(tqdm(elements, desc="🔍 Analyzing elements")):
#                 report = sh.analyze_element_structure(element)
#                 f.write(f"--- Element {i+1} ---\n")
#                 f.write(f"Class: {report['class']}\n\n")
                
#                 # Print the result of every check
#                 for check_name, result in report['checks'].items():
#                     f.write(f"- Check for {check_name.replace('_', ' ')}: {result}\n")
                
#                 f.write("\n" + "="*50 + "\n\n")

#         print(f"\n✅ Analysis complete! Please check the file: '{output_filename}'")
#         print("    This file shows exactly what the script sees for each message type.")
#         input("Press Enter to close the browser and exit debug mode.")

#     except Exception as e:
#         print(f"An error occurred during the debug session: {e}")
#     finally:
#         if driver:
#             driver.quit()
#         print("--- 🛠️ Exited Analysis Mode ---")

if __name__ == "__main__":
    api_thread = threading.Thread(target=run_api_server, args=(config.YOUR_WHATSAPP_NAME, TASK_LOCK), daemon=True)
    api_thread.start()
    time.sleep(2)
    db.init_db()
    
    while True:
        print("\n" + "="*40 + "\n       WhatsApp Automation Menu\n" + "="*40)
        print("0. Start Bot (Continuous Sync Only)")
        print("1. Start Bot (Continuous Sync & AI Auto-Reply)")
        print("2. Update Database (One-Time Full Scan)")
        print("3. Database API Tools")
        print("4. Debug UI Elements")
        print("5. Exit")
        choice = input("Enter your choice (0-5): ").strip()
        
        if choice == '0':
            run_parallel_tasks(True)
        elif choice == '1':
            run_parallel_tasks(False)
        elif choice == '2': 
            with TASK_LOCK:
                driver = None
                try:
                    driver = sh.open_whatsapp()
                    if driver:
                        run_full_update(driver)
                finally:
                    if driver:
                        driver.quit()
        elif choice == '3':
            run_api_tools()
        elif choice == '4':
            debug_ui_elements()
        elif choice == '5': 
            print("👋 Exiting program."); break
        else: 
            print("❌ Invalid choice.")