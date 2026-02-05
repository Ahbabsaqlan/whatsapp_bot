# Security Considerations

This document outlines security best practices for deploying the WhatsApp bot in production environments.

## ⚠️ Important Notice

The example code in the `examples/` directory is **for demonstration purposes only**. It includes several security shortcuts that are **NOT suitable for production use**.

## Production Security Checklist

### 1. Authentication & Authorization

#### API Key Management
- ✅ Store API keys in environment variables, never in code
- ✅ Use a secrets management system (AWS Secrets Manager, HashiCorp Vault, etc.)
- ✅ Rotate API keys periodically
- ✅ Implement API key expiration
- ✅ Log all API key usage for audit trails

#### Password Security
```python
# ❌ NEVER do this (from examples)
if password == 'password123':
    login_user()

# ✅ DO this instead
from werkzeug.security import check_password_hash
if check_password_hash(stored_hash, password):
    login_user()
```

#### Lawyer Account Creation
The `/api/lawyer/lawyers` endpoint creates new accounts without authentication. In production:

1. **Protect this endpoint** with admin authentication
2. **Use invitation tokens** that expire after use
3. **Implement email verification** before activation
4. **Add rate limiting** to prevent abuse

Example protection:
```python
@lawyer_api.route('/lawyers', methods=['POST'])
def create_lawyer():
    # Verify admin token
    admin_token = request.headers.get('X-Admin-Token')
    if not verify_admin_token(admin_token):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Or verify invitation code
    invite_code = data.get('invite_code')
    if not verify_and_consume_invite(invite_code):
        return jsonify({"error": "Invalid invitation code"}), 400
    
    # ... proceed with account creation
```

### 2. Webhook Security

Webhooks are currently **not authenticated** in the example code. This allows anyone to send fake messages to your application.

#### Implement Webhook Verification

**Option 1: Shared Secret**
```python
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    webhook_secret = request.headers.get('X-Webhook-Secret')
    expected_secret = os.environ.get('WEBHOOK_SECRET')
    
    if not secrets.compare_digest(webhook_secret or '', expected_secret or ''):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Process webhook...
```

**Option 2: HMAC Signature**
```python
import hmac
import hashlib

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Process webhook...
```

**Option 3: IP Whitelisting**
```python
ALLOWED_IPS = ['127.0.0.1', '10.0.0.0/8']

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    if request.remote_addr not in ALLOWED_IPS:
        return jsonify({'error': 'Unauthorized IP'}), 401
    
    # Process webhook...
```

### 3. Database Security

#### Connection Security
```python
# Ensure database files have proper permissions
import os
os.chmod('whatsapp_archive.db', 0o600)  # Owner read/write only
```

#### SQL Injection Prevention
The code uses parameterized queries (✅), which prevents SQL injection:
```python
# ✅ GOOD - Parameterized query
cursor.execute("SELECT * FROM Lawyers WHERE email = ?", (email,))

# ❌ NEVER do this
cursor.execute(f"SELECT * FROM Lawyers WHERE email = '{email}'")
```

#### Sensitive Data
- Consider encrypting phone numbers in the database
- Hash or tokenize client data if regulations require
- Implement data retention policies

### 4. Input Validation

All user inputs must be validated:

```python
def create_lawyer():
    data = request.json
    
    # Validate email format
    email = data.get('email', '').strip()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate phone number format
    phone = data.get('phone_number', '').strip()
    if not re.match(r'^\+[1-9]\d{1,14}$', phone):  # E.164 format
        return jsonify({'error': 'Invalid phone number format'}), 400
    
    # Sanitize name (prevent XSS)
    name = bleach.clean(data.get('name', '').strip())
    
    # ... proceed with creation
```

### 5. Session Security

#### Flask Example
```python
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    SESSION_COOKIE_SECURE=True,      # Require HTTPS
    SESSION_COOKIE_HTTPONLY=True,    # Prevent XSS
    SESSION_COOKIE_SAMESITE='Lax',   # Prevent CSRF
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1)
)
```

#### Express Example
```javascript
app.use(session({
    secret: process.env.SESSION_SECRET,
    cookie: {
        secure: true,        // Require HTTPS
        httpOnly: true,      // Prevent XSS
        sameSite: 'strict',  // Prevent CSRF
        maxAge: 3600000      // 1 hour
    },
    resave: false,
    saveUninitialized: false
}));

// Add CSRF protection
const csrf = require('csurf');
app.use(csrf());
```

### 6. Rate Limiting

Prevent abuse by implementing rate limiting:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/lawyer/messages/send', methods=['POST'])
@limiter.limit("10 per minute")  # Limit message sending
def send_message():
    # ... implementation
```

### 7. HTTPS/SSL

**Always use HTTPS in production:**

```bash
# Use a reverse proxy like Nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Or use a load balancer (AWS ALB, Cloudflare) to handle SSL termination.

### 8. Logging & Monitoring

Implement comprehensive logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Log security events
@lawyer_api.route('/lawyers/me')
def get_my_profile():
    lawyer = authenticate_lawyer(request)
    if not lawyer:
        logging.warning(f"Unauthorized access attempt from {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401
    
    logging.info(f"Profile accessed by lawyer {lawyer['id']}")
    # ... implementation
```

### 9. Error Handling

Never expose internal details in error messages:

```python
try:
    # ... operation
except Exception as e:
    # ❌ Don't expose internal errors
    # return jsonify({"error": str(e)}), 500
    
    # ✅ Log internally, return generic message
    logging.error(f"Error in operation: {e}", exc_info=True)
    return jsonify({"error": "An error occurred"}), 500
```

### 10. Dependency Security

Keep dependencies up to date:

```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip list --outdated
pip install -U package_name
```

### 11. Environment Variables

Never commit secrets to version control:

```bash
# .env file (add to .gitignore)
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://...
WEBHOOK_SECRET=your-webhook-secret
API_KEY_SALT=random-salt-for-api-keys
```

```python
# Load from environment
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable not set")
```

### 12. File Upload Security

If implementing file uploads for attachments:

```python
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    if file.tell() > MAX_FILE_SIZE:
        return jsonify({"error": "File too large"}), 400
    file.seek(0)
    
    # Sanitize filename
    filename = secure_filename(file.filename)
    
    # Save to secure location
    file.save(os.path.join(UPLOAD_FOLDER, filename))
```

## Security Audit Checklist

Before deploying to production, verify:

- [ ] All secrets are in environment variables or secrets manager
- [ ] All passwords are hashed with bcrypt/argon2
- [ ] API endpoints have proper authentication
- [ ] Webhook endpoints verify signatures/secrets
- [ ] HTTPS is enabled and enforced
- [ ] Rate limiting is configured
- [ ] Input validation is comprehensive
- [ ] Error messages don't expose internal details
- [ ] Logging captures security events
- [ ] Database has proper access controls
- [ ] File permissions are restrictive
- [ ] Dependencies are up to date
- [ ] CSRF protection is enabled
- [ ] Session cookies are secure
- [ ] No debug mode in production
- [ ] Security headers are set (HSTS, X-Frame-Options, etc.)

## Reporting Security Issues

If you discover a security vulnerability, please:
1. **DO NOT** open a public GitHub issue
2. Email the maintainers privately
3. Provide details of the vulnerability
4. Allow time for a fix before public disclosure

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Express Security Best Practices](https://expressjs.com/en/advanced/best-practice-security.html)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
