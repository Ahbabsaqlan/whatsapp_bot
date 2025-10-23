# api_routes.py
from flask import Flask, request, jsonify, current_app
import database_manager as db
import requests
import random
import datetime
import threading # <-- NEW: For running Selenium tasks in the background
import selenium_handler as sh # <-- NEW: The API will now directly use Selenium functions
import time # <-- NEW

app = Flask(__name__)

# --- CONFIG ---
SELF_API_BASE_URL = "http://127.0.0.1:5001"
SIMULATED_AI_REPLIES = [
    "Hello! Thanks for your message. Ahbab has received it and will get back to you soon.",
    "Hi there! Ahbab has seen your message and will reply shortly. Thank you!",
    "Got it! Thanks for reaching out. Ahbab will respond as soon as possible.",
    "Message received. Ahbab will get back to you shortly. Have a great day!"
]

# ==============================================================================
# --- NEW: True API-Based Send Message Endpoint ---
# ==============================================================================

@app.route('/send-message', methods=['POST'])
def send_message_endpoint():
    """
    Receives a request to send a message. Starts the process in a background thread.
    """
    data = request.json
    phone_number = data.get('phone_number')
    text = data.get('text')

    if not phone_number or not text:
        return jsonify({"status": "error", "message": "Missing 'phone_number' or 'text'"}), 400

    # Get the name from the app config, which was set at startup
    your_name = current_app.config.get('YOUR_WHATSAPP_NAME')
    if not your_name:
         return jsonify({"status": "error", "message": "Server is not configured with YOUR_WHATSAPP_NAME"}), 500

    # Start the Selenium task in a background thread so the API can respond immediately
    task_thread = threading.Thread(target=sync_and_send_worker, args=(phone_number, text, your_name))
    task_thread.start()

    # Immediately respond to the client
    return jsonify({"status": "success", "message": "Message sending task has been initiated."}), 202

def sync_and_send_worker(number, text, your_name):
    """
    This function runs in a separate thread and performs the entire Selenium workflow.
    """
    print(f"\n--- [API Task Started] ---")
    print(f"  - Target: {number}")
    print(f"  - Message: '{text[:30]}...'")
    
    driver = None
    try:
        # Step 1: Pre-check DB for existing contact
        contact_info = db.get_contact_details_by_phone(number)
        last_msg_bookmark = contact_info.get("last_meta_text") if contact_info else None
        
        # Step 2: Open browser and navigate
        driver = sh.open_whatsapp()
        sanitized_number = ''.join(filter(str.isdigit, number))
        driver.get(f"https://web.whatsapp.com/send?phone={sanitized_number}")

        # Step 3: Sync unread messages
        if not sh.get_element(driver, "reply_message_box", timeout=20):
            raise Exception(f"The number '{number}' might be invalid or not on WhatsApp.")
        
        actual_name, _ = sh.get_details_from_header(driver)
        unread_messages = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg_bookmark)
        if unread_messages:
            print(f"   - Synced {len(unread_messages)} new message(s).")
        
        # Step 4: Send your reply
        print("   - Sending reply...")
        sh.send_reply(driver, text)
        
        # Step 5: Sync the sent reply
        new_bookmark = unread_messages[-1]['meta_text'] if unread_messages else last_msg_bookmark
        sent_message_data = sh.smart_scroll_and_collect(driver, stop_at_last=new_bookmark)
        
        # Step 6: Consolidate and save everything
        all_messages_to_save = unread_messages + sent_message_data
        if all_messages_to_save:
            db.save_messages_to_db(actual_name, number, all_messages_to_save, your_name)
            print(f"   - Saved {len(all_messages_to_save)} total messages to the database.")
        
        print(f"--- [API Task for {number} Finished Successfully] ---")

    except Exception as e:
        print(f"--- [API Task for {number} FAILED] ---")
        print(f"   - Error: {e}")
    finally:
        if driver:
            print("   - Closing browser session.")
            driver.quit()


@app.route('/trigger-reply', methods=['POST'])
def trigger_reply():
    data = request.json
    phone_number = data.get('phone_number')
    if not phone_number:
        return jsonify({"status": "error", "message": "Missing phone_number"}), 400
    try:
        reply_text = random.choice(SIMULATED_AI_REPLIES)
        callback_url = f"{SELF_API_BASE_URL}/execute-send-reply"
        callback_payload = {"contact_number": phone_number, "reply_text": reply_text}
        print(f"🤖 Simulated AI chose reply for {phone_number}. Sending callback to self.")
        requests.post(callback_url, json=callback_payload)
        return jsonify({"status": "success", "message": "Simulated AI process triggered."}), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- MODIFIED: Reads name from config ---
@app.route('/execute-send-reply', methods=['POST'])
def execute_send_reply():
    data = request.json
    phone_number = data.get('contact_number')
    reply_text = data.get('reply_text')
    if not phone_number or not reply_text:
        return jsonify({"status": "error", "message": "Missing contact_number or reply_text"}), 400

    try:
        # --- THIS IS THE FIX: Read the name from the app's config ---
        your_name = current_app.config['YOUR_WHATSAPP_NAME']
        
        now = datetime.datetime.now()
        reply_message_object = {
            "date": now.strftime("%m/%d/%Y"), "time": now.strftime("%I:%M %p"),
            "sender": your_name, "content": reply_text,
            "meta_text": f"[{now.strftime('%I:%M %p, %m/%d/%Y')}] {your_name}: {reply_text}"
        }
        db.save_messages_to_db(phone_number, phone_number, [reply_message_object], your_name)
        print(f"💾 Saved outgoing reply for {phone_number} to DB.")

        command_queue = current_app.config['COMMAND_QUEUE']
        command = {"action": "send_reply", "number": phone_number, "text": reply_text}
        command_queue.put(command)
        print(f"✅ Queued reply for {phone_number}")
        return jsonify({"status": "success", "message": "Reply saved and queued."}), 200
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

@app.route('/messages', methods=['POST'])
def save_messages_route():
    data = request.json
    try:
        contact_name = data['contact_name']
        phone_number = data['phone_number']
        new_messages = data['new_messages']
        your_name = data['your_name']
        db.save_messages_to_db(contact_name, phone_number, new_messages, your_name)
        return jsonify({"status": "success", "message": f"Processed messages for {contact_name}"}), 201
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing key in request: {e}"}), 400
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

# --- API Tool Routes ---
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

if __name__ == '__main__':
    # Changed debug to False to match your log output
    app.run(debug=False, port=5001)