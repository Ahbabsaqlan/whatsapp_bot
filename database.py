import sqlite3
import datetime

DB_NAME = "whatsapp_log.db"

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table to store unique contacts and their aliases
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            alias TEXT
        )
    ''')
    
    # Table to store all messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            sender_name TEXT,
            message_text TEXT,
            timestamp TEXT,
            is_from_me BOOLEAN,
            needs_reply BOOLEAN,
            FOREIGN KEY(contact_id) REFERENCES contacts(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def get_or_create_contact(name):
    """Finds a contact by name or creates a new one. Returns the contact ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM contacts WHERE name = ?", (name,))
    result = cursor.fetchone()
    
    if result:
        contact_id = result[0]
    else:
        cursor.execute("INSERT INTO contacts (name) VALUES (?)", (name,))
        contact_id = cursor.lastrowid
        print(f"New contact '{name}' added to database.")
    
    conn.commit()
    conn.close()
    return contact_id

def log_message(contact_id, sender_name, text, is_from_me=False):
    """Logs a message to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Incoming messages need a reply
    needs_reply = not is_from_me
    
    cursor.execute('''
        INSERT INTO messages (contact_id, sender_name, message_text, timestamp, is_from_me, needs_reply)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (contact_id, sender_name, text, timestamp, is_from_me, needs_reply))
    
    conn.commit()
    conn.close()

def check_if_message_exists(contact_id, message_text):
    """Checks if an identical message from a contact already exists to avoid duplicates."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM messages 
        WHERE contact_id = ? AND message_text = ? AND is_from_me = 0
    ''', (contact_id, message_text))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_chats_needing_reply():
    """Gets a list of contact names that have messages needing a reply."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT c.name FROM contacts c
        JOIN messages m ON c.id = m.contact_id
        WHERE m.needs_reply = 1
    ''')
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results

def mark_chat_as_replied(contact_name):
    """Marks all messages from a specific contact as not needing a reply."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE messages SET needs_reply = 0
        WHERE contact_id = (SELECT id FROM contacts WHERE name = ?)
    ''', (contact_name,))
    conn.commit()
    conn.close()
    print(f"Marked chat with '{contact_name}' as replied.")