#!/usr/bin/env python3
"""
Quick setup script for lawyer directory integration.
This helps create lawyer accounts and configure the system.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lawyer_directory_integration as ldi
import database_manager as db

def main():
    print("=" * 60)
    print("  WhatsApp Bot - Lawyer Directory Setup")
    print("=" * 60)
    print()
    
    # Initialize databases
    print("Initializing databases...")
    db.init_db()
    ldi.init_lawyer_directory_db()
    print("✅ Databases initialized\n")
    
    # Interactive lawyer creation
    print("Let's create a lawyer account.")
    print("You can create multiple accounts by running this script again.\n")
    
    name = input("Lawyer's full name: ").strip()
    if not name:
        print("❌ Name is required")
        return
    
    email = input("Lawyer's email: ").strip()
    if not email:
        print("❌ Email is required")
        return
    
    phone = input("Lawyer's phone number (e.g., +1234567890): ").strip()
    if not phone:
        print("❌ Phone number is required")
        return
    
    whatsapp_name = input("Name as shown in WhatsApp: ").strip()
    if not whatsapp_name:
        whatsapp_name = name
    
    profile_path_input = input("WhatsApp profile path (leave empty for shared profile): ").strip()
    profile_path = profile_path_input if profile_path_input else None
    
    if profile_path:
        # Create directory if it doesn't exist
        os.makedirs(profile_path, exist_ok=True)
        print(f"✅ Profile directory created: {profile_path}")
    
    print("\nCreating lawyer account...")
    lawyer = ldi.create_lawyer(
        name=name,
        email=email,
        phone_number=phone,
        whatsapp_name=whatsapp_name,
        profile_path=profile_path
    )
    
    if lawyer:
        print("\n" + "=" * 60)
        print("  ✅ Lawyer Account Created Successfully!")
        print("=" * 60)
        print(f"\nLawyer ID: {lawyer['id']}")
        print(f"Name: {lawyer['name']}")
        print(f"Email: {lawyer['email']}")
        print(f"Phone: {lawyer['phone_number']}")
        print(f"WhatsApp Name: {lawyer['whatsapp_name']}")
        print(f"\n🔑 API KEY (save this securely):")
        print(f"   {lawyer['api_key']}")
        print("\n⚠️  IMPORTANT: Save the API key above! You'll need it for all API calls.")
        print("\nNext steps:")
        print("1. Start the server: python run_server.py")
        print("2. Use the API key in your web application")
        print("3. Scan WhatsApp QR code when sending first message")
        print("\nSee LAWYER_DIRECTORY_INTEGRATION.md for full documentation.")
    else:
        print("\n❌ Failed to create lawyer account.")
        print("This might be because the email or phone is already registered.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
