# storage_manager.py
import os
import shutil
from supabase import create_client, ClientOptions

# --- Load Environment Variables ---
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# --- Constants ---
BUCKET_NAME = "whatsapp_data"
ZIP_NAME = "whatsapp_profile" # shutil adds .zip
REMOTE_FILE = "whatsapp_profile.zip"
LOCAL_DIR = "whatsapp_automation_profile"

# --- Initialize Supabase with Fix for Proxy Error ---
if not url or not key:
    print("❌ ERROR: Supabase Credentials Missing in Environment Variables")
    supabase = None
else:
    # ClientOptions fix for the 'proxy' TypeError
    supabase = create_client(
        url, 
        key,
        options=ClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=10
        )
    )

def upload_session():
    """Zips the local session and uploads it to Supabase Storage."""
    if not supabase: return
    if not os.path.exists(LOCAL_DIR):
        print("⚠️ No local profile found to upload.")
        return

    try:
        print("📦 Zipping WhatsApp session...")
        shutil.make_archive(ZIP_NAME, 'zip', LOCAL_DIR)
        
        with open(f"{ZIP_NAME}.zip", "rb") as f:
            print("📤 Uploading session to Supabase Storage...")
            supabase.storage.from_(BUCKET_NAME).upload(
                path=REMOTE_FILE, 
                file=f, 
                file_options={"cache-control": "3600", "upsert": "true"}
            )
        os.remove(f"{ZIP_NAME}.zip")
        print("✅ Session backed up to cloud.")
    except Exception as e:
        print(f"❌ Failed to upload session: {e}")

def download_session():
    """Downloads the session from Supabase and unzips it locally."""
    if not supabase: return False
    print("📥 Checking for cloud session backup...")
    try:
        # Check if bucket/file exists by attempting download
        res = supabase.storage.from_(BUCKET_NAME).download(REMOTE_FILE)
        
        with open("restore.zip", "wb") as f:
            f.write(res)
        
        if os.path.exists(LOCAL_DIR):
            shutil.rmtree(LOCAL_DIR)
            
        print("📂 Unzipping cloud session...")
        shutil.unpack_archive("restore.zip", LOCAL_DIR)
        os.remove("restore.zip")
        print("✅ Session restored from cloud.")
        return True
    except Exception as e:
        print(f"ℹ️ Could not restore session (this is normal if first run): {e}")
        return False