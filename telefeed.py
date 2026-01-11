import os
import asyncio
from dotenv import load_dotenv
load_dotenv()
import time
import asyncio
import yaml
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ====== נתיבים וקבצים ======
APP_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(APP_DIR, "data")
ROUTES_FILE  = os.path.join(APP_DIR, "routes.yaml")
ENV_FILE     = os.path.join(APP_DIR, ".env")
RELOAD_EVERY = int(os.getenv("ROUTES_RELOAD_EVERY", "5"))  # שניות לבדיקה אוטומטית

# ====== ENV ======
load_dotenv(ENV_FILE)

API_ID   = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

BOT_TOKEN      = os.getenv("BOT_TOKEN")               # אופציונלי – להרצה כבוט
SESSION_NAME   = os.getenv("SESSION", "telefeed")     # בלי .session
SESSION_STRING = os.getenv("SESSION_STRING")          # אופציונלי – אם רוצים בלי קובץ
OWNER_ID       = int(os.getenv("OWNER_ID", "0"))      # מי יכול להריץ /reload

# ====== ברירת מחדל גלובלית לחוקים ======
global_defaults = {
    "mode":       os.getenv("TRANSFER_MODE", "FORWARD").upper(),  # FORWARD | COPY | PREFIX
    "prefix":     os.getenv("PREFIX", ""),
    "text_only":  os.getenv("TEXT_ONLY",  "false").lower() == "true",
    "media_only": os.getenv("MEDIA_ONLY", "false").lower() == "true",
}

# ====== לוג פשוט עם חותמת זמן ======
def log(*a):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}]", *a, flush=True)

# ====== טעינת חוקים + ניטור שינויים ======
_routes = []
_routes_mtime = 0.0

def _merge_defaults(cfg_defaults):
    merged = dict(global_defaults)
    if isinstance(cfg_defaults, dict):
        merged.update(cfg_defaults)
        if "mode" in merged and merged["mode"]:
            merged["mode"] = merged["mode"].upper()
    return merged

def load_routes(force=False):
    """טען את routes.yaml אם הוא השתנה או אם force=True."""
    global _routes, _routes_mtime

    try:
        mtime = os.path.getmtime(ROUTES_FILE)
    except FileNotFoundError:
        if force or _routes == []:
            _routes = []
            _routes_mtime = 0.0
            log("⚠️ routes.yaml not found – no routes loaded")
        return False

    if not force and mtime == _routes_mtime:
        return False  # אין שינוי

    with open(ROUTES_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    defaults = _merge_defaults(cfg.get("defaults", {}))
    routes   = cfg.get("routes", []) or []

    normalized = []
    for r in routes:
        # normalize + ירושה של ברירות מחדל
        rr = dict(r)
        rr["sources"]    = [int(x) for x in rr.get("sources", [])]
        rr["dests"]      = [int(x) for x in rr.get("dests", [])]
        rr["mode"]       = str(rr.get("mode", defaults["mode"])).upper()
        rr["prefix"]     = rr.get("prefix", defaults["prefix"])
        rr["text_only"]  = bool(rr.get("text_only",  defaults["text_only"]))
        rr["media_only"] = bool(rr.get("media_only", defaults["media_only"]))
        normalized.append(rr)

    _routes = normalized
    _routes_mtime = mtime
    log(f"🔁 routes reloaded: {len(_routes)} rule(s)")
    return True

def get_routes():
    return _routes

# ====== הכנת הלקוח ======
os.makedirs(DATA_DIR, exist_ok=True)

if SESSION_STRING:
    session = StringSession(SESSION_STRING)
else:
    # Telethon יוצר/טוען קובץ בשם <SESSION_NAME>.session בתוך /app/data
    session = os.path.join(DATA_DIR, SESSION_NAME)

client = TelegramClient(session, API_ID, API_HASH)

# ====== עזר לזיהוי מדיה ======
def is_media(msg):
    return bool(msg.media)

# ====== שליחה/העברה ======
async def deliver(msg, dest, mode, prefix):
    if mode == "FORWARD":
        await client.forward_messages(dest, msg)
        return

    text = msg.message or ""
    if mode == "PREFIX" and text:
        text = f"{prefix} {text}" if prefix else text

    if is_media(msg):
        await client.send_file(
            dest,
            file=msg.media,
            caption=text if text else None,
            parse_mode="html",
            supports_streaming=True,
        )
    else:
        await client.send_message(dest, text or " ", parse_mode="html")

# ====== מאזין להודעות ======
_last_reload_check = 0.0

@client.on(events.NewMessage())
async def on_new_message(event):
    global _last_reload_check

    # בדיקת עדכון קובץ החוקים כל RELOAD_EVERY שניות
    now = time.time()
    if now - _last_reload_check >= RELOAD_EVERY:
        _last_reload_check = now
        load_routes()  # נטען אם השתנה

    src = event.chat_id
    msg = event.message

    log(f"📥 message in {src} | text={bool(msg.message)} media={bool(msg.media)}")

    routes = get_routes()
    matching = [r for r in routes if src in r["sources"]]
    if not matching:
        log(f"↪️ no matching routes for {src}")
        return

    for rule in matching:
        log(
            f"🔎 rule match → dests={rule['dests']} mode={rule['mode']} "
            f"text_only={rule['text_only']} media_only={rule['media_only']}"
        )

        if rule["text_only"] and not (msg.message and msg.message.strip()):
            log("   ⏭ skipped: text_only and message has no text")
            continue
        if rule["media_only"] and not is_media(msg):
            log("   ⏭ skipped: media_only and no media")
            continue

        sent_to = set()
        for dest in rule["dests"]:
            if dest == src:
                log(f"   ⏭ skipped: dest==src ({dest})")
                continue
            if dest in sent_to:
                log(f"   ⏭ skipped: duplicate dest ({dest})")
                continue
            try:
                await deliver(msg, dest, rule["mode"], rule["prefix"])
                sent_to.add(dest)
                log(f"✅ sent to {dest}")
            except Exception as e:
                log(f"❌ FAILED to send to {dest}: {e}")
        log(f"➡️ {src} → {list(sent_to)} [{rule['mode']}]")

# ====== פקודות ניהול: /id ו-/reload ======
@client.on(events.NewMessage(pattern=r'^/id$'))
async def cmd_id(event):
    chat_id = event.chat_id
    await event.reply(f"🆔 chat_id: `{chat_id}`", parse_mode="md")
    log(f"ℹ️ /id in {chat_id}")

@client.on(events.NewMessage(pattern=r'^/reload$'))
async def cmd_reload(event):
    user_id = (await event.get_sender()).id
    if OWNER_ID and user_id != OWNER_ID:
        await event.reply("⛔ only OWNER can /reload")
        log(f"⛔ /reload denied for user {user_id}")
        return
    changed = load_routes(force=True)
    await event.reply("🔁 routes reloaded" if changed else "✅ routes unchanged")
    log(f"🔁 /reload by {user_id} → {'changed' if changed else 'unchanged'}")

# ====== main ======
async def main():
    if BOT_TOKEN:
        await client.start(bot_token=BOT_TOKEN)
        log("🤖 TeleFeed started as BOT account")
    else:
        await client.start()
        log("👤 TeleFeed started as USER account")

    load_routes(force=True)
    log("📡 TeleFeed running with multiple routes…")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
