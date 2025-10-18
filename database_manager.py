import sqlite3
import datetime

DB_NAME = "whatsapp_archive.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        phone_number TEXT,
        created TEXT NOT NULL,
        updated TEXT NOT NULL,
        context_summary TEXT,
        size INTEGER DEFAULT 0
    );
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_title_no_phone ON Conversations (title) WHERE phone_number IS NULL;")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_number ON Conversations (phone_number) WHERE phone_number IS NOT NULL;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        message_index INTEGER NOT NULL,
        created_date TEXT NOT NULL,
        meta_text TEXT UNIQUE, 
        FOREIGN KEY (conversation_id) REFERENCES Conversations (id)
    );
    """)
    
    conn.commit()
    conn.close()
    print("🗄️ Database initialized successfully.")

def save_messages_to_db(contact_name, phone_number, new_messages, your_name):
    if not new_messages:
        print(f"✔️ No new messages to save for '{contact_name}'")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()

    if phone_number:
        cursor.execute("SELECT id, size FROM Conversations WHERE phone_number = ?", (phone_number,))
    else:
        cursor.execute("SELECT id, size FROM Conversations WHERE title = ? AND phone_number IS NULL", (contact_name,))
    
    conversation = cursor.fetchone()
    
    if conversation:
        conversation_id, current_size = conversation['id'], conversation['size']
        cursor.execute("UPDATE Conversations SET updated = ?, title = ? WHERE id = ?", (now, contact_name, conversation_id))
    else:
        cursor.execute("INSERT INTO Conversations (title, phone_number, created, updated) VALUES (?, ?, ?, ?)", (contact_name, phone_number, now, now))
        conversation_id, current_size = cursor.lastrowid, 0
    
    messages_added = 0
    for idx, msg in enumerate(new_messages):
        role = "me" if msg['sender'] == your_name else "user"
        try:
            msg_datetime = datetime.datetime.strptime(f"{msg['date']} {msg['time']}", "%m/%d/%Y %I:%M %p")
            created_iso = msg_datetime.isoformat()
        except ValueError:
            created_iso = now

        cursor.execute(
            "INSERT OR IGNORE INTO Messages (conversation_id, role, content, message_index, created_date, meta_text) VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, role, msg['content'], current_size + messages_added + 1, created_iso, msg['meta_text'])
        )
        if cursor.rowcount > 0:
            messages_added += 1
            
    if messages_added > 0:
        new_total_size = current_size + messages_added
        cursor.execute("UPDATE Conversations SET size = ? WHERE id = ?", (new_total_size, conversation_id))
        # Generate summary after updating the size
        summary = _generate_summary(cursor, conversation_id)
        cursor.execute("UPDATE Conversations SET context_summary = ? WHERE id = ?", (summary, conversation_id))
        print(f"💾 Saved {messages_added} new messages for '{contact_name}' to the database.")
    else:
        print(f"✔️ No new messages to save for '{contact_name}'")

    conn.commit()
    conn.close()

def _generate_summary(cursor, conversation_id):
    """Helper to generate a context summary."""
    # This query for the first message works fine.
    cursor.execute("SELECT content FROM Messages WHERE conversation_id = ? ORDER BY message_index ASC LIMIT 1", (conversation_id,))
    first_msg = cursor.fetchone()
    
    # --- THIS QUERY IS NOW CORRECT ---
    # The previous version had an incorrect 'm.' alias. This is the fix.
    cursor.execute("SELECT content FROM Messages WHERE conversation_id = ? ORDER BY message_index DESC LIMIT 1", (conversation_id,))
    last_msg = cursor.fetchone()

    if not (first_msg and last_msg): return "Conversation has messages."

    first_content = first_msg['content'][:30] + '...' if len(first_msg['content']) > 30 else first_msg['content']
    last_content = last_msg['content'][:30] + '...' if len(last_msg['content']) > 30 else last_msg['content']
    
    total_size_query = cursor.execute("SELECT size FROM Conversations WHERE id = ?", (conversation_id,)).fetchone()
    total_size = total_size_query['size'] if total_size_query else 0
    
    return f"Start: '{first_content}' | End: '{last_content}' | Total: {total_size} msgs"

def get_last_message_from_db(phone_number, title, your_name):
    """Retrieves the meta_text of the last stored message for a contact."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = ""
    params = ()
    if phone_number:
        query = "SELECT m.meta_text FROM Messages m JOIN Conversations c ON m.conversation_id = c.id WHERE c.phone_number = ? ORDER BY m.message_index DESC LIMIT 1"
        params = (phone_number,)
    else:
        query = "SELECT m.meta_text FROM Messages m JOIN Conversations c ON m.conversation_id = c.id WHERE c.title = ? AND c.phone_number IS NULL ORDER BY m.message_index DESC LIMIT 1"
        params = (title,)

    try:
        cursor.execute(query, params)
        last_msg_row = cursor.fetchone()
        conn.close()
        return last_msg_row['meta_text'] if last_msg_row else None
    except sqlite3.OperationalError as e:
        # This will catch 'no such table' errors if the DB is in a bad state.
        print(f"⚠️ Database query failed in get_last_message_from_db: {e}. Returning None to allow full scrape.")
        conn.close()
        return None

# --- API Functions ---
def get_summary_by_title(title):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT context_summary FROM Conversations WHERE title LIKE ?", (f'%{title}%',))
    result = cursor.fetchone()
    conn.close()
    return result['context_summary'] if result else "No conversation found with that title."

def get_last_messages(title, count=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.role, m.content, m.created_date FROM Messages m JOIN Conversations c ON m.conversation_id = c.id
        WHERE c.title LIKE ? ORDER BY m.message_index DESC LIMIT ?
    """, (f'%{title}%', count))
    messages = cursor.fetchall()
    conn.close()
    return reversed(messages)

def get_all_unreplied_conversations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.title, c.phone_number, c.updated FROM Conversations c
        WHERE (SELECT m.role FROM Messages m WHERE m.conversation_id = c.id ORDER BY m.message_index DESC LIMIT 1) = 'user'
    """)
    conversations = cursor.fetchall()
    conn.close()
    return conversations

def get_recent_messages_for_prompt(phone_number, count=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.role, m.content FROM Messages m JOIN Conversations c ON m.conversation_id = c.id
        WHERE c.phone_number = ? ORDER BY m.message_index DESC LIMIT ?
    """, (phone_number, count))
    messages = cursor.fetchall()
    conn.close()
    return reversed(messages)