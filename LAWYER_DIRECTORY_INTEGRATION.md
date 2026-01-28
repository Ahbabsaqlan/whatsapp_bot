# Lawyer Directory Integration Guide

## Overview

This WhatsApp bot has been extended to support **multi-user lawyer-client communication** for lawyer directory web applications. The integration allows:

- **Multiple lawyers** to use the system with separate WhatsApp accounts
- **Client-lawyer relationship management**
- **Real-time webhook notifications** for message events
- **Secure API key authentication** for each lawyer

## Architecture

### Database Schema

The integration adds the following tables:

1. **Lawyers**: Stores lawyer profiles with authentication
2. **Clients**: Stores client information
3. **LawyerClientRelationships**: Maps lawyers to their clients
4. **Webhooks**: Stores webhook URLs for event notifications
5. **WebhookQueue**: Queues webhook notifications for reliable delivery

### Multi-User Support

Each lawyer gets:
- A unique API key for authentication
- A separate WhatsApp Web profile (optional)
- Their own client list
- Custom webhook endpoints

## Getting Started

### 1. Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Initialize the Database

The system automatically initializes all required tables when you start the server:

```bash
python run_server.py
```

Or initialize manually:
```python
import lawyer_directory_integration as ldi
ldi.init_lawyer_directory_db()
```

### 3. Create Lawyer Accounts

Create a lawyer account via API:

```bash
curl -X POST http://localhost:5001/api/lawyer/lawyers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@lawfirm.com",
    "phone_number": "+1234567890",
    "whatsapp_name": "John Doe - Attorney"
  }'
```

Response:
```json
{
  "status": "success",
  "message": "Lawyer account created successfully",
  "lawyer": {
    "id": 1,
    "name": "John Doe",
    "email": "john@lawfirm.com",
    "phone_number": "+1234567890",
    "whatsapp_name": "John Doe - Attorney",
    "api_key": "ABC123XYZ789..."
  }
}
```

**Important**: Save the `api_key` - you'll need it for all subsequent API calls.

### 4. Setup WhatsApp for Each Lawyer

#### Option A: Shared Browser Profile (Simpler)
All lawyers use the same WhatsApp Web session. This works if:
- Only one lawyer is active at a time
- Lawyers take turns using the system

#### Option B: Separate Browser Profiles (Recommended)
Each lawyer has their own WhatsApp Web session:

1. Create a profile directory for each lawyer:
```bash
mkdir -p /path/to/lawyer_profiles/john_doe
```

2. Update lawyer profile with the path:
```python
import lawyer_directory_integration as ldi
import database_manager as db

conn = db.get_db_connection()
cursor = conn.cursor()
cursor.execute(
    "UPDATE Lawyers SET profile_path = ? WHERE id = ?",
    ("/path/to/lawyer_profiles/john_doe", 1)
)
conn.commit()
conn.close()
```

3. Each lawyer scans their own QR code when first using the system

## API Reference

### Authentication

All lawyer-specific endpoints require authentication via API key:

```
Header: X-API-Key: <your_api_key>
```

### Endpoints

#### 1. Create Lawyer Account

**POST** `/api/lawyer/lawyers`

Creates a new lawyer account.

**Request:**
```json
{
  "name": "Jane Smith",
  "email": "jane@lawfirm.com",
  "phone_number": "+1234567890",
  "whatsapp_name": "Jane Smith - Legal Counsel",
  "profile_path": "/path/to/profile" // optional
}
```

**Response:**
```json
{
  "status": "success",
  "lawyer": {
    "id": 2,
    "api_key": "XYZ789ABC123..."
  }
}
```

---

#### 2. Get My Profile

**GET** `/api/lawyer/lawyers/me`

Get the authenticated lawyer's profile.

**Headers:**
```
X-API-Key: <your_api_key>
```

**Response:**
```json
{
  "status": "success",
  "lawyer": {
    "id": 1,
    "name": "John Doe",
    "email": "john@lawfirm.com",
    "phone_number": "+1234567890",
    "whatsapp_name": "John Doe - Attorney"
  }
}
```

---

#### 3. Create/Link Client

**POST** `/api/lawyer/clients`

Create a new client and link to your account.

**Headers:**
```
X-API-Key: <your_api_key>
```

**Request:**
```json
{
  "name": "Alice Johnson",
  "phone_number": "+1234567891",
  "email": "alice@example.com" // optional
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Client created and linked to your account",
  "client_id": 1,
  "relationship_id": 1
}
```

---

#### 4. Get My Clients

**GET** `/api/lawyer/clients`

Get all clients linked to your account.

**Headers:**
```
X-API-Key: <your_api_key>
```

**Query Parameters:**
- `status`: Filter by status (default: 'active')

**Response:**
```json
{
  "status": "success",
  "clients": [
    {
      "id": 1,
      "name": "Alice Johnson",
      "phone_number": "+1234567891",
      "email": "alice@example.com",
      "conversation_id": 123,
      "title": "Alice Johnson",
      "last_message_time": "2025-01-28T10:30:00",
      "message_count": 45
    }
  ],
  "count": 1
}
```

---

#### 5. Send Message to Client

**POST** `/api/lawyer/messages/send`

Send a WhatsApp message to a client.

**Headers:**
```
X-API-Key: <your_api_key>
```

**Request:**
```json
{
  "client_phone_number": "+1234567891",
  "text": "Hello Alice, your documents are ready.",
  "file_path": "/path/to/document.pdf" // optional
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Message sending task has been initiated."
}
```

**Note**: Message sending is asynchronous. The message will be sent in the background.

---

#### 6. Get Conversation with Client

**GET** `/api/lawyer/conversations/<phone_number>`

Get message history with a specific client.

**Headers:**
```
X-API-Key: <your_api_key>
```

**Query Parameters:**
- `count`: Number of recent messages (default: 20)

**Response:**
```json
{
  "status": "success",
  "phone_number": "+1234567891",
  "contact_name": "Alice Johnson",
  "messages": [
    {
      "role": "user",
      "content": "When can I pick up the documents?",
      "sending_date": "2025-01-28T10:25:00"
    },
    {
      "role": "assistant",
      "content": "They'll be ready by 3 PM today.",
      "sending_date": "2025-01-28T10:26:00"
    }
  ],
  "count": 2
}
```

---

#### 7. Register Webhook

**POST** `/api/lawyer/webhooks`

Register a webhook URL to receive real-time notifications.

**Headers:**
```
X-API-Key: <your_api_key>
```

**Request:**
```json
{
  "url": "https://your-app.com/webhook/whatsapp",
  "event_type": "message_received"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Webhook registered successfully",
  "webhook_id": 1
}
```

**Event Types:**
- `message_received`: Triggered when a client sends a message
- `message_sent`: Triggered when you send a message

**Webhook Payload Example:**
```json
{
  "event_type": "message_received",
  "data": {
    "client_phone_number": "+1234567891",
    "message": "Hello, I need legal advice",
    "timestamp": "2025-01-28T10:30:00"
  },
  "lawyer_id": 1
}
```

---

#### 8. Get My Webhooks

**GET** `/api/lawyer/webhooks`

List all registered webhooks.

**Headers:**
```
X-API-Key: <your_api_key>
```

**Response:**
```json
{
  "status": "success",
  "webhooks": [
    {
      "id": 1,
      "url": "https://your-app.com/webhook/whatsapp",
      "event_type": "message_received",
      "is_active": 1
    }
  ],
  "count": 1
}
```

---

## Integration Examples

### Example 1: Web Application Backend (Node.js/Express)

```javascript
const express = require('express');
const axios = require('axios');
const app = express();

// Your lawyer's API key
const WHATSAPP_API_KEY = 'ABC123XYZ789...';
const WHATSAPP_API_URL = 'http://localhost:5001/api/lawyer';

// Send message to client
app.post('/send-to-client', async (req, res) => {
  const { clientPhone, message } = req.body;
  
  try {
    const response = await axios.post(
      `${WHATSAPP_API_URL}/messages/send`,
      {
        client_phone_number: clientPhone,
        text: message
      },
      {
        headers: {
          'X-API-Key': WHATSAPP_API_KEY,
          'Content-Type': 'application/json'
        }
      }
    );
    
    res.json({ success: true, data: response.data });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Webhook endpoint to receive WhatsApp messages
app.post('/webhook/whatsapp', (req, res) => {
  const { event_type, data, lawyer_id } = req.body;
  
  console.log(`Received ${event_type} event:`, data);
  
  // Process the incoming message
  // - Store in your database
  // - Notify the lawyer via your app
  // - Trigger auto-responses
  
  res.status(200).send('OK');
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

### Example 2: Python/Django Backend

```python
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

WHATSAPP_API_KEY = 'ABC123XYZ789...'
WHATSAPP_API_URL = 'http://localhost:5001/api/lawyer'

def send_message_to_client(request):
    """Send WhatsApp message to client"""
    client_phone = request.POST.get('client_phone')
    message = request.POST.get('message')
    
    response = requests.post(
        f'{WHATSAPP_API_URL}/messages/send',
        json={
            'client_phone_number': client_phone,
            'text': message
        },
        headers={
            'X-API-Key': WHATSAPP_API_KEY,
            'Content-Type': 'application/json'
        }
    )
    
    return JsonResponse(response.json())

@csrf_exempt
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages"""
    if request.method == 'POST':
        data = json.loads(request.body)
        event_type = data.get('event_type')
        message_data = data.get('data')
        
        # Process the message
        # - Save to database
        # - Send notification to lawyer
        # - Auto-respond if needed
        
        return JsonResponse({'status': 'ok'})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

def get_client_messages(request, phone_number):
    """Get conversation history with a client"""
    response = requests.get(
        f'{WHATSAPP_API_URL}/conversations/{phone_number}',
        params={'count': 50},
        headers={'X-API-Key': WHATSAPP_API_KEY}
    )
    
    return JsonResponse(response.json())
```

### Example 3: React Frontend

```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const LawyerClientChat = ({ clientPhone }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  
  // Your backend API that proxies to WhatsApp bot
  const BACKEND_API = 'http://localhost:3000';
  
  useEffect(() => {
    // Load conversation history
    loadMessages();
    
    // Poll for new messages or use WebSocket
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, [clientPhone]);
  
  const loadMessages = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_API}/client-messages/${clientPhone}`
      );
      setMessages(response.data.messages);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };
  
  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    
    try {
      await axios.post(`${BACKEND_API}/send-to-client`, {
        clientPhone,
        message: newMessage
      });
      
      setNewMessage('');
      
      // Wait a bit then reload to show sent message
      setTimeout(loadMessages, 2000);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };
  
  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="content">{msg.content}</div>
            <div className="time">{msg.sending_date}</div>
          </div>
        ))}
      </div>
      
      <div className="input-area">
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type a message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
};

export default LawyerClientChat;
```

## Deployment Considerations

### 1. Multiple WhatsApp Profiles

For production with multiple lawyers, use separate Chrome profiles:

```python
# In your lawyer setup
import os

lawyer_id = 1
profile_path = f"/var/whatsapp/profiles/lawyer_{lawyer_id}"
os.makedirs(profile_path, exist_ok=True)

# Update in database
# Each lawyer will scan QR code once for their profile
```

### 2. Webhook Reliability

The system queues webhook notifications for reliability. For production:

1. Implement a webhook worker process
2. Add retry logic with exponential backoff
3. Monitor webhook queue for failures

### 3. Security

- **API Keys**: Store securely, never in client-side code
- **HTTPS**: Use HTTPS for webhook URLs
- **Rate Limiting**: Implement rate limiting on endpoints
- **Validation**: Validate all phone numbers and inputs

### 4. Scaling

For high-volume scenarios:

- Use a message queue (Redis, RabbitMQ) instead of threads
- Run multiple bot instances with load balancing
- Use a production WSGI server (Gunicorn, uWSGI)

Example with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5001 run_server:app
```

## Troubleshooting

### Issue: "Authentication required"
- Verify your API key is correct
- Check the `X-API-Key` header is being sent
- Ensure the lawyer account is active

### Issue: Message not sending
- Check WhatsApp Web is logged in for that lawyer's profile
- Verify the phone number format
- Check server logs for Selenium errors

### Issue: Webhook not receiving events
- Test webhook URL is accessible from the bot server
- Check webhook is registered and active
- Verify webhook URL uses HTTPS (for production)

### Issue: Multiple lawyers conflict
- Ensure each lawyer has a separate profile_path
- Only one lawyer should use the bot at a time (or use message queue)
- Check TASK_LOCK is properly preventing concurrent access

## Support

For issues or questions:
1. Check the main README.md for general WhatsApp bot issues
2. Review the API documentation above
3. Check server logs for detailed error messages
4. Ensure all dependencies are installed: `pip install -r requirements.txt`
