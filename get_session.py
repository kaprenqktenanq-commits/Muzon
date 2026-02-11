#!/usr/bin/env python3
"""
Telegram Session String Generator using Telethon
Usage:
    python get_session.py
"""

import sys
import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

def get_session():
    """Generate a Telegram session string for your account."""
    
    # Get API credentials from user
    api_id = input("Enter your Telegram API ID (from https://my.telegram.org/apps): ").strip()
    api_hash = input("Enter your Telegram API Hash (from https://my.telegram.org/apps): ").strip()
    phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
    
    if not api_id or not api_hash or not phone:
        print("Error: All fields are required!")
        sys.exit(1)
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("Error: API ID must be a number!")
        sys.exit(1)
    
    # Create a session file that will be generated
    session_name = "temp_session"
    
    # Create client and authenticate
    client = TelegramClient(session_name, api_id, api_hash)
    
    try:
        with client:
            # Send code request
            if not client.is_user_authorized():
                client.send_code_request(phone)
                
                # Get code from user
                code = input("\nEnter the code sent to your Telegram account: ").strip()
                
                try:
                    client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    password = input("Two-factor authentication enabled. Enter your password: ").strip()
                    client.sign_in(password=password)
                
                print("\n✓ Login successful!")
            
            # Export the session string
            session_string = client.session.save()
            
            print("\n" + "="*60)
            print("YOUR SESSION STRING (Telethon format):")
            print("="*60)
            print(session_string)
            print("="*60)
            
            print("\nFor Pyrogram, you need to convert this session to Pyrogram format.")
            print("For now, you can use this with Telethon-based clients.")
            print("\nTo use with ArmedMusic (Pyrogram):")
            print("1. Log in once with this script to create the session")
            print("2. Then copy the session file to your ArmedMusic directory")
            print(f"3. Rename it to your STRING variable name (e.g., 'session1')")
            
            # Also show file location
            import os
            session_file = f"{session_name}.session"
            if os.path.exists(session_file):
                print(f"\n✓ Session file saved as: {session_file}")
                print("  Copy this file to your ArmedMusic config and update STRING1, STRING2, etc.")
            
    except Exception as e:
        print(f"\n✗ Error during login: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        get_session()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

