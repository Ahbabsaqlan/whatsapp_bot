# lawyer_api_routes.py
"""
Enhanced API routes for lawyer directory integration.
Provides endpoints for multi-user lawyer-client communication.
"""

from flask import Blueprint, request, jsonify, current_app
import threading
import lawyer_directory_integration as ldi
import database_manager as db
import selenium_handler as sh
import json

lawyer_api = Blueprint('lawyer_api', __name__)

def authenticate_lawyer(request):
    """
    Authenticate a lawyer using API key from headers.
    
    Returns:
        Lawyer dict or None if authentication fails
    """
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return None
    
    return ldi.get_lawyer_by_api_key(api_key)

@lawyer_api.route('/lawyers', methods=['POST'])
def create_lawyer():
    """
    Create a new lawyer account.
    
    Body:
        {
            "name": "John Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "whatsapp_name": "John Doe",
            "profile_path": "/path/to/profile" (optional)
        }
    """
    data = request.json
    
    required_fields = ['name', 'email', 'phone_number', 'whatsapp_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
    
    lawyer = ldi.create_lawyer(
        name=data['name'],
        email=data['email'],
        phone_number=data['phone_number'],
        whatsapp_name=data['whatsapp_name'],
        profile_path=data.get('profile_path')
    )
    
    if lawyer:
        # Remove sensitive API key from response for security, or return it only on creation
        return jsonify({
            "status": "success",
            "message": "Lawyer account created successfully",
            "lawyer": lawyer
        }), 201
    else:
        return jsonify({"status": "error", "message": "Failed to create lawyer account"}), 500

@lawyer_api.route('/lawyers/me', methods=['GET'])
def get_my_profile():
    """
    Get the authenticated lawyer's profile.
    
    Headers:
        X-API-Key: <lawyer_api_key>
    """
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    # Remove API key from response
    lawyer_safe = dict(lawyer)
    lawyer_safe.pop('api_key', None)
    
    return jsonify({"status": "success", "lawyer": lawyer_safe}), 200

@lawyer_api.route('/clients', methods=['POST'])
def create_client():
    """
    Create a new client and link to authenticated lawyer.
    
    Headers:
        X-API-Key: <lawyer_api_key>
    
    Body:
        {
            "name": "Jane Smith",
            "phone_number": "+1234567890",
            "email": "jane@example.com" (optional)
        }
    """
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    data = request.json
    
    if not data.get('name') or not data.get('phone_number'):
        return jsonify({"status": "error", "message": "Missing required fields: name, phone_number"}), 400
    
    # Create or get client
    client_id = ldi.create_or_get_client(
        name=data['name'],
        phone_number=data['phone_number'],
        email=data.get('email')
    )
    
    # Link to lawyer
    rel_id = ldi.link_lawyer_client(lawyer['id'], client_id)
    
    return jsonify({
        "status": "success",
        "message": "Client created and linked to your account",
        "client_id": client_id,
        "relationship_id": rel_id
    }), 201

@lawyer_api.route('/clients', methods=['GET'])
def get_my_clients():
    """
    Get all clients for the authenticated lawyer.
    
    Headers:
        X-API-Key: <lawyer_api_key>
    
    Query params:
        status: Filter by relationship status (default: 'active')
    """
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    status = request.args.get('status', 'active')
    clients = ldi.get_lawyer_clients(lawyer['id'], status)
    
    return jsonify({
        "status": "success",
        "clients": clients,
        "count": len(clients)
    }), 200

@lawyer_api.route('/messages/send', methods=['POST'])
def send_message_as_lawyer():
    """
    Send a message to a client as the authenticated lawyer.
    
    Headers:
        X-API-Key: <lawyer_api_key>
    
    Body:
        {
            "client_phone_number": "+1234567890",
            "text": "Hello, this is your lawyer",
            "file_path": "/path/to/file" (optional)
        }
    """
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    data = request.json
    phone_number = data.get('client_phone_number')
    text = data.get('text')
    file_path = data.get('file_path')
    
    if not phone_number or (not text and not file_path):
        return jsonify({
            "status": "error", 
            "message": "Request must include 'client_phone_number' and either 'text' or 'file_path'"
        }), 400
    
    # Get the task lock from app config
    task_lock = current_app.config.get('TASK_LOCK')
    if not task_lock:
        return jsonify({"status": "error", "message": "Server is not configured correctly."}), 500
    
    # Start background task to send message
    task_thread = threading.Thread(
        target=send_message_worker,
        args=(phone_number, text, file_path, lawyer, task_lock)
    )
    task_thread.start()
    
    return jsonify({
        "status": "success",
        "message": "Message sending task has been initiated."
    }), 202

def send_message_worker(phone_number, text, file_path, lawyer, lock):
    """
    Worker function to send message as a specific lawyer.
    Uses the lawyer's WhatsApp profile.
    """
    print(f"\n--- [Lawyer API Task Started for {phone_number} by {lawyer['name']}] ---")
    print("   Attempting to acquire lock for exclusive browser access...")
    
    with lock:
        print("   ✅ Lock acquired. Starting browser operation.")
        driver = None
        try:
            # Open WhatsApp with lawyer's profile
            driver = sh.open_whatsapp(profile_path=lawyer.get('profile_path'))
            if not driver:
                raise Exception("Failed to open WhatsApp. The task will be aborted.")
            
            sanitized_number = ''.join(filter(str.isdigit, phone_number))
            driver.get(f"https://web.whatsapp.com/send?phone={sanitized_number}")
            
            # Wait for chat to be ready
            if not sh.get_element(driver, "reply_message_box", timeout=20, 
                                context_message=f"Wait for chat with {phone_number} to open."):
                raise Exception(f"Could not open chat with '{phone_number}'. It might be an invalid number.")
            
            # Send file or text
            if file_path:
                sh.send_file_with_caption(driver, file_path, caption=text)
            elif text:
                sh.send_reply(driver, text)
            
            # Scrape the sent message to log it
            actual_name, _ = sh.get_details_from_header(driver)
            last_msg = db.get_last_message_from_db(phone_number, actual_name, lawyer['whatsapp_name'])
            sent_message_data = sh.smart_scroll_and_collect(driver, stop_at_last=last_msg)
            
            if sent_message_data:
                db.save_messages_to_db(actual_name, phone_number, sent_message_data)
            
            # Trigger webhook notification if configured
            trigger_webhook_notification(lawyer['id'], 'message_sent', {
                'client_phone_number': phone_number,
                'message': text,
                'timestamp': sh.datetime.datetime.now().isoformat()
            })
            
            print(f"--- [Lawyer API Task for {phone_number} Finished Successfully] ---")
            
        except Exception as e:
            print(f"--- [Lawyer API Task for {phone_number} FAILED] ---")
            print(f"   - Error: {e}")
        finally:
            if driver:
                print("   - Closing lawyer API browser session.")
                driver.quit()
            print("   Releasing lock.")

@lawyer_api.route('/conversations/<phone_number>', methods=['GET'])
def get_conversation_with_client(phone_number):
    """
    Get conversation history with a specific client.
    
    Headers:
        X-API-Key: <lawyer_api_key>
    
    Query params:
        count: Number of recent messages to retrieve (default: 20)
    """
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    count = request.args.get('count', 20, type=int)
    
    # Get conversation details
    contact_details = db.get_contact_details_by_phone(phone_number)
    if not contact_details:
        return jsonify({
            "status": "error",
            "message": "No conversation found with this phone number"
        }), 404
    
    # Get messages
    messages = list(db.get_last_messages(contact_details['title'], count=count))
    messages_list = [dict(msg) for msg in messages]
    
    return jsonify({
        "status": "success",
        "phone_number": phone_number,
        "contact_name": contact_details['title'],
        "messages": messages_list,
        "count": len(messages_list)
    }), 200

@lawyer_api.route('/webhooks', methods=['POST'])
def register_webhook():
    """
    Register a webhook for the authenticated lawyer.
    
    Headers:
        X-API-Key: <lawyer_api_key>
    
    Body:
        {
            "url": "https://your-app.com/webhook",
            "event_type": "message_received"
        }
    """
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    data = request.json
    url = data.get('url')
    event_type = data.get('event_type', 'message_received')
    
    if not url:
        return jsonify({"status": "error", "message": "Missing required field: url"}), 400
    
    webhook_id = ldi.register_webhook(lawyer['id'], url, event_type)
    
    return jsonify({
        "status": "success",
        "message": "Webhook registered successfully",
        "webhook_id": webhook_id
    }), 201

@lawyer_api.route('/webhooks', methods=['GET'])
def get_my_webhooks():
    """
    Get all webhooks for the authenticated lawyer.
    
    Headers:
        X-API-Key: <lawyer_api_key>
    """
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    webhooks = ldi.get_lawyer_webhooks(lawyer['id'])
    
    return jsonify({
        "status": "success",
        "webhooks": webhooks,
        "count": len(webhooks)
    }), 200

def trigger_webhook_notification(lawyer_id, event_type, payload):
    """
    Trigger webhook notifications for a specific event.
    
    Args:
        lawyer_id: Lawyer's ID
        event_type: Type of event
        payload: Event data
    """
    try:
        webhooks = ldi.get_lawyer_webhooks(lawyer_id, event_type=event_type)
        
        for webhook in webhooks:
            # Queue the notification for async processing
            ldi.queue_webhook_notification(webhook['id'], {
                'event_type': event_type,
                'data': payload,
                'lawyer_id': lawyer_id
            })
            
            # Start a background thread to send the webhook
            threading.Thread(
                target=send_webhook,
                args=(webhook['url'], payload)
            ).start()
            
    except Exception as e:
        print(f"⚠️ Failed to trigger webhook notification: {e}")

def send_webhook(url, payload):
    """
    Send webhook notification to a URL.
    
    Args:
        url: Webhook URL
        payload: JSON payload
    """
    import requests
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        print(f"✅ Webhook sent successfully to {url}")
    except Exception as e:
        print(f"❌ Failed to send webhook to {url}: {e}")
