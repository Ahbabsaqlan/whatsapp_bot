# Quick Start Guide - Lawyer Directory Integration

This guide will help you get the WhatsApp bot integrated with your lawyer directory web application in under 10 minutes.

## Prerequisites

- Python 3.7 or higher
- Google Chrome browser installed
- A lawyer directory web application (or the provided examples)

## Step 1: Install and Setup (2 minutes)

1. Clone and install dependencies:
```bash
git clone https://github.com/Ahbabsaqlan/whatsapp_bot.git
cd whatsapp_bot
pip install -r requirements.txt
```

2. Run the setup script:
```bash
python setup_lawyer_directory.py
```

3. Follow the prompts to create your first lawyer account:
   - Enter lawyer's name
   - Enter email
   - Enter phone number (format: +1234567890)
   - Enter WhatsApp display name
   - (Optional) Specify a custom profile path

4. **SAVE THE API KEY** displayed at the end - you'll need it!

Example output:
```
🔑 API KEY (save this securely):
   PkXStxJIFlsiEtvqJescABC123XYZ789...
```

## Step 2: Start the Server (1 minute)

```bash
python run_server.py
```

The server will start on http://localhost:5001

You should see:
```
🗄️ Database initialized successfully
🗄️ Lawyer directory database tables initialized successfully
 * Running on http://0.0.0.0:5001
```

## Step 3: Test the Integration (3 minutes)

### Option A: Using curl (Quick Test)

1. Test getting your lawyer profile:
```bash
curl -H "X-API-Key: YOUR_API_KEY_HERE" \
  http://localhost:5001/api/lawyer/lawyers/me
```

2. Add a test client:
```bash
curl -X POST http://localhost:5001/api/lawyer/clients \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "phone_number": "+1234567890",
    "email": "client@example.com"
  }'
```

3. Send a message (will open WhatsApp Web):
```bash
curl -X POST http://localhost:5001/api/lawyer/messages/send \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "client_phone_number": "+1234567890",
    "text": "Hello from the lawyer directory!"
  }'
```

**First time only**: WhatsApp Web will open and ask you to scan a QR code with your phone.

### Option B: Run Example Web App

**Flask Example:**
```bash
# In a new terminal (keep server running)
cd examples
python flask_integration.py
```

Visit: http://localhost:3000

**Node.js Example:**
```bash
cd examples
npm install express axios express-session body-parser
# Update the API key in nodejs_integration.js first!
node nodejs_integration.js
```

## Step 4: Integrate with Your App (4 minutes)

### For Web Applications

Add to your backend:

**Python/Django:**
```python
import requests

LAWYER_API_KEY = 'YOUR_API_KEY_HERE'
WHATSAPP_API = 'http://localhost:5001/api/lawyer'

def send_message_to_client(client_phone, message):
    response = requests.post(
        f'{WHATSAPP_API}/messages/send',
        json={
            'client_phone_number': client_phone,
            'text': message
        },
        headers={'X-API-Key': LAWYER_API_KEY}
    )
    return response.json()
```

**Node.js/Express:**
```javascript
const axios = require('axios');

const LAWYER_API_KEY = 'YOUR_API_KEY_HERE';
const WHATSAPP_API = 'http://localhost:5001/api/lawyer';

async function sendMessageToClient(clientPhone, message) {
    const response = await axios.post(
        `${WHATSAPP_API}/messages/send`,
        {
            client_phone_number: clientPhone,
            text: message
        },
        {
            headers: { 'X-API-Key': LAWYER_API_KEY }
        }
    );
    return response.data;
}
```

### Add Webhook for Real-time Messages

Register a webhook to receive incoming messages:

```bash
curl -X POST http://localhost:5001/api/lawyer/webhooks \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook/whatsapp",
    "event_type": "message_received"
  }'
```

Then in your app, create an endpoint to receive webhooks:

**Python/Flask:**
```python
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    data = request.json
    # Process incoming message
    client_phone = data['data']['client_phone_number']
    message = data['data']['message']
    
    # Store in your database, notify lawyer, etc.
    
    return jsonify({'status': 'ok'})
```

**Node.js/Express:**
```javascript
app.post('/webhook/whatsapp', (req, res) => {
    const { data } = req.body;
    const clientPhone = data.client_phone_number;
    const message = data.message;
    
    // Process the message
    
    res.json({ status: 'ok' });
});
```

## Common Use Cases

### 1. Client Sends Message → Lawyer Gets Notification

```
Client WhatsApp → WhatsApp Bot → Webhook → Your App → Email/SMS/Push to Lawyer
```

### 2. Lawyer Responds via Web Interface

```
Lawyer Web UI → Your Backend → WhatsApp Bot API → WhatsApp Web → Client
```

### 3. Automated Responses

```
Client WhatsApp → Webhook → Your App Logic → WhatsApp Bot API → Client
```

Example auto-response:
```python
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    data = request.json
    client_phone = data['data']['client_phone_number']
    
    # Auto-respond
    send_message_to_client(
        client_phone,
        "Thank you for your message. Your lawyer will respond shortly."
    )
    
    return jsonify({'status': 'ok'})
```

## Multiple Lawyers

To add more lawyers, run the setup script again:

```bash
python setup_lawyer_directory.py
```

Each lawyer gets:
- Unique API key
- Separate client list
- Own WhatsApp profile (optional)

For separate WhatsApp accounts per lawyer, specify a unique profile path during setup:
```
WhatsApp profile path: /path/to/profiles/lawyer2
```

## Troubleshooting

**Issue**: "Authentication required"
- **Fix**: Make sure you're sending the `X-API-Key` header with each request

**Issue**: Message not sending
- **Fix**: Ensure WhatsApp Web is logged in. The first message will open a browser to scan QR code

**Issue**: Webhook not receiving events
- **Fix**: Make sure your webhook URL is publicly accessible (use ngrok for local testing)

**Issue**: Can't scan QR code
- **Fix**: Check if Chrome is installed. The bot uses Chrome/Chromium to open WhatsApp Web

## Next Steps

- Read the [Full Integration Guide](LAWYER_DIRECTORY_INTEGRATION.md) for advanced features
- Check out the [examples](examples/) directory for complete implementations
- See the original [README.md](README.md) for WhatsApp bot configuration

## Support

- 📘 [Complete API Documentation](LAWYER_DIRECTORY_INTEGRATION.md)
- 💬 [GitHub Issues](https://github.com/Ahbabsaqlan/whatsapp_bot/issues)
- 📧 Check your server logs for detailed error messages

---

**Congratulations!** You now have a WhatsApp bot integrated with your lawyer directory. 🎉
