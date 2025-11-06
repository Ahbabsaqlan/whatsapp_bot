# ai_manager.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
import config

# --- Load environment variables from .env file ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

# --- Configure the Gemini API ---
genai.configure(api_key=GEMINI_API_KEY)

# --- Set up the model with safety settings ---
generation_config = {
    "temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048,
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro",
    generation_config=generation_config,
    safety_settings=safety_settings
)

def generate_reply(history, your_name):
    """
    Generates a reply using Gemini based on the conversation history.
    """
    if not history:
        print("   ⚠️ AI Warning: Conversation history is empty. Cannot generate reply.")
        return None

    formatted_history = []
    for message in history:
        role = "user" if message["role"] == "user" else "model"
        formatted_history.append({"role": role, "parts": [message["content"]]})

    last_message = formatted_history.pop()
    if last_message['role'] != 'user':
        print("   ⚠️ AI Warning: Last message is not from you. No reply needed.")
        return None

    try:
        chat_prompt = [
            {"role": "user", "parts": [config.SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood. I am ready to assist."]}
        ] + formatted_history
        
        chat = model.start_chat(history=chat_prompt)
        
        print(f"   🧠 Sending prompt to Gemini to reply to: '{last_message['parts'][0][:50]}...'")
        response = chat.send_message(last_message['parts'])
        
        ai_reply = response.text.strip()
        print(f"   🤖 Gemini replied: '{ai_reply[:50]}...'")
        
        return ai_reply
    except Exception as e:
        print(f"   ❌ An error occurred with the Gemini API: {e}")
        return "Sorry, I'm having trouble connecting right now. Ahbab will get back to you shortly."