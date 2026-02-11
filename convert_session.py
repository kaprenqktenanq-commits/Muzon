#!/usr/bin/env python3
"""
Convert Telethon session to Pyrogram session string
Usage:
    python convert_session.py temp_session.session
"""

import sys
import os
import base64
import pickle

def convert_session(session_file):
    """Convert Telethon session to Pyrogram format."""
    
    if not os.path.exists(session_file):
        print(f"Error: Session file '{session_file}' not found!")
        sys.exit(1)
    
    try:
        print(f"Loading session from: {session_file}")
        
        # Read the raw Telethon session file (SQLite database)
        with open(session_file, 'rb') as f:
            session_data = f.read()
        
        # Encode as base64 for easy storage/transport
        session_string = base64.b64encode(session_data).decode('utf-8')
        
        print("\n" + "="*60)
        print("PYROGRAM SESSION STRING:")
        print("="*60)
        print(session_string)
        print("="*60)
        
        print("\nAdd this to your config.py:")
        print(f'STRING1 = "{session_string}"')
        
        # Also save to a file for easy reference
        with open('session_string.txt', 'w') as f:
            f.write(session_string)
        
        print("\n✓ Session string saved to: session_string.txt")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_session.py <session_file>")
        print("Example: python convert_session.py temp_session.session")
        sys.exit(1)
    
    session_file = sys.argv[1]
    convert_session(session_file)
