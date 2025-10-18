import sqlite3
import datetime

DB_NAME = "whatsapp_archive.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Conversations Table (unchanged)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        phone_number TEXT UNIQUE,
        created TEXT NOT NULL,
        updated TEXT NOT NULL,
        context_summary TEXT,
        size INTEGER DEFAULT 0
    );
    """)
    
    # --- MODIFIED: Messages Table now includes meta_text ---
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
    """Saves new messages to the database using meta_text to prevent duplicates."""
    if not new_messages:
        print(f"✔️ No new messages to save for '{contact_name}'")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()

    cursor.execute("SELECT id, size FROM Conversations WHERE phone_number = ?", (phone_number,))
    conversation = cursor.fetchone()
    
    if conversation:
        conversation_id, current_size = conversation['id'], conversation['size']
        cursor.execute("UPDATE Conversations SET updated = ? WHERE id = ?", (now, conversation_id))
    else:
        cursor.execute("INSERT INTO Conversations (title, phone_number, created, updated) VALUES (?, ?, ?, ?)", (contact_name, phone_number, now, now))
        conversation_id, current_size = cursor.lastrowid, 0
    
    # --- MODIFIED: Use INSERT OR IGNORE with unique meta_text ---
    messages_added = 0
    for idx, msg in enumerate(new_messages):
        role = "me" if msg['sender'] == your_name else "user"
        try:
            msg_datetime = datetime.datetime.strptime(f"{msg['date']} {msg['time']}", "%m/%d/%Y %I:%M %p")
            created_iso = msg_datetime.isoformat()
        except ValueError:
            created_iso = now

        # This will only insert if the meta_text is not already in the database.
        cursor.execute(
            "INSERT OR IGNORE INTO Messages (conversation_id, role, content, message_index, created_date, meta_text) VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, role, msg['content'], current_size + idx + 1, created_iso, msg['meta_text'])
        )
        if cursor.rowcount > 0:
            messages_added += 1
            
    # --- MODIFIED: Update conversation size and summary only if messages were added ---
    if messages_added > 0:
        new_total_size = current_size + messages_added
        summary = _generate_summary(cursor, conversation_id)
        cursor.execute("UPDATE Conversations SET size = ?, context_summary = ? WHERE id = ?", (new_total_size, summary, conversation_id))
        print(f"💾 Saved {messages_added} new messages for '{contact_name}' to the database.")
    else:
        print(f"✔️ No new messages to save for '{contact_name}'")

    conn.commit()
    conn.close()

def _generate_summary(cursor, conversation_id):
    """Helper to generate a context summary."""
    cursor.execute("SELECT content, size FROM Conversations c JOIN Messages m ON c.id = m.conversation_id WHERE c.id = ? ORDER BY m.message_index ASC LIMIT 1", (conversation_id,))
    first_msg = cursor.fetchone()
    cursor.execute("SELECT content FROM Messages WHERE conversation_id = ? ORDER BY message_index DESC LIMIT 1", (conversation_id,))
    last_msg = cursor.fetchone()
    if not (first_msg and last_msg): return "Conversation has messages."
    first_content = first_msg['content'][:30] + '...' if len(first_msg['content']) > 30 else first_msg['content']
    last_content = last_msg['content'][:30] + '...' if len(last_msg['content']) > 30 else last_msg['content']
    return f"Start: '{first_content}' | End: '{last_content}' | Total: {first_msg['size']} msgs"

# --- MODIFIED: This function is now simpler and more robust ---
def get_last_message_from_db(phone_number, your_name):
    """Retrieves the meta_text of the last stored message for a contact."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.meta_text FROM Messages m JOIN Conversations c ON m.conversation_id = c.id
        WHERE c.phone_number = ? ORDER BY m.message_index DESC LIMIT 1
    """, (phone_number,))
    last_msg_row = cursor.fetchone()
    conn.close()
    return last_msg_row['meta_text'] if last_msg_row else None


# --- API FUNCTIONS ---

def get_summary_by_title(title):
    """API: Get the context summary for a conversation by its title."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT context_summary FROM Conversations WHERE title LIKE ?", (f'%{title}%',))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result['context_summary']
    return "No conversation found with that title."

def get_last_messages(title, count=5):
    """API: Get the last N messages from a conversation by its title."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.role, m.content, m.created_date
        FROM Messages m
        JOIN Conversations c ON m.conversation_id = c.id
        WHERE c.title LIKE ?
        ORDER BY m.message_index DESC
        LIMIT ?
    """, (f'%{title}%', count))
    messages = cursor.fetchall()
    conn.close()
    return reversed(messages) # Return in chronological order

def get_all_unreplied_conversations():
    """
    API: Get all conversations where the last message was not from 'me'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # This query finds conversations where the role of the message with the highest index is not 'me'.
    cursor.execute("""
        SELECT c.title, c.phone_number, c.updated
        FROM Conversations c
        WHERE (
            SELECT m.role 
            FROM Messages m 
            WHERE m.conversation_id = c.id 
            ORDER BY m.message_index DESC 
            LIMIT 1
        ) = 'user'
    """)
    
    conversations = cursor.fetchall()
    conn.close()
    return conversations

# Add this new function at the end of database_manager.py

def get_recent_messages_for_prompt(phone_number, count=10):
    """
    Fetches the last 'count' messages for a conversation to be used as a prompt.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT m.role, m.content
        FROM Messages m
        JOIN Conversations c ON m.conversation_id = c.id
        WHERE c.phone_number = ?
        ORDER BY m.message_index DESC
        LIMIT ?
    """, (phone_number, count))
    
    messages = cursor.fetchall()
    conn.close()
    
    # The results are fetched in reverse order (newest first),
    # so we reverse them again to get chronological order for the prompt.
    return reversed(messages)