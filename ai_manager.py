# ai_manager.py
import os
from openai import OpenAI
from dotenv import load_dotenv
import config

# --- Load environment variables ---
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")

# Initialize the OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_reply(history, your_name):
    """
    Generates a reply using OpenAI GPT based on the conversation history.
    """
    if not history:
        print("   ⚠️ AI Warning: History is empty.")
        return None

    # Check for empty content to save money/quota
    last_content = history[-1].get("content", "")
    if "Unsupported or Empty Message" in last_content or not last_content.strip():
        print("   ⚠️ AI Skipping: Last message is empty or unsupported.")
        return None

    # --- Convert History to OpenAI Format ---
    # OpenAI roles: "system", "user", "assistant"
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
    
    for msg in history:
        # Map your DB roles to OpenAI roles
        role = "assistant" if msg["role"] == "me" else "user"
        messages.append({"role": role, "content": msg["content"]})

    try:
        print(f"   🧠 Sending prompt to GPT to reply to: '{last_content[:50]}...'")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Best for bots: fast and very cheap
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        ai_reply = response.choices[0].message.content.strip()
        print(f"   🤖 GPT replied: '{ai_reply[:50]}...'")
        
        return ai_reply

    except Exception as e:
        print(f"   ❌ An error occurred with the OpenAI API: {e}")
        return "Sorry, I'm having trouble thinking right now. Ahbab will get back to you soon."