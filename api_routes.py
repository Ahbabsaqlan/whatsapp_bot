# api_routes.py

from flask import Blueprint, jsonify, request
import database_manager as db
import threading
import time

# Import the functions from your renamed scraper file
try:
    from whatsappSynchoronizer import open_whatsapp, run_full_update
except ImportError:
    print("FATAL ERROR: Could not import from scraper_bot.py. Did you rename test5.py?")
    # Define dummy functions to prevent server from crashing on startup
    def open_whatsapp(): pass
    def run_full_update(driver): pass


# Create a Blueprint for our API routes
api = Blueprint('api', __name__)

# --- State Management for the background task ---
# A simple flag to prevent multiple updates from running at once.
is_update_running = False

def update_task_worker():
    """This function will run in a separate thread."""
    global is_update_running
    print("BACKGROUND_TASK: Starting full WhatsApp database update...")
    
    driver = None
    try:
        driver = open_whatsapp()
        run_full_update(driver)
        print("BACKGROUND_TASK: Update process completed successfully.")
    except Exception as e:
        print(f"BACKGROUND_TASK: An error occurred during the update: {e}")
    finally:
        if driver:
            driver.quit()
        # CRITICAL: Reset the flag so another update can be triggered later.
        is_update_running = False
        print("BACKGROUND_TASK: Worker thread finished and cleaned up.")


# --- API Endpoint Definitions ---

@api.route('/')
def index():
    return jsonify({"message": "Welcome to the WhatsApp Database API. See documentation for available endpoints."})

@api.route('/update', methods=['POST'])
def trigger_update():
    """
    API endpoint to start the WhatsApp scraping process in the background.
    """
    global is_update_running
    
    if is_update_running:
        # 409 Conflict: Indicates a request could not be processed because of conflict in the current state of the resource.
        return jsonify({"status": "Update already in progress."}), 409
    
    # Set the flag and start the background thread
    is_update_running = True
    update_thread = threading.Thread(target=update_task_worker)
    update_thread.start()
    
    # 202 Accepted: The request has been accepted for processing, but the processing has not been completed.
    return jsonify({"status": "Update process started in the background. Check server logs for progress."}), 202

@api.route('/update/status', methods=['GET'])
def get_update_status():
    """
    API endpoint to check if an update is currently running.
    """
    return jsonify({"is_update_running": is_update_running})


@api.route('/conversations/summary/<string:title>', methods=['GET'])
def get_summary(title):
    """API endpoint to get a conversation's summary by its title."""
    summary = db.get_summary_by_title(title)
    if "No conversation found" in summary:
        return jsonify({"error": summary}), 404
    return jsonify({"title": title, "summary": summary})

@api.route('/conversations/messages/<string:title>', methods=['GET'])
def get_messages(title):
    """API endpoint to get the last messages from a conversation."""
    try:
        count = request.args.get('count', default=5, type=int)
        messages_generator = db.get_last_messages(title, count=count)
        messages_list = [dict(row) for row in messages_generator]
        if not messages_list:
            return jsonify({"error": f"No messages found for title '{title}'"}), 404
        return jsonify({"title": title, "messages": messages_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/conversations/unreplied', methods=['GET'])
def get_unreplied():
    """API endpoint to get all unreplied conversations."""
    try:
        conversations = db.get_all_unreplied_conversations()
        conversations_list = [dict(row) for row in conversations]
        return jsonify({"unreplied_conversations": conversations_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500