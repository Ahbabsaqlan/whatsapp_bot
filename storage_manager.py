# storage_manager.py
import os
import shutil
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

BUCKET_NAME = "whatsapp_data"
ZIP_NAME = "whatsapp_profile" # shutil adds .zip automatically
REMOTE_FILE = "whatsapp_profile.zip"
LOCAL_DIR = "whatsapp_automation_profile"

def upload_session():
    """Zips the local session folder and uploads to Supabase Storage."""
    if not os.path.exists(LOCAL_DIR):
        print("❌ Local session folder not found.")
        return

    print("📦 Zipping session...")
    # Creates whatsapp_profile.zip
    shutil.make_archive(ZIP_NAME, 'zip', LOCAL_DIR)
    
    with open(f"{ZIP_NAME}.zip", "rb") as f:
        print("📤 Uploading to Supabase...")
        # upsert=true overwrites the old session
        supabase.storage.from_(BUCKET_NAME).upload(
            path=REMOTE_FILE, 
            file=f, 
            file_options={"cache-control": "3600", "upsert": "true"}
        )
    os.remove(f"{ZIP_NAME}.zip")
    print("✅ Session saved to Cloud.")

def download_session():
    """Downloads the session from Supabase and restores it locally."""
    print("📥 Attempting to restore session from Cloud...")
    try:
        with open("restore.zip", "wb") as f:
            res = supabase.storage.from_(BUCKET_NAME).download(REMOTE_FILE)
            f.write(res)
        
        if os.path.exists(LOCAL_DIR):
            shutil.rmtree(LOCAL_DIR)
            
        shutil.unpack_archive("restore.zip", LOCAL_DIR)
        os.remove("restore.zip")
        print("✅ Session restored successfully.")
        return True
    except Exception as e:
        print(f"⚠️ No cloud session found or error: {e}")
        return False