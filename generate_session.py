"""
Generate SESSION_STRING for Telegram account
Run this locally to get your session string for Railway
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("API_ID", input("Enter API_ID: ")))
API_HASH = os.getenv("API_HASH", input("Enter API_HASH: "))

async def main():
    print("=" * 50)
    print("🔐 Telegram Session String Generator")
    print("=" * 50)
    
    # התחברות עם StringSession ריק
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    await client.start()
    
    print("\n✅ Login successful!")
    print("\n📋 Your SESSION_STRING:")
    print("=" * 50)
    session_string = client.session.save()
    print(session_string)
    print("=" * 50)
    
    print("\n💡 Add this to Railway environment variables:")
    print(f"SESSION_STRING={session_string}")
    print("\n⚠️  KEEP THIS SECRET! Don't share or commit to git!")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
