"""
Example: Flask Web Application Integration
Demonstrates how to integrate the WhatsApp bot into a Flask-based lawyer directory.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# WhatsApp Bot API Configuration
WHATSAPP_BOT_URL = os.environ.get('WHATSAPP_BOT_URL', 'http://localhost:5001')

# In production, store these in a database
# For this example, we'll use a simple dict
LAWYER_API_KEYS = {
    'lawyer1@example.com': 'your-lawyer-1-api-key',
    'lawyer2@example.com': 'your-lawyer-2-api-key',
}

def get_lawyer_api_key():
    """Get the current logged-in lawyer's API key"""
    lawyer_email = session.get('lawyer_email')
    if not lawyer_email:
        return None
    return LAWYER_API_KEYS.get(lawyer_email)

def make_whatsapp_request(method, endpoint, data=None, params=None):
    """Helper function to make requests to WhatsApp bot API"""
    api_key = get_lawyer_api_key()
    if not api_key:
        return None
    
    url = f"{WHATSAPP_BOT_URL}/api/lawyer{endpoint}"
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    if method == 'GET':
        response = requests.get(url, headers=headers, params=params)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return response.json() if response.ok else None

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if 'lawyer_email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # In production, verify password from database
        if email in LAWYER_API_KEYS:
            session['lawyer_email'] = email
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.pop('lawyer_email', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Lawyer dashboard - shows client list"""
    if 'lawyer_email' not in session:
        return redirect(url_for('login'))
    
    # Get lawyer profile
    profile = make_whatsapp_request('GET', '/lawyers/me')
    
    # Get all clients
    clients_data = make_whatsapp_request('GET', '/clients')
    clients = clients_data.get('clients', []) if clients_data else []
    
    return render_template('dashboard.html', 
                         lawyer=profile.get('lawyer') if profile else {},
                         clients=clients)

@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    """Add a new client"""
    if 'lawyer_email' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        result = make_whatsapp_request('POST', '/clients', {
            'name': name,
            'phone_number': phone,
            'email': email
        })
        
        if result and result.get('status') == 'success':
            return redirect(url_for('dashboard'))
        else:
            return render_template('add_client.html', error='Failed to add client')
    
    return render_template('add_client.html')

@app.route('/chat/<phone_number>')
def chat(phone_number):
    """Chat interface with a specific client"""
    if 'lawyer_email' not in session:
        return redirect(url_for('login'))
    
    # Get conversation history
    conversation = make_whatsapp_request('GET', f'/conversations/{phone_number}', 
                                        params={'count': 50})
    
    if not conversation:
        return "Conversation not found", 404
    
    return render_template('chat.html',
                         phone_number=phone_number,
                         contact_name=conversation.get('contact_name', 'Unknown'),
                         messages=conversation.get('messages', []))

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """API endpoint to send a message"""
    if 'lawyer_email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    phone_number = data.get('phone_number')
    text = data.get('text')
    
    if not phone_number or not text:
        return jsonify({'error': 'Missing phone_number or text'}), 400
    
    result = make_whatsapp_request('POST', '/messages/send', {
        'client_phone_number': phone_number,
        'text': text
    })
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Webhook endpoint to receive WhatsApp messages"""
    data = request.json
    
    event_type = data.get('event_type')
    message_data = data.get('data')
    lawyer_id = data.get('lawyer_id')
    
    print(f"Received webhook: {event_type}")
    print(f"Data: {message_data}")
    
    # In production:
    # 1. Store message in your database
    # 2. Send real-time notification to lawyer (WebSocket, SSE, etc.)
    # 3. Trigger any auto-responses or workflows
    
    # Example: Store in database (pseudo-code)
    # db.messages.create({
    #     'lawyer_id': lawyer_id,
    #     'client_phone': message_data.get('client_phone_number'),
    #     'content': message_data.get('message'),
    #     'timestamp': message_data.get('timestamp'),
    #     'direction': 'incoming'
    # })
    
    return jsonify({'status': 'ok'}), 200

@app.route('/settings/webhooks', methods=['GET', 'POST'])
def manage_webhooks():
    """Manage webhook settings"""
    if 'lawyer_email' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        webhook_url = request.form.get('webhook_url')
        event_type = request.form.get('event_type', 'message_received')
        
        result = make_whatsapp_request('POST', '/webhooks', {
            'url': webhook_url,
            'event_type': event_type
        })
        
        if result and result.get('status') == 'success':
            return redirect(url_for('manage_webhooks'))
    
    # Get existing webhooks
    webhooks_data = make_whatsapp_request('GET', '/webhooks')
    webhooks = webhooks_data.get('webhooks', []) if webhooks_data else []
    
    return render_template('webhooks.html', webhooks=webhooks)

# Simple HTML templates (in production, create separate template files)

@app.route('/templates/login.html')
def template_login():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lawyer Login</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; }
            input { width: 100%; padding: 10px; margin: 5px 0; }
            button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <h1>Lawyer Login</h1>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    '''

if __name__ == '__main__':
    # In production, use a proper WSGI server
    app.run(debug=True, port=3000)
