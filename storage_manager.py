import os
import shutil
from supabase import create_client, ClientOptions

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key, options=ClientOptions(postgrest_client_timeout=10, storage_client_timeout=60))

BUCKET_NAME = "whatsapp_data"

def upload_session(session_id):
    """Zips a SPECIFIC session folder and uploads it as session_id.zip"""
    local_dir = f"profiles/{session_id}" # e.g., profiles/user123
    
    if not os.path.exists(local_dir):
        return False

    # Zip profiles/user123 -> user123.zip
    shutil.make_archive(session_id, 'zip', local_dir)
    
    with open(f"{session_id}.zip", "rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=f"{session_id}.zip", 
            file=f, 
            file_options={"cache-control": "3600", "upsert": "true"}
        )
    os.remove(f"{session_id}.zip")
    print(f"✅ Session '{session_id}' saved to Cloud.")

def download_session(session_id):
    """Downloads session_id.zip and extracts it to profiles/session_id"""
    local_dir = f"profiles/{session_id}"
    
    try:
        res = supabase.storage.from_(BUCKET_NAME).download(f"{session_id}.zip")
        with open("restore.zip", "wb") as f:
            f.write(res)
        
        if os.path.exists(local_dir):
            shutil.rmtree(local_dir)
            
        shutil.unpack_archive("restore.zip", local_dir)
        os.remove("restore.zip")
        return True
    except:
        return False
    
def list_available_sessions():
    """Returns a list of .zip files in the bucket."""
    try:
        # Supabase storage list API
        files = supabase.storage.from_(BUCKET_NAME).list()
        # Filter only zip files
        return [f['name'] for f in files if f['name'].endswith('.zip')]
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return []