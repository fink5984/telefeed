"""
מנהל חשבונות - ניהול מרובה חשבונות טלגרם
"""
import os
import json
import asyncio
import time
from typing import Dict, List, Optional
from telethon import TelegramClient
from telethon.sessions import StringSession

ACCOUNTS_DIR = "accounts"
ACCOUNTS_FILE = os.path.join(ACCOUNTS_DIR, "accounts.json")

class AccountManager:
    """מנהל חשבונות טלגרם"""
    
    def __init__(self):
        self.accounts: Dict[str, dict] = {}
        self.clients: Dict[str, TelegramClient] = {}
        os.makedirs(ACCOUNTS_DIR, exist_ok=True)
        self.load_accounts()
    
    def load_accounts(self):
        """טוען חשבונות מהקובץ"""
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load accounts: {e}")
                self.accounts = {}
    
    def save_accounts(self):
        """שומר חשבונות לקובץ עם retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Write to temp file first
                temp_file = ACCOUNTS_FILE + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.accounts, f, ensure_ascii=False, indent=2)
                
                # Atomic rename
                if os.path.exists(ACCOUNTS_FILE):
                    os.replace(temp_file, ACCOUNTS_FILE)
                else:
                    os.rename(temp_file, ACCOUNTS_FILE)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    print(f"Error saving accounts: {e}")
    
    def add_account(self, name: str, api_id: int, api_hash: str, 
                   phone: str = None, bot_token: str = None, 
                   session_string: str = None):
        """מוסיף חשבון חדש"""
        self.accounts[name] = {
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "bot_token": bot_token,
            "session_string": session_string,
            "routes_file": f"accounts/{name}_routes.yaml",
            "enabled": True
        }
        self.save_accounts()
        
        # יצירת קובץ routes ריק
        routes_file = self.accounts[name]["routes_file"]
        if not os.path.exists(routes_file):
            with open(routes_file, 'w', encoding='utf-8') as f:
                f.write("# Routes for account: {}\n".format(name))
                f.write("routes: []\n")
    
    def remove_account(self, name: str):
        """מסיר חשבון"""
        if name in self.accounts:
            # מחיקת קובץ routes
            routes_file = self.accounts[name].get("routes_file")
            if routes_file and os.path.exists(routes_file):
                os.remove(routes_file)
            
            # מחיקת הגדרות
            del self.accounts[name]
            self.save_accounts()
            
            # ניתוק client אם פעיל
            if name in self.clients:
                asyncio.create_task(self.clients[name].disconnect())
                del self.clients[name]
    
    def get_account(self, name: str) -> Optional[dict]:
        """מחזיר פרטי חשבון"""
        return self.accounts.get(name)
    
    def list_accounts(self) -> List[str]:
        """מחזיר רשימת חשבונות"""
        return list(self.accounts.keys())
    
    def toggle_account(self, name: str, enabled: bool):
        """הפעלה/כיבוי חשבון"""
        if name in self.accounts:
            self.accounts[name]["enabled"] = enabled
            self.save_accounts()
    
    async def create_client(self, name: str) -> Optional[TelegramClient]:
        """יוצר client לחשבון"""
        account = self.get_account(name)
        if not account or not account.get("enabled"):
            return None
        
        api_id = account["api_id"]
        api_hash = account["api_hash"]
        
        # אם יש session_string, משתמשים בו
        if account.get("session_string"):
            session = StringSession(account["session_string"])
        else:
            # אחרת, משתמשים בקובץ session
            session_file = os.path.join(ACCOUNTS_DIR, f"{name}.session")
            session = session_file
        
        # בוט או משתמש?
        if account.get("bot_token"):
            client = TelegramClient(session, api_id, api_hash)
        else:
            client = TelegramClient(session, api_id, api_hash)
        
        return client
    
    async def login_account(self, name: str, code: str = None) -> dict:
        """מתחבר לחשבון (עם קוד אימות אם נדרש)"""
        account = self.get_account(name)
        if not account:
            return {"success": False, "error": "Account not found"}
        
        try:
            client = await self.create_client(name)
            if not client:
                return {"success": False, "error": "Failed to create client"}
            
            # Always use StringSession to avoid database issues
            await client.connect()
            
            if not await client.is_user_authorized():
                if account.get("bot_token"):
                    await client.start(bot_token=account["bot_token"])
                elif code:
                    # אימות עם קוד
                    phone = account.get("phone")
                    if not phone:
                        await client.disconnect()
                        return {"success": False, "error": "Phone number required"}
                    await client.sign_in(phone, code)
                else:
                    # שליחת קוד
                    phone = account.get("phone")
                    if not phone:
                        await client.disconnect()
                        return {"success": False, "error": "Phone number required"}
                    await client.send_code_request(phone)
                    # Don't disconnect yet - keep the session
                    return {
                        "success": False, 
                        "needs_code": True,
                        "message": f"Code sent to {phone}"
                    }
            
            # שמירת session string
            if isinstance(client.session, StringSession):
                session_str = client.session.save()
                self.accounts[name]["session_string"] = session_str
                self.save_accounts()
            
            # Keep client connected
            self.clients[name] = client
            
            return {
                "success": True,
                "message": "Logged in successfully"
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"Login error for {name}: {error_msg}")
            # Try to clean up
            try:
                if client and client.is_connected():
                    await client.disconnect()
            except:
                pass
            return {"success": False, "error": error_msg}
    
    def get_client(self, name: str) -> Optional[TelegramClient]:
        """מחזיר client פעיל"""
        return self.clients.get(name)
    
    async def disconnect_all(self):
        """מנתק את כל החשבונות"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
