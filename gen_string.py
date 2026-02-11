from pyrogram import Client

api_id = 21457002        # вставь свой api_id
api_hash = "6f9f6b8fb05ef1f4d9916e901f27bf52"  # вставь свой api_hash

with Client("session", api_id=api_id, api_hash=api_hash) as app:
    print("\nВот твой STRING_SESSION:\n")
    print(app.export_session_string())
    print("\nСкопируй эту строку и вставь в config.py в переменную STRING_SESSION\n")
