# storage_manager.py
import os
import shutil
from supabase import create_client, ClientOptions # Added ClientOptions

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ ERROR: Supabase Credentials Missing")
    supabase = None
else:
    # We initialize without a proxy to avoid the error you saw
    supabase = create_client(
        url, 
        key,
        options=ClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=10
        )
    )