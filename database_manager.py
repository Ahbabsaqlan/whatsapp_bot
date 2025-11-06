# database_manager.py

import sqlite3
import datetime
import re

DB_NAME = "whatsapp_archive.db"

def normalize_phone_number(phone_number_str):
    if not phone_number_str: return None
    digits = re.sub(r'[^\d+]', '', phone_number_str)
    if len(digits) == 11 and digits.startswith('01'): return f"+880{digits[1:]}"
    if len(digits) > 11 and digits.startswith('880'): return f"+{digits}"
    if digits.startswith('+'): return digits
    return phone_number_str

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, phone_number TEXT, created TEXT NOT NULL,
        updated TEXT NOT NULL, context_summary TEXT, size INTEGER DEFAULT 0
    );
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_title_no_phone ON Conversations (title) WHERE phone_number IS NULL;")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_number ON Conversations (phone_number) WHERE phone_number IS NOT NULL;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        content TEXT NOT NULL,
        message_index INTEGER NOT NULL,
        sending_date TEXT NOT NULL,
        stored_date TEXT NOT NULL,
        meta_text TEXT UNIQUE,
        attachment_filename TEXT, -- <-- NEW COLUMN
        FOREIGN KEY (conversation_id) REFERENCES Conversations (id)
    );
    """)
    conn.commit()
    conn.close()
    print("🗄️ Database initialized successfully with robust schema.")

def save_messages_to_db(contact_name, phone_number, new_messages):
    if not new_messages:
        print(f"✔️ No new messages to save for '{contact_name}'"); return

    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.now().isoformat()
    normalized_number = normalize_phone_number(phone_number)

    if normalized_number:
        cursor.execute("SELECT id, size FROM Conversations WHERE phone_number = ?", (normalized_number,))
    else:
        cursor.execute("SELECT id, size FROM Conversations WHERE title = ? AND phone_number IS NULL", (contact_name,))
    
    conversation = cursor.fetchone()
    if conversation:
        conversation_id, current_size = conversation['id'], conversation['size']
        cursor.execute("UPDATE Conversations SET updated = ?, title = ? WHERE id = ?", (now_iso, contact_name, conversation_id))
    else:
        cursor.execute("INSERT INTO Conversations (title, phone_number, created, updated) VALUES (?, ?, ?, ?)", (contact_name, normalized_number, now_iso, now_iso))
        conversation_id, current_size = cursor.lastrowid, 0
    
    messages_added = 0
    for idx, msg in enumerate(new_messages):
        role, sender_name = msg['role'], msg['sender']
        try:
            msg_datetime = datetime.datetime.strptime(f"{msg['date']} {msg['time']}", "%d/%m/%Y %I:%M %p")
            sending_date_iso = msg_datetime.isoformat()
        except (ValueError, KeyError, TypeError):
            sending_date_iso = datetime.datetime.now().isoformat()
        
        # --- NEW: Get the attachment filename from the parsed data ---
        attachment = msg.get('attachment_filename')

        # --- MODIFIED INSERT STATEMENT ---
        cursor.execute(
            """INSERT OR IGNORE INTO Messages (conversation_id, role, sender_name, content, message_index, 
               sending_date, stored_date, meta_text, attachment_filename) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, role, sender_name, msg['content'], current_size + messages_added + 1, 
             sending_date_iso, datetime.datetime.now().isoformat(), msg['meta_text'], attachment)
        )
        if cursor.rowcount > 0:
            messages_added += 1
            
    if messages_added > 0:
        new_total_size = current_size + messages_added
        cursor.execute("UPDATE Conversations SET size = ? WHERE id = ?", (new_total_size, conversation_id))
        summary = _generate_summary(cursor, conversation_id)
        cursor.execute("UPDATE Conversations SET context_summary = ? WHERE id = ?", (summary, conversation_id))
        print(f"💾 Saved {messages_added} new messages for '{contact_name}' to the database.")
    else:
        print(f"✔️ No new, unique messages to save for '{contact_name}'") 
    conn.commit()
    conn.close()

def get_last_message_from_db(phone_number, title, your_name):
    normalized_number = normalize_phone_number(phone_number)
    conn = get_db_connection()
    cursor = conn.cursor()
    query, params = "", ()
    if normalized_number:
        query = "SELECT m.meta_text FROM Messages m JOIN Conversations c ON m.conversation_id = c.id WHERE c.phone_number = ? ORDER BY m.message_index DESC LIMIT 1"
        params = (normalized_number,)
    else:
        query = "SELECT m.meta_text FROM Messages m JOIN Conversations c ON m.conversation_id = c.id WHERE c.title = ? AND c.phone_number IS NULL ORDER BY m.message_index DESC LIMIT 1"
        params = (title,)
    try:
        cursor.execute(query, params)
        last_msg_row = cursor.fetchone()
        conn.close()
        return last_msg_row['meta_text'] if last_msg_row else None
    except sqlite3.OperationalError as e:
        print(f"⚠️ Database query failed: {e}. Returning None.")
        conn.close()
        return None



def _generate_summary(cursor, conversation_id):
    cursor.execute("SELECT content FROM Messages WHERE conversation_id = ? ORDER BY message_index ASC LIMIT 1", (conversation_id,))
    first_msg = cursor.fetchone()
    cursor.execute("SELECT content FROM Messages WHERE conversation_id = ? ORDER BY message_index DESC LIMIT 1", (conversation_id,))
    last_msg = cursor.fetchone()
    if not (first_msg and last_msg): return "Conversation has messages."
    first_content = first_msg['content'][:30] + '...' if len(first_msg['content']) > 30 else first_msg['content']
    last_content = last_msg['content'][:30] + '...' if len(last_msg['content']) > 30 else last_msg['content']
    total_size_query = cursor.execute("SELECT size FROM Conversations WHERE id = ?", (conversation_id,)).fetchone()
    total_size = total_size_query['size'] if total_size_query else 0
    return f"Start: '{first_content}' | End: '{last_content}' | Total: {total_size} msgs"


# --- API Functions ---
def get_summary_by_title(title):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT context_summary FROM Conversations WHERE title LIKE ?", (f'%{title}%',))
    result = cursor.fetchone()
    conn.close()
    return result['context_summary'] if result else "No conversation found."

def get_last_messages(title, count=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.role, m.content, m.sending_date FROM Messages m JOIN Conversations c ON m.conversation_id = c.id
        WHERE c.title LIKE ? ORDER BY m.message_index DESC LIMIT ?
    """, (f'%{title}%', count))
    messages = cursor.fetchall()
    conn.close()
    return reversed(messages)

def get_all_unreplied_conversations():
    """
    Retrieves conversations where the last message is from a 'user'.
    Crucially, it now fetches the actual 'sending_date' of that last message
    for accurate age-checking.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- MODIFIED QUERY: Fetches the actual sending_date of the last message ---
    cursor.execute("""
        SELECT 
            c.title, 
            c.phone_number, 
            (SELECT m.sending_date FROM Messages m WHERE m.conversation_id = c.id ORDER BY m.message_index DESC LIMIT 1) as last_message_date
        FROM Conversations c
        WHERE (SELECT m.role FROM Messages m WHERE m.conversation_id = c.id ORDER BY m.message_index DESC LIMIT 1) = 'user'
    """)
    conversations = cursor.fetchall()
    conn.close()
    return conversations

def get_recent_messages_for_prompt(phone_number, count=10):
    normalized_number = normalize_phone_number(phone_number)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.role, m.content FROM Messages m JOIN Conversations c ON m.conversation_id = c.id
        WHERE c.phone_number = ? ORDER BY m.message_index DESC LIMIT ?
    """, (normalized_number, count))
    messages = cursor.fetchall()
    conn.close()
    return reversed(messages)

def get_contact_details_by_phone(phone_number):
    """
    Finds a conversation and returns its title and the meta_text of the last message.
    This is what the scraper needs to know where to stop scrolling.
    """
    normalized_number = normalize_phone_number(phone_number)
    if not normalized_number: return None
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            c.title,
            (SELECT m.meta_text FROM Messages m WHERE m.conversation_id = c.id ORDER BY m.message_index DESC LIMIT 1) as last_meta_text
        FROM Conversations c
        WHERE c.phone_number = ?
    """
    cursor.execute(query, (normalized_number,))
    contact_data = cursor.fetchone()
    conn.close()
    if contact_data:
        return {"title": contact_data["title"], "last_meta_text": contact_data["last_meta_text"]}
    else:
        return None