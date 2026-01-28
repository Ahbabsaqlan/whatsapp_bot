"""
Example: Node.js/Express Integration
Demonstrates how to integrate the WhatsApp bot into an Express-based lawyer directory.
"""

// Save this as: app.js

const express = require('express');
const axios = require('axios');
const session = require('express-session');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3000;

// Configuration
const WHATSAPP_BOT_URL = process.env.WHATSAPP_BOT_URL || 'http://localhost:5001';

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(session({
    secret: 'your-secret-key-change-this',
    resave: false,
    saveUninitialized: false
}));

// In production, store these in a database
const LAWYER_CREDENTIALS = {
    'lawyer1@example.com': {
        password: 'password123', // Use bcrypt in production!
        apiKey: 'your-lawyer-1-api-key'
    }
};

// Authentication middleware
const requireAuth = (req, res, next) => {
    if (!req.session.lawyerEmail) {
        return res.status(401).json({ error: 'Not authenticated' });
    }
    next();
};

// Helper function to make WhatsApp bot API requests
const whatsappRequest = async (method, endpoint, data = null, lawyerEmail = null) => {
    const lawyer = LAWYER_CREDENTIALS[lawyerEmail];
    if (!lawyer) {
        throw new Error('Lawyer not found');
    }

    const config = {
        method: method,
        url: `${WHATSAPP_BOT_URL}/api/lawyer${endpoint}`,
        headers: {
            'X-API-Key': lawyer.apiKey,
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        config.data = data;
    }

    try {
        const response = await axios(config);
        return response.data;
    } catch (error) {
        console.error('WhatsApp API Error:', error.message);
        throw error;
    }
};

// Routes

// Login
app.post('/api/auth/login', (req, res) => {
    const { email, password } = req.body;
    
    const lawyer = LAWYER_CREDENTIALS[email];
    if (lawyer && lawyer.password === password) {
        req.session.lawyerEmail = email;
        res.json({ success: true, message: 'Logged in successfully' });
    } else {
        res.status(401).json({ success: false, message: 'Invalid credentials' });
    }
});

// Logout
app.post('/api/auth/logout', (req, res) => {
    req.session.destroy();
    res.json({ success: true, message: 'Logged out successfully' });
});

// Get lawyer profile
app.get('/api/profile', requireAuth, async (req, res) => {
    try {
        const profile = await whatsappRequest('GET', '/lawyers/me', null, req.session.lawyerEmail);
        res.json(profile);
    } catch (error) {
        res.status(500).json({ error: 'Failed to get profile' });
    }
});

// Get all clients
app.get('/api/clients', requireAuth, async (req, res) => {
    try {
        const clients = await whatsappRequest('GET', '/clients', null, req.session.lawyerEmail);
        res.json(clients);
    } catch (error) {
        res.status(500).json({ error: 'Failed to get clients' });
    }
});

// Add a new client
app.post('/api/clients', requireAuth, async (req, res) => {
    const { name, phone_number, email } = req.body;
    
    if (!name || !phone_number) {
        return res.status(400).json({ error: 'Name and phone number are required' });
    }

    try {
        const result = await whatsappRequest('POST', '/clients', {
            name,
            phone_number,
            email
        }, req.session.lawyerEmail);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to add client' });
    }
});

// Get conversation with a client
app.get('/api/conversations/:phoneNumber', requireAuth, async (req, res) => {
    const { phoneNumber } = req.params;
    const count = req.query.count || 50;

    try {
        const conversation = await whatsappRequest(
            'GET',
            `/conversations/${phoneNumber}?count=${count}`,
            null,
            req.session.lawyerEmail
        );
        res.json(conversation);
    } catch (error) {
        res.status(500).json({ error: 'Failed to get conversation' });
    }
});

// Send message to client
app.post('/api/messages/send', requireAuth, async (req, res) => {
    const { client_phone_number, text, file_path } = req.body;
    
    if (!client_phone_number || (!text && !file_path)) {
        return res.status(400).json({ 
            error: 'client_phone_number and either text or file_path are required' 
        });
    }

    try {
        const result = await whatsappRequest('POST', '/messages/send', {
            client_phone_number,
            text,
            file_path
        }, req.session.lawyerEmail);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to send message' });
    }
});

// Register webhook
app.post('/api/webhooks', requireAuth, async (req, res) => {
    const { url, event_type } = req.body;
    
    if (!url) {
        return res.status(400).json({ error: 'Webhook URL is required' });
    }

    try {
        const result = await whatsappRequest('POST', '/webhooks', {
            url,
            event_type: event_type || 'message_received'
        }, req.session.lawyerEmail);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to register webhook' });
    }
});

// Get webhooks
app.get('/api/webhooks', requireAuth, async (req, res) => {
    try {
        const webhooks = await whatsappRequest('GET', '/webhooks', null, req.session.lawyerEmail);
        res.json(webhooks);
    } catch (error) {
        res.status(500).json({ error: 'Failed to get webhooks' });
    }
});

// Webhook receiver endpoint (no auth required, as it's called by WhatsApp bot)
app.post('/webhook/whatsapp', (req, res) => {
    const { event_type, data, lawyer_id } = req.body;
    
    console.log(`Received webhook: ${event_type}`);
    console.log('Data:', data);
    
    // In production:
    // 1. Verify webhook signature/secret
    // 2. Store message in your database
    // 3. Send real-time notification to lawyer (WebSocket, SSE, etc.)
    // 4. Trigger any auto-responses or workflows
    
    // Example: Emit to WebSocket clients
    // io.to(`lawyer_${lawyer_id}`).emit('new_message', data);
    
    res.status(200).json({ status: 'ok' });
});

// Serve static files (your frontend)
app.use(express.static('public'));

// Start server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log(`WhatsApp Bot URL: ${WHATSAPP_BOT_URL}`);
});

/*
To use this example:

1. Install dependencies:
   npm install express axios express-session body-parser

2. Create a .env file:
   WHATSAPP_BOT_URL=http://localhost:5001
   PORT=3000

3. Run:
   node app.js

4. Test with curl:
   # Login
   curl -X POST http://localhost:3000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"lawyer1@example.com","password":"password123"}' \
     -c cookies.txt

   # Get clients
   curl http://localhost:3000/api/clients -b cookies.txt

   # Send message
   curl -X POST http://localhost:3000/api/messages/send \
     -H "Content-Type: application/json" \
     -d '{"client_phone_number":"+1234567890","text":"Hello from Node.js!"}' \
     -b cookies.txt
*/
