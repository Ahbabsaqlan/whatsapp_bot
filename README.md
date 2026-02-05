# 📱 WhatsApp Automation API

This project automates WhatsApp Web using Selenium and provides a **REST API** for managing messages, contacts, and replies. It’s designed for semi-automated workflows like chat assistants, schedulers, or personal bots.

The system operates in distinct modes: a **Continuous Bot** for parallel syncing and replying, a **Manual Full Scan** to build your database, and a suite of **API Tools** for direct interaction.

## 🏢 **NEW: Lawyer Directory Integration**

This bot now supports **multi-user lawyer-client communication** for lawyer directory web applications! Each lawyer can:
- Have their own WhatsApp account and client list
- Send/receive messages through a secure API
- Receive real-time webhook notifications
- Manage client relationships independently

**Integration Guides:**
- **[📘 General Lawyer Directory Integration](LAWYER_DIRECTORY_INTEGRATION.md)** - Complete API reference and examples
- **[🎯 AinSongjog-Specific Integration](AINSONGJOG_INTEGRATION.md)** - Ready-to-use NestJS modules for AinSongjog platform

---

## 🚀 Features

### Core Functionality
| Feature | Status |
|:----------|:--------:|
| Open WhatsApp Web & Handle Login | ✅ Done |
| Scrape Unread Messages Reliably | ✅ Done |
| Identify Senders (Name/Number) | ✅ Done |
| Differentiate Personal, Business & Group Chats | ✅ Done |
| Store Conversations Locally in SQLite | ✅ Done |
| Send Automated, Human-like Replies | ✅ Done |
| REST API for Programmatic Control | ✅ Done |
| All features in the form functions for integration with any other system(`controller.py`) | ✅ Done |
| Read and Store Received Images | ✅ Done  |

### Advanced Capabilities
| Feature | Status |
|:----------|:--------:|
| Parallel Sync & Reply Scheduler | ✅ Done |
| Centralized Configuration File (`config.py`) | ✅ Done |
| Command-Line API Tools for DB Interaction | ✅ Done |
| Emoji & Special Character Support in Names | ✅ Done |
| Robust Error Handling & Task Recovery | ✅ Done |

---

## 📖 User Manual

> ### Quick Start
> 1.  Clone the repository.
> 2.  Run `pip install -r requirements.txt` (or let `utility.py` handle it on first run).
> 3.  Customize `config.py` with your WhatsApp name and desired timings.
> 4.  Run `python3 whatsappSynchronizer.py`.
> 5.  On the first run, choose **Option 2 (Full Scan)** to build your database.
> 6.  After the scan, restart and choose **Option 1 (Start Bot)** to run in continuous mode.

### 1. Configuration (`config.py`)

Before running the application, you **must** configure `config.py`.

```python
# Your full WhatsApp name as it appears in the app.
YOUR_WHATSAPP_NAME = "Your Name Here"

# How often the bot should check for new messages (in seconds).
SYNC_INTERVAL_SECONDS = 60

# How often the bot should check for conversations that need a reply.
REPLY_INTERVAL_SECONDS = 180

```
### 2. Operational Modes

The tool offers several modes accessible from the main menu.

#### Mode 1: Start Bot (Continuous Sync & Reply)
This is the primary mode for continuous, unattended operation.

*   **What it does:** Runs an intelligent scheduler that alternates between two tasks on independent timers:
    1.  **Sync Task:** Opens WhatsApp Web, scrapes all unread messages, saves them to the database, and closes the browser.
    2.  **Reply Task:** Checks the database for any conversations where you haven't sent the last message. It then uses the API to send a pre-configured reply.
*   **When to use it:** For daily, hands-off operation after your database has been initially populated.

#### Mode 2: Update Database (One-Time Full Scan)
This mode is for building or completely refreshing your message archive.

*   **What it does:** Opens WhatsApp Web and methodically goes through **every single contact** in your chat list. It scrolls up through each conversation history, scraping and saving all messages that aren't already in the database.
*   **When to use it:**
    *   On the very first run to create your initial database.
    *   After a long period of inactivity to catch up on all conversations, not just unread ones.
    *   If you suspect the database is out of sync.

#### Mode 3: Database API Tools
A command-line interface for power users to directly query the database via the API.

*   **What it does:** Allows you to perform actions like:
    *   Get a summary of a specific conversation.
    *   View the last few messages from a contact.
    *   List all conversations that are currently awaiting a reply.
    *   Manually send a custom message to any number.
*   **When to use it:** For debugging, manual intervention, or quickly checking the status of a conversation without opening the full WhatsApp client.

### 3. First-Time Setup & Best Practices

1.  **Initial Run:** The first time you run the script, it will download the correct ChromeDriver for your version of Google Chrome.
2.  **QR Code Scan:** You will need to scan the WhatsApp Web QR code with your phone. The script saves your session in a `whatsapp_automation_profile` folder, so you will only need to do this once.
3.  **Build the Database First:** Always run a **Full Scan (Option 2)** before starting the continuous bot. A complete database ensures the bot has the full context of conversations and doesn't miss old unreplied messages.
4.  **Let it Run:** The continuous bot is designed to be a long-running process. You can leave it running in a terminal window (or a `screen`/`tmux` session on a server) to manage your messages automatically.

## 🧩 System Overview
1. The bot launches WhatsApp Web using Selenium.
2. It reads messages, identifies contacts, and stores them in SQLite.
3. REST API endpoints allow sending, retrieving, and managing conversations.
4. The client (`api_client.py`) can call these endpoints programmatically.

---

## 🧠 Database Schema

**Conversations Table**
| Column | Type | Description |
|---------|------|-------------|
| id | INTEGER | Primary key |
| title | TEXT | Contact name or title |
| phone_number | TEXT | Normalized contact number |
| created / updated | TEXT | ISO timestamps |
| context_summary | TEXT | Short summary of conversation |
| size | INTEGER | Total messages count |

**Messages Table**
| Column | Type | Description |
|---------|------|-------------|
| id | INTEGER | Primary key |
| conversation_id | INTEGER | FK to Conversations |
| role | TEXT | ‘user’ or ‘assistant’ |
| sender_name | TEXT | Who sent the message |
| content | TEXT | Message text |
| meta_text | TEXT | Unique ID to prevent duplicates |
| sending_date / stored_date | TEXT | ISO timestamps |
| attachment_filename | TEXT | Downloaded filename |

---



# 🧾 API Documentation

## Base URL
```
http://127.0.0.1:5001
```

---

## 🗄️ Initialize Database

**POST** `/init_db`

Initializes the SQLite database used to store all messages and contacts.

### Responses
| Code | Description |
|------|-------------|
| 200 | Database initialized successfully |
| 500 | Internal server error |

### Response Example
```json
{
  "status": "success",
  "message": "Database initialized."
}
```

---

## 💬 Save Messages

**POST** `/messages`

Stores one or more new messages into the local database.

### Request Body
```json
{
  "contact_name": "John Doe",
  "phone_number": "+8801712345678",
  "new_messages": [
    {
      "role": "user",
      "sender": "John Doe",
      "content": "Hey!",
      "date": "25/10/2025",
      "time": "6:15 PM",
      "meta_text": "msg_abc123"
    }
  ]
}
```

### Responses
| Code | Description |
|------|-------------|
| 201 | Messages successfully stored |
| 400 | Missing or invalid fields |
| 500 | Database or internal error |

### Response Example
```json
{
  "status": "success",
  "message": "Processed messages for John Doe"
}
```

---

## 📇 Get Contact Details

**GET** `/contact-details`

Retrieves stored details about a contact, such as their name and the last message identifier.

### Query Parameters
| Name | Type | Required | Description |
|------|------|----------|-------------|
| phone_number | string | ✅ | Contact phone number |

### Responses
| Code | Description |
|------|-------------|
| 200 | Contact found |
| 404 | Contact not found |
| 400 | Missing phone number |

### Response Example
```json
{
  "title": "John Doe",
  "last_meta_text": "msg_abc123"
}
```

---

## 🔍 Get Last Message

**GET** `/last_message`

Retrieves the meta_text of the last message for a given contact.

### Query Parameters
| Name | Type | Required | Description |
|------|------|----------|-------------|
| phone_number | string | ✅ | Contact phone number |
| title | string | ✅ | Contact title |
| your_name | string | ✅ | Your WhatsApp profile name |

### Responses
| Code | Description |
|------|-------------|
| 200 | Last message retrieved successfully |
| 400 | Missing parameters |

### Response Example
```json
{
  "meta_text": "msg_xyz789"
}
```

---

## 📜 Get Conversation Summary

**GET** `/summary`

Returns a summarized view of a stored conversation.

### Query Parameters
| Name | Type | Required | Description |
|------|------|----------|-------------|
| title | string | ✅ | Contact title |

### Responses
| Code | Description |
|------|-------------|
| 200 | Summary returned successfully |
| 400 | Missing title parameter |

### Response Example
```json
{
  "summary": "Start: 'Hey!' | End: 'Got it!' | Total: 15 msgs"
}
```

---

## 📨 Get Recent Messages

**GET** `/messages`

Fetches the most recent messages for a given conversation.

### Query Parameters
| Name | Type | Required | Description |
|------|------|----------|-------------|
| title | string | ✅ | Contact title |
| count | integer | ❌ | Number of messages to return (default: 5) |

### Responses
| Code | Description |
|------|-------------|
| 200 | Messages retrieved successfully |
| 400 | Missing title parameter |

### Response Example
```json
[
  {
    "role": "user",
    "content": "Hey!",
    "sending_date": "2025-10-25T18:15:00"
  },
  {
    "role": "assistant",
    "content": "Hi there!",
    "sending_date": "2025-10-25T18:16:10"
  }
]
```

---

## ⚠️ Get Unreplied Conversations

**GET** `/unreplied`

Retrieves a list of conversations where the last message came from the user and hasn't been replied to yet.

### Responses
| Code | Description |
|------|-------------|
| 200 | Unreplied conversations retrieved successfully |

### Response Example
```json
[
  {
    "title": "John Doe",
    "phone_number": "+8801712345678",
    "updated": "2025-10-25T18:20:00"
  }
]
```

---

## 🤖 Send Message

**POST** `/send-message`

Triggers a background Selenium process to send a message via WhatsApp Web.Both param is optional but the text param Will be used as caption if file_path is present.

### Request Body
```json
{
  "phone_number": "+8801712345678",
  "text": "Hello from the API!",
  "file_path": "file_path"
}
```

### Responses
| Code | Description |
|------|-------------|
| 202 | Message sending initiated successfully |
| 400 | Missing phone number or text |
| 500 | Server configuration or automation error |

### Response Example
```json
{
  "status": "success",
  "message": "Message sending task has been initiated."
}
```