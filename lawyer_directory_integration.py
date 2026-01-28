# lawyer_directory_integration.py
"""
This module extends the WhatsApp bot for lawyer directory integration.
It adds multi-user support, lawyer-client relationships, and webhook notifications.
"""

import sqlite3
import datetime
import hashlib
import secrets
from database_manager import get_db_connection, normalize_phone_number

def init_lawyer_directory_db():
    """
    Initialize additional database tables for lawyer directory integration.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lawyers table - stores lawyer profiles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Lawyers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        whatsapp_name TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        profile_path TEXT,
        is_active INTEGER DEFAULT 1,
        created TEXT NOT NULL,
        updated TEXT NOT NULL
    );
    """)
    
    # Clients table - stores client information
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        email TEXT,
        created TEXT NOT NULL,
        updated TEXT NOT NULL
    );
    """)
    
    # Lawyer-Client relationships
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS LawyerClientRelationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lawyer_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        conversation_id INTEGER,
        status TEXT DEFAULT 'active',
        created TEXT NOT NULL,
        updated TEXT NOT NULL,
        FOREIGN KEY (lawyer_id) REFERENCES Lawyers (id),
        FOREIGN KEY (client_id) REFERENCES Clients (id),
        FOREIGN KEY (conversation_id) REFERENCES Conversations (id),
        UNIQUE (lawyer_id, client_id)
    );
    """)
    
    # Webhooks table - for callback notifications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Webhooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lawyer_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        event_type TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created TEXT NOT NULL,
        FOREIGN KEY (lawyer_id) REFERENCES Lawyers (id)
    );
    """)
    
    # Message queue for webhook notifications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS WebhookQueue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        webhook_id INTEGER NOT NULL,
        payload TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created TEXT NOT NULL,
        last_attempt TEXT,
        FOREIGN KEY (webhook_id) REFERENCES Webhooks (id)
    );
    """)
    
    conn.commit()
    conn.close()
    print("🗄️ Lawyer directory database tables initialized successfully.")

def generate_api_key():
    """Generate a secure API key for a lawyer."""
    return secrets.token_urlsafe(32)

def create_lawyer(name, email, phone_number, whatsapp_name, profile_path=None):
    """
    Create a new lawyer account.
    
    Args:
        name: Lawyer's full name
        email: Lawyer's email address
        phone_number: Lawyer's phone number
        whatsapp_name: Name as it appears in WhatsApp
        profile_path: Optional path to WhatsApp profile directory
        
    Returns:
        Dictionary with lawyer data including API key, or None if failed
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.now().isoformat()
    normalized_number = normalize_phone_number(phone_number)
    api_key = generate_api_key()
    
    try:
        cursor.execute("""
            INSERT INTO Lawyers (name, email, phone_number, whatsapp_name, api_key, profile_path, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, normalized_number, whatsapp_name, api_key, profile_path, now_iso, now_iso))
        
        lawyer_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Created lawyer account: {name} (ID: {lawyer_id})")
        return {
            "id": lawyer_id,
            "name": name,
            "email": email,
            "phone_number": normalized_number,
            "whatsapp_name": whatsapp_name,
            "api_key": api_key,
            "profile_path": profile_path
        }
    except sqlite3.IntegrityError as e:
        print(f"❌ Failed to create lawyer: {e}")
        return None
    finally:
        conn.close()

def get_lawyer_by_api_key(api_key):
    """Get lawyer information by API key."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Lawyers WHERE api_key = ? AND is_active = 1", (api_key,))
    lawyer = cursor.fetchone()
    conn.close()
    
    return dict(lawyer) if lawyer else None

def get_lawyer_by_id(lawyer_id):
    """Get lawyer information by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Lawyers WHERE id = ? AND is_active = 1", (lawyer_id,))
    lawyer = cursor.fetchone()
    conn.close()
    
    return dict(lawyer) if lawyer else None

def create_or_get_client(name, phone_number, email=None):
    """
    Create a new client or get existing client.
    
    Args:
        name: Client's name
        phone_number: Client's phone number
        email: Optional client email
        
    Returns:
        Client ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.now().isoformat()
    normalized_number = normalize_phone_number(phone_number)
    
    # Check if client exists
    cursor.execute("SELECT id FROM Clients WHERE phone_number = ?", (normalized_number,))
    existing = cursor.fetchone()
    
    if existing:
        client_id = existing['id']
        # Update name if provided
        cursor.execute("UPDATE Clients SET name = ?, updated = ?, email = COALESCE(?, email) WHERE id = ?", 
                      (name, now_iso, email, client_id))
    else:
        cursor.execute("""
            INSERT INTO Clients (name, phone_number, email, created, updated)
            VALUES (?, ?, ?, ?, ?)
        """, (name, normalized_number, email, now_iso, now_iso))
        client_id = cursor.lastrowid
        print(f"✅ Created client: {name} (ID: {client_id})")
    
    conn.commit()
    conn.close()
    return client_id

def link_lawyer_client(lawyer_id, client_id, conversation_id=None):
    """
    Create or update a relationship between a lawyer and client.
    
    Args:
        lawyer_id: Lawyer's ID
        client_id: Client's ID
        conversation_id: Optional conversation ID
        
    Returns:
        Relationship ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.now().isoformat()
    
    # Check if relationship exists
    cursor.execute("""
        SELECT id FROM LawyerClientRelationships 
        WHERE lawyer_id = ? AND client_id = ?
    """, (lawyer_id, client_id))
    existing = cursor.fetchone()
    
    if existing:
        rel_id = existing['id']
        cursor.execute("""
            UPDATE LawyerClientRelationships 
            SET conversation_id = COALESCE(?, conversation_id), updated = ?, status = 'active'
            WHERE id = ?
        """, (conversation_id, now_iso, rel_id))
    else:
        cursor.execute("""
            INSERT INTO LawyerClientRelationships (lawyer_id, client_id, conversation_id, created, updated)
            VALUES (?, ?, ?, ?, ?)
        """, (lawyer_id, client_id, conversation_id, now_iso, now_iso))
        rel_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return rel_id

def get_lawyer_clients(lawyer_id, status='active'):
    """
    Get all clients for a lawyer.
    
    Args:
        lawyer_id: Lawyer's ID
        status: Relationship status filter (default: 'active')
        
    Returns:
        List of client dictionaries with conversation info
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id, c.name, c.phone_number, c.email,
            r.conversation_id, r.status,
            conv.title, conv.updated as last_message_time,
            (SELECT COUNT(*) FROM Messages WHERE conversation_id = r.conversation_id) as message_count
        FROM Clients c
        JOIN LawyerClientRelationships r ON c.id = r.client_id
        LEFT JOIN Conversations conv ON r.conversation_id = conv.id
        WHERE r.lawyer_id = ? AND r.status = ?
        ORDER BY conv.updated DESC
    """, (lawyer_id, status))
    
    clients = cursor.fetchall()
    conn.close()
    
    return [dict(client) for client in clients]

def get_client_lawyer(client_phone_number):
    """
    Get the lawyer associated with a client by phone number.
    
    Args:
        client_phone_number: Client's phone number
        
    Returns:
        Lawyer dictionary or None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    normalized_number = normalize_phone_number(client_phone_number)
    
    cursor.execute("""
        SELECT l.* FROM Lawyers l
        JOIN LawyerClientRelationships r ON l.id = r.lawyer_id
        JOIN Clients c ON r.client_id = c.id
        WHERE c.phone_number = ? AND r.status = 'active' AND l.is_active = 1
        LIMIT 1
    """, (normalized_number,))
    
    lawyer = cursor.fetchone()
    conn.close()
    
    return dict(lawyer) if lawyer else None

def register_webhook(lawyer_id, url, event_type='message_received'):
    """
    Register a webhook for a lawyer.
    
    Args:
        lawyer_id: Lawyer's ID
        url: Webhook URL
        event_type: Type of event (default: 'message_received')
        
    Returns:
        Webhook ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO Webhooks (lawyer_id, url, event_type, created)
        VALUES (?, ?, ?, ?)
    """, (lawyer_id, url, event_type, now_iso))
    
    webhook_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"✅ Registered webhook for lawyer {lawyer_id}: {url}")
    return webhook_id

def get_lawyer_webhooks(lawyer_id, event_type=None, active_only=True):
    """Get all webhooks for a lawyer."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM Webhooks WHERE lawyer_id = ?"
    params = [lawyer_id]
    
    if active_only:
        query += " AND is_active = 1"
    
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    
    cursor.execute(query, params)
    webhooks = cursor.fetchall()
    conn.close()
    
    return [dict(webhook) for webhook in webhooks]

def queue_webhook_notification(webhook_id, payload):
    """
    Add a webhook notification to the queue.
    
    Args:
        webhook_id: Webhook ID
        payload: JSON payload to send
        
    Returns:
        Queue item ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.now().isoformat()
    
    import json
    payload_str = json.dumps(payload)
    
    cursor.execute("""
        INSERT INTO WebhookQueue (webhook_id, payload, created)
        VALUES (?, ?, ?)
    """, (webhook_id, payload_str, now_iso))
    
    queue_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return queue_id
