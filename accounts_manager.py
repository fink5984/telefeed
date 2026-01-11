"""
מנהל חשבונות - ניהול מרובה חשבונות טלגרם
"""
import os
import json
import asyncio
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
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                self.accounts = json.load(f)
    
    def save_accounts(self):
        """שומר חשבונות לקובץ"""
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)
    
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
            
            if not await client.is_user_authorized():
                if account.get("bot_token"):
                    await client.start(bot_token=account["bot_token"])
                elif code:
                    # אימות עם קוד
                    await client.sign_in(account["phone"], code)
                else:
                    # שליחת קוד
                    await client.send_code_request(account["phone"])
                    return {
                        "success": False, 
                        "needs_code": True,
                        "message": "Code sent to phone"
                    }
            
            # שמירת session string
            if isinstance(client.session, StringSession):
                session_str = client.session.save()
                self.accounts[name]["session_string"] = session_str
                self.save_accounts()
            
            self.clients[name] = client
            
            return {
                "success": True,
                "message": "Logged in successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_client(self, name: str) -> Optional[TelegramClient]:
        """מחזיר client פעיל"""
        return self.clients.get(name)
    
    async def disconnect_all(self):
        """מנתק את כל החשבונות"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
