# controller.py
import requests
import json

API_BASE_URL = "http://127.0.0.1:5001"

def init_db():
    """Calls the API to initialize the database."""
    try:
        response = requests.post(f"{API_BASE_URL}/init_db")
        response.raise_for_status()
        print("🗄️ Database initialized successfully via API.")
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: Could not initialize database. Is the server running? Error: {e}")

def save_messages_to_db(contact_name, phone_number, new_messages):
    """Calls the API to save new messages."""
    if not new_messages:
        return
    payload = {
        "contact_name": contact_name,
        "phone_number": phone_number,
        "new_messages": new_messages
    }
    try:
        response = requests.post(f"{API_BASE_URL}/messages", json=payload)
        response.raise_for_status()
        print(f"📡 Sent {len(new_messages)} messages for '{contact_name}' to API for saving.")
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: Could not save messages for '{contact_name}'. Error: {e}")

def get_last_message_from_db(phone_number, title, your_name):
    """Calls the API to get the last message's meta_text."""
    params = {
        "phone_number": phone_number,
        "title": title,
        "your_name": your_name
    }
    try:
        response = requests.get(f"{API_BASE_URL}/last_message", params=params)
        response.raise_for_status()
        return response.json().get('meta_text')
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: Could not get last message for '{title}'. Error: {e}")
        return None


def get_contact_details(phone_number):
    """Calls the API to get a contact's title and last message bookmark."""
    try:
        params = {"phone_number": phone_number}
        response = requests.get(f"{API_BASE_URL}/contact-details", params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"API Info: Contact with number {phone_number} is new to the database.")
            return None
        else:
            response.raise_for_status()
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: Could not get contact details. Error: {e}")
        return None

def send_message_via_api(phone_number, text=None, file_path=None):
    """
    Calls the main API endpoint to trigger a send process for either text or a file.
    """
    if not text and not file_path:
        print("❌ Error: You must provide either text or a file_path to send.")
        return False

    try:
        payload = {
            "phone_number": phone_number,
            "text": text,         # Will be used as caption if file_path is present
            "file_path": file_path
        }
        response = requests.post(f"{API_BASE_URL}/send-message", json=payload, timeout=10)
        
        if response.status_code != 202:
             print(f"❌ API Error: Server responded with status {response.status_code}. Message: {response.text}")
             return False

        print(f"\n✅ API request accepted. The server will now handle the sending process.")
        print("   (Check the server's terminal window for real-time progress).")
        return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Connection Error: Could not connect to the server.")
        print(f"   Please ensure the main script is running. Error: {e}")
        return False

def get_prompt_history(phone_number, count=15):
    """Calls the API to get the recent message history for a contact."""
    try:
        params = {"phone_number": phone_number, "count": count}
        response = requests.get(f"{API_BASE_URL}/prompt_history", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: Could not get prompt history for '{phone_number}'. Error: {e}")
        return None
    
# --- API Tool Functions ---
def get_summary_by_title(title):
    try:
        response = requests.get(f"{API_BASE_URL}/summary", params={'title': title})
        response.raise_for_status()
        return response.json().get('summary', "No summary found.")
    except requests.exceptions.RequestException as e:
        return f"API Error: {e}"

def get_last_messages(title, count=5):
    try:
        response = requests.get(f"{API_BASE_URL}/messages", params={'title': title, 'count': count})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return []

def get_all_unreplied_conversations():
    try:
        response = requests.get(f"{API_BASE_URL}/unreplied")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return []