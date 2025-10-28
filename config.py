# config.py

# ==============================================================================
# --- CORE SETTINGS ---
# ==============================================================================

# Your full WhatsApp name as it appears in the app.
# This is crucial for correctly identifying messages sent by you.
YOUR_WHATSAPP_NAME = "AHBAB SAKALAN"


# ==============================================================================
# --- BOT BEHAVIOR SETTINGS ---
# ==============================================================================

# A list of generic replies the bot can send.
# When a reply is needed, a random message from this list will be chosen.
SIMULATED_AI_REPLIES = [
    "Hello! Thanks for your message. Ahbab has received it and will get back to you soon.",
    "Hi there! Ahbab has seen your message and will reply shortly. Thank you!",
    "Got it! Thanks for reaching out. Ahbab will respond as soon as possible.",
    "Message received. Ahbab will get back to you shortly. Have a great day!"
]

# --- NEW SETTING ---
# The maximum age of an unreplied message, in days, that the bot will respond to.
# This prevents the bot from replying to very old conversations.
REPLY_MAX_AGE_DAYS = 7


# ==============================================================================
# --- SCHEDULER TIMINGS (in seconds) ---
# ==============================================================================

# How often the bot should check for new unread messages by opening WhatsApp Web.
SYNC_INTERVAL_SECONDS = 60

# How often the bot should check the database for conversations that need a reply.
REPLY_INTERVAL_SECONDS = 180

# How long to pause between sending replies to different people in the same batch.
REPLY_API_TASK_DELAY_SECONDS = 30