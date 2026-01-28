# Integration Examples

This directory contains example code showing how to integrate the WhatsApp bot into various web application frameworks for lawyer directory use cases.

## Available Examples

### 1. Flask Integration (`flask_integration.py`)

A complete Flask web application example showing:
- Lawyer authentication
- Client management
- Chat interface
- Message sending
- Webhook handling

**To run:**
```bash
pip install flask requests
python flask_integration.py
```

Then visit: http://localhost:3000

### 2. Node.js/Express Integration (`nodejs_integration.js`)

An Express.js backend example showing:
- RESTful API endpoints
- Session management
- WhatsApp bot integration
- Webhook receiver

**To run:**
```bash
npm install express axios express-session body-parser
node nodejs_integration.js
```

Then test with curl or your frontend.

## Usage Notes

1. **Update API Keys**: Replace placeholder API keys with actual keys from lawyer accounts
2. **Configure URLs**: Update `WHATSAPP_BOT_URL` to point to your running WhatsApp bot server
3. **Security**: These are examples - add proper authentication, validation, and error handling for production
4. **Database**: In production, store lawyer credentials and API keys in a proper database

## Integration Steps

1. Start the WhatsApp bot server:
   ```bash
   python run_server.py
   ```

2. Create a lawyer account:
   ```bash
   python setup_lawyer_directory.py
   ```
   Save the API key provided.

3. Update the example code with the API key

4. Run your web application

5. Use the API endpoints to:
   - Add clients
   - Send messages
   - View conversations
   - Receive webhook notifications

## More Information

See the main [Lawyer Directory Integration Guide](../LAWYER_DIRECTORY_INTEGRATION.md) for:
- Complete API reference
- Architecture details
- Deployment guide
- Troubleshooting

## Support

For issues or questions, refer to the main documentation or check the server logs for detailed error messages.
