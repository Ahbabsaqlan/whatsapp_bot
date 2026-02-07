# api_routes.py
from flask import Flask, request, jsonify, current_app
import database_manager as db
import threading
import selenium_handler as sh
import time

# api_routes.py
import os
from flask import Flask, request, jsonify, render_template

# This ensures Flask looks in the correct directory for your login.html
template_dir = os.path.abspath('templates')
app = Flask(__name__, template_folder=template_dir)

@app.route('/send-message', methods=['POST'])
def send_message_endpoint():
    data = request.json
    phone_number = data.get('phone_number')
    text = data.get('text')
    file_path = data.get('file_path') # <-- Get the new parameter

    # A message must have either text or a file
    if not phone_number or (not text and not file_path):
        return jsonify({"status": "error", "message": "Request must include 'phone_number' and either 'text' or 'file_path'"}), 400

    your_name = current_app.config.get('YOUR_WHATSAPP_NAME')
    task_lock = current_app.config.get('TASK_LOCK')
    if not your_name or not task_lock:
         return jsonify({"status": "error", "message": "Server is not configured correctly."}), 500

    # Pass all relevant data to the worker thread
    task_thread = threading.Thread(target=sync_and_send_worker, args=(phone_number, text, file_path, your_name, task_lock))
    task_thread.start()
    return jsonify({"status": "success", "message": "Message sending task has been initiated."}), 202

# --- MODIFIED WORKER FUNCTION ---
def sync_and_send_worker(number, text, file_path, your_name, lock):
    """
    Worker function that now handles sending either a text message or a file with a caption.
    """
    print(f"\n--- [API Task Started for {number}] ---")
    print("   Attempting to acquire lock for exclusive browser access...")
    
    with lock:
        print("   ✅ Lock acquired. Starting browser operation.")
        driver = None
        try:
            # Syncing logic is now only relevant if we are replying to an existing chat.
            # For sending a new message, we can simplify.
            
            driver = sh.open_whatsapp()
            if not driver:
                raise Exception("Failed to open WhatsApp. The task will be aborted.")

            sanitized_number = ''.join(filter(str.isdigit, number))
            driver.get(f"https://web.whatsapp.com/send?phone={sanitized_number}")
            
            # Wait for chat to be ready before proceeding
            if not sh.get_element(driver, "reply_message_box", timeout=20, context_message=f"Wait for chat with {number} to open."):
                raise Exception(f"Could not open chat with '{number}'. It might be an invalid number.")

            # --- NEW LOGIC: Decide whether to send a file or text ---
            if file_path:
                # If a file path is provided, send the file with 'text' as the caption
                sh.send_file_with_caption(driver, file_path, caption=text)
            elif text:
                # Otherwise, send a normal text message
                sh.send_reply(driver, text)
            
            # After sending, we can do a quick scrape to log the sent message
            actual_name, _ = sh.get_details_from_header(driver)
            last_msg = db.get_last_message_from_db(number, actual_name, your_name)
            sent_message_data = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg)
            if sent_message_data:
                db.save_messages_to_db(actual_name, number, sent_message_data)
            
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


@app.route('/attachments', methods=['GET'])
def get_attachments_route():
    """
    API endpoint to retrieve the set of all known attachment filenames from the database.
    """
    try:
        # We need to convert the set to a list for JSON serialization
        attachment_set = db.get_existing_attachments_from_db()
        return jsonify(list(attachment_set)), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    



# api_routes.py
from flask import render_template, jsonify
import selenium_handler as sh

login_driver = None # Global to keep track of the login process

@app.route('/login-page')
def login_page():
    # Make sure you create a folder named 'templates' with login.html inside
    return render_template('login.html')

@app.route('/get-qr')
def get_qr():
    global login_driver
    if login_driver: login_driver.quit()
    
    # Start driver in headless mode to capture QR
    login_driver = sh.open_whatsapp(headless=True)
    qr_data = sh.get_qr_base64(login_driver)
    
    if qr_data:
        return jsonify({"status": "success", "qr": qr_data})
    return jsonify({"status": "error", "message": "Failed to generate QR"})

@app.route('/check-auth')
def check_auth():
    global login_driver
    if not login_driver: return jsonify({"status": "idle"})
    
    # Check if the search box (login_check) appeared
    is_logged_in = sh.get_element(login_driver, "login_check", timeout=1, suppress_error=True)
    
    if is_logged_in:
        from storage_manager import upload_session
        upload_session() # Save to Supabase
        login_driver.quit()
        login_driver = None
        return jsonify({"status": "authenticated"})
    
    return jsonify({"status": "waiting"})

