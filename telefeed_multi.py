"""
Telefeed Multi-Account - מערכת routing לריבוי חשבונות טלגרם
"""
import os
import asyncio
import yaml
from accounts_manager import AccountManager
from telethon import events

# ====== נתיבים וקבצים ======
RELOAD_EVERY = int(os.getenv("ROUTES_RELOAD_EVERY", "5"))

class MultiAccountTelefeed:
    """מערכת telefeed לריבוי חשבונות"""
    
    def __init__(self):
        self.manager = AccountManager()
        self.routes_cache = {}  # cache של routes לכל חשבון
        self.last_reload = {}   # זמן טעינה אחרון לכל חשבון
        
    async def load_routes_for_account(self, account_name: str):
        """טוען routes עבור חשבון מסוים"""
        account = self.manager.get_account(account_name)
        if not account:
            return
        
        routes_file = account.get('routes_file')
        if not routes_file or not os.path.exists(routes_file):
            self.routes_cache[account_name] = []
            return
        
        try:
            with open(routes_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.routes_cache[account_name] = data.get('routes', [])
                self.last_reload[account_name] = os.path.getmtime(routes_file)
                print(f"[{account_name}] ✓ Loaded {len(self.routes_cache[account_name])} routes")
        except Exception as e:
            print(f"[{account_name}] ✗ Error loading routes: {e}")
            self.routes_cache[account_name] = []
    
    def should_forward_message(self, route: dict, message) -> bool:
        """בודק אם הודעה עומדת בתנאי route"""
        filters = route.get('filters', {})
        
        # בדיקת מילות מפתח
        keywords = filters.get('keywords')
        if keywords:
            text = message.text or ""
            if not any(kw in text for kw in keywords):
                return False
        
        # בדיקת אורך מינימלי
        min_length = filters.get('min_length')
        if min_length and len(message.text or "") < min_length:
            return False
        
        # בדיקת מדיה
        only_media = filters.get('only_media')
        if only_media and not message.media:
            return False
        
        # בדיקת טקסט בלבד
        only_text = filters.get('only_text')
        if only_text and message.media:
            return False
        
        return True
    
    async def handle_new_message(self, account_name: str, event):
        """מטפל בהודעה חדשה מחשבון מסוים"""
        message = event.message
        
        # טוען routes אם צריך
        if account_name not in self.routes_cache:
            await self.load_routes_for_account(account_name)
        
        routes = self.routes_cache.get(account_name, [])
        
        for route in routes:
            # בדיקת source
            source = route.get('source')
            if source:
                # תמיכה בשניהם - מספר וסטרינג
                if isinstance(source, str):
                    source = int(source) if source.lstrip('-').isdigit() else source
                
                msg_chat_id = message.chat_id
                
                # השוואה
                if source != msg_chat_id:
                    continue
            
            # בדיקת filters
            if not self.should_forward_message(route, message):
                continue
            
            # העברת הודעה
            dest = route.get('dest')
            if dest:
                try:
                    client = self.manager.get_client(account_name)
                    if client:
                        await client.forward_messages(dest, message)
                        print(f"[{account_name}] ✓ Forwarded: {source} → {dest}")
                except Exception as e:
                    print(f"[{account_name}] ✗ Error forwarding: {e}")
    
    async def setup_account_handlers(self, account_name: str):
        """מגדיר event handlers לחשבון"""
        client = self.manager.get_client(account_name)
        if not client:
            print(f"[{account_name}] Client not connected, skipping")
            return
        
        # טוען routes
        await self.load_routes_for_account(account_name)
        
        # רישום handler
        @client.on(events.NewMessage())
        async def handler(event):
            await self.handle_new_message(account_name, event)
        
        print(f"[{account_name}] ✓ Handler registered")
    
    async def reload_routes_loop(self):
        """לולאה לטעינה מחדש של routes"""
        while True:
            await asyncio.sleep(RELOAD_EVERY)
            
            for account_name in self.manager.list_accounts():
                account = self.manager.get_account(account_name)
                if not account or not account.get('enabled'):
                    continue
                
                routes_file = account.get('routes_file')
                if not routes_file or not os.path.exists(routes_file):
                    continue
                
                # בדיקה אם הקובץ השתנה
                current_mtime = os.path.getmtime(routes_file)
                last_mtime = self.last_reload.get(account_name, 0)
                
                if current_mtime > last_mtime:
                    print(f"[{account_name}] Routes file changed, reloading...")
                    await self.load_routes_for_account(account_name)
    
    async def start_all_accounts(self):
        """מתחיל את כל החשבונות"""
        print("🚀 Starting Telefeed Multi-Account System")
        print("=" * 50)
        
        # התחברות לכל החשבונות
        for account_name in self.manager.list_accounts():
            account = self.manager.get_account(account_name)
            if not account or not account.get('enabled'):
                print(f"[{account_name}] Skipped (disabled)")
                continue
            
            try:
                client = await self.manager.create_client(account_name)
                if not client:
                    print(f"[{account_name}] ✗ Failed to create client")
                    continue
                
                # התחברות
                if account.get('bot_token'):
                    await client.start(bot_token=account['bot_token'])
                elif account.get('session_string'):
                    await client.connect()
                    if not await client.is_user_authorized():
                        print(f"[{account_name}] ✗ Not authorized, need login via web UI")
                        continue
                else:
                    print(f"[{account_name}] ✗ No session_string, need login via web UI")
                    continue
                
                # שמירת client
                self.manager.clients[account_name] = client
                
                # הגדרת handlers
                await self.setup_account_handlers(account_name)
                
                print(f"[{account_name}] ✓ Started successfully")
                
            except Exception as e:
                print(f"[{account_name}] ✗ Error: {e}")
        
        print("=" * 50)
        print(f"✓ {len(self.manager.clients)} accounts running")
        print("📡 Listening for messages...")
        
        # לולאת reload
        await self.reload_routes_loop()
    
    async def stop_all_accounts(self):
        """עוצר את כל החשבונות"""
        print("\n🛑 Stopping all accounts...")
        await self.manager.disconnect_all()
        print("✓ All accounts stopped")

async def main():
    """נקודת כניסה ראשית"""
    system = MultiAccountTelefeed()
    
    try:
        await system.start_all_accounts()
    except KeyboardInterrupt:
        print("\n⚠ Received stop signal")
    finally:
        await system.stop_all_accounts()

if __name__ == "__main__":
    asyncio.run(main())
