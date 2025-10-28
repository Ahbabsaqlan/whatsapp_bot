# api_routes.py
from flask import Flask, request, jsonify, current_app
import database_manager as db
import threading
import selenium_handler as sh
import time

app = Flask(__name__)

@app.route('/send-message', methods=['POST'])
def send_message_endpoint():
    data = request.json
    phone_number = data.get('phone_number')
    text = data.get('text')
    if not phone_number or not text:
        return jsonify({"status": "error", "message": "Missing 'phone_number' or 'text'"}), 400

    your_name = current_app.config.get('YOUR_WHATSAPP_NAME')
    task_lock = current_app.config.get('TASK_LOCK') # Get the lock from the app config
    if not your_name or not task_lock:
         return jsonify({"status": "error", "message": "Server is not configured correctly (missing name or lock)."}), 500

    # Pass the lock to the worker thread
    task_thread = threading.Thread(target=sync_and_send_worker, args=(phone_number, text, your_name, task_lock))
    task_thread.start()
    return jsonify({"status": "success", "message": "Message sending task has been initiated."}), 202

# --- THIS IS THE MODIFIED WORKER FUNCTION ---
def sync_and_send_worker(number, text, your_name, lock):
    """
    This worker now acquires a lock to ensure it has exclusive access to the
    browser profile, pausing any scheduled tasks.
    """
    print(f"\n--- [API Task Started for {number}] ---")
    print("   Attempting to acquire lock for exclusive browser access...")
    
    with lock: # This will wait until the lock is free, then acquire it
        print("   ✅ Lock acquired. Starting browser operation.")
        driver = None
        try:
            contact_info = db.get_contact_details_by_phone(number)
            last_msg_bookmark = contact_info.get("last_meta_text") if contact_info else None
            
            driver = sh.open_whatsapp()
            if not driver: # Handle startup failure (e.g., network error)
                raise Exception("Failed to open WhatsApp. The task will be aborted.")

            sanitized_number = ''.join(filter(str.isdigit, number))
            driver.get(f"https://web.whatsapp.com/send?phone={sanitized_number}")

            if not sh.get_element(driver, "reply_message_box", timeout=20):
                raise Exception(f"The number '{number}' might be invalid or not on WhatsApp.")
            
            actual_name, _ = sh.get_details_from_header(driver)
            unread_messages = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg_bookmark)
            if unread_messages:
                print(f"   - Synced {len(unread_messages)} new message(s).")
            
            print("   - Sending reply...")
            sh.send_reply(driver, text)
            
            new_bookmark = unread_messages[-1]['meta_text'] if unread_messages else last_msg_bookmark
            sent_message_data = sh.smart_scroll_and_collect(driver, stop_at_last=new_bookmark)
            
            all_messages_to_save = unread_messages + sent_message_data
            if all_messages_to_save:
                db.save_messages_to_db(actual_name, number, all_messages_to_save)
            
            print(f"--- [API Task for {number} Finished Successfully] ---")

        except Exception as e:
            print(f"--- [API Task for {number} FAILED] ---")
            print(f"   - Error: {e}")
        finally:
            if driver:
                print("   - Closing API browser session.")
                driver.quit()
            print("   Releasing lock.")

@app.route('/messages', methods=['POST'])
def save_messages_route():
    data = request.json
    try:
        contact_name = data['contact_name']
        phone_number = data['phone_number']
        new_messages = data['new_messages']
        db.save_messages_to_db(contact_name, phone_number, new_messages)
        return jsonify({"status": "success", "message": f"Processed messages for {contact_name}"}), 201
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing key in request: {e}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/contact-details', methods=['GET'])
def get_contact_details():
    phone_number = request.args.get('phone_number')
    if not phone_number:
        return jsonify({"status": "error", "message": "Missing phone_number parameter"}), 400

    details = db.get_contact_details_by_phone(phone_number)
    
    if details:
        return jsonify(details), 200
    else:
        return jsonify({"message": "Contact not found"}), 404

@app.route('/init_db', methods=['POST'])
def init_db_route():
    try:
        db.init_db()
        return jsonify({"status": "success", "message": "Database initialized."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/last_message', methods=['GET'])
def get_last_message_route():
    phone_number = request.args.get('phone_number')
    title = request.args.get('title')
    your_name = request.args.get('your_name')
    
    if not title or not your_name:
        return jsonify({"status": "error", "message": "Missing 'title' or 'your_name' query parameters."}), 400

    meta_text = db.get_last_message_from_db(phone_number, title, your_name)
    return jsonify({"meta_text": meta_text})

@app.route('/prompt_history', methods=['GET'])
def get_prompt_history_route():
    phone_number = request.args.get('phone_number')
    count = request.args.get('count', 10, type=int)

    if not phone_number:
        return jsonify({"status": "error", "message": "Missing 'phone_number' query parameter."}), 400

    messages_rows = list(db.get_recent_messages_for_prompt(phone_number, count=count))
    messages_dicts = [dict(row) for row in messages_rows]
    return jsonify(messages_dicts)

@app.route('/summary', methods=['GET'])
def get_summary_route():
    title = request.args.get('title')
    if not title:
        return jsonify({"status": "error", "message": "Missing 'title' query parameter."}), 400
    summary = db.get_summary_by_title(title)
    return jsonify({"summary": summary})

@app.route('/messages', methods=['GET'])
def get_last_messages_route():
    title = request.args.get('title')
    count = request.args.get('count', 5, type=int)
    if not title:
        return jsonify({"status": "error", "message": "Missing 'title' query parameter."}), 400
    
    messages_rows = list(db.get_last_messages(title, count=count))
    messages_dicts = [dict(row) for row in messages_rows]
    return jsonify(messages_dicts)

@app.route('/unreplied', methods=['GET'])
def get_unreplied_route():
    conversations_rows = db.get_all_unreplied_conversations()
    conversations_dicts = [dict(row) for row in conversations_rows]
    return jsonify(conversations_dicts)