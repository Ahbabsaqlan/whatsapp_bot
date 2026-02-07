# bot_state.py
import threading

# Global State Dictionary
state = {
    "status": "BOOTING",      # BOOTING, IDLE, LOGIN_MODE, AUTHENTICATED
    "qr_code": None,          # Stores the Base64 QR image
    "driver": None,           # Holds the Selenium Driver instance
    "last_sync": 0
}

# A lock to ensure only one thread touches the browser at a time
BROWSER_LOCK = threading.Lock()