#!/usr/bin/env python3
"""
🎵 Music Bot with API Key Generator
- Multiple admins can generate keys
- Host on Vercel
"""

import os
import json
import time
import secrets
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ===================== CONFIGURATION =====================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8736103437:AAHx0Zhm0m46n9rmZ4Cqb52IxLTe5J1crLY")
OWNER_ID = int(os.environ.get("OWNER_ID", 8041502308))
API_BASE_URL = os.environ.get("API_BASE_URL", "https://zyra-yt-dlp-api.vercel.app")
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", 1000))

# ===================== MULTIPLE ADMINS =====================

ADMINS = os.environ.get("ADMINS", "").split(",")
ADMINS = [int(a.strip()) for a in ADMINS if a.strip().isdigit()]

# If no admins set in env, use default list
if not ADMINS:
    ADMINS = [
        8041502308,      # Owner (Your ID)
        # Add more admin IDs here
        # 123456789,
        # 987654321,
    ]

# Owner is always an admin
if OWNER_ID not in ADMINS:
    ADMINS.append(OWNER_ID)

def is_admin(user_id):
    return user_id in ADMINS or user_id == OWNER_ID

# ===================== DATA MANAGEMENT =====================

def load_json(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def get_user_api_key(user_id):
    keys = load_json(API_KEYS_FILE)
    user_id_str = str(user_id)
    
    if user_id_str not in keys:
        keys[user_id_str] = {
            "api_key": f"API-{secrets.token_hex(16)}",
            "created_at": time.time(),
            "is_active": True
        }
        save_json(API_KEYS_FILE, keys)
    
    return keys[user_id_str]["api_key"]

def get_user_usage(user_id):
    usage = load_json(USAGE_FILE)
    user_id_str = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user_id_str not in usage or usage[user_id_str].get("date") != today:
        usage[user_id_str] = {"date": today, "count": 0}
        save_json(USAGE_FILE, usage)
        return 0
    
    return usage[user_id_str]["count"]

def increment_usage(user_id):
    usage = load_json(USAGE_FILE)
    user_id_str = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user_id_str not in usage or usage[user_id_str].get("date") != today:
        usage[user_id_str] = {"date": today, "count": 0}
    
    usage[user_id_str]["count"] += 1
    save_json(USAGE_FILE, usage)
    return usage[user_id_str]["count"]

def can_make_request(user_id):
    return get_user_usage(user_id) < DAILY_LIMIT

def generate_new_key(friend_username, admin_id):
    new_key = f"API-{secrets.token_hex(16)}"
    keys = load_json(GENERATED_KEYS_FILE)
    
    keys[new_key] = {
        "username": friend_username,
        "generated_by": admin_id,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_active": True
    }
    
    save_json(GENERATED_KEYS_FILE, keys)
    return new_key

# ===================== API CALLS =====================

def call_api(endpoint, params=None, json_data=None, api_key=None):
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        if endpoint == "search":
            response = requests.get(f"{API_BASE_URL}/search", params=params, headers=headers, timeout=10)
        elif endpoint == "stream":
            response = requests.get(f"{API_BASE_URL}/stream", params=params, headers=headers, timeout=10)
        elif endpoint == "recommendations":
            response = requests.get(f"{API_BASE_URL}/recommendations", params=params, headers=headers, timeout=10)
        elif endpoint == "batch":
            response = requests.post(f"{API_BASE_URL}/search-songs/", json=json_data, headers=headers, timeout=15)
        else:
            return None, "Unknown endpoint"
        
        if response.status_code == 200:
            return response.json(), None
        return None, f"API Error: {response.status_code}"
    except Exception as e:
        return None, str(e)

# ===================== TELEGRAM COMMANDS =====================

# Files
API_KEYS_FILE = "api_keys.json"
USAGE_FILE = "usage.json"
GENERATED_KEYS_FILE = "generated_keys.json"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin_user = is_admin(user.id)
    
    msg = (
        f"🎵 **Welcome {user.first_name}!**\n\n"
        "I'm a Music Bot with free API keys!\n\n"
        "📋 **Commands:**\n"
        "• `/getapi` - Get your free API key\n"
        "• `/myapi` - Show your API key & usage\n"
        "• `/search <song>` - Search song\n"
        "• `/stream <url>` - Get audio URL\n"
        "• `/recommend <song>` - AI recommendations\n"
        "• `/batch <song1> <song2> ...` - Multiple songs\n\n"
    )
    
    if is_admin_user:
        msg += (
            "👑 **Admin Commands:**\n"
            "• `/generatekey @username` - Generate key for friend\n"
            "• `/listkeys` - List all generated keys\n"
            "• `/revokekey <key>` - Revoke a key\n"
            "• `/admins` - List all admins\n"
            "• `/addadmin <user_id>` - Add new admin (Owner only)\n"
            "• `/removeadmin <user_id>` - Remove admin (Owner only)\n\n"
        )
    
    msg += f"⚡ **Daily Limit:** {DAILY_LIMIT} requests/day"
    await update.message.reply_text(msg)

# ===================== ADMIN MANAGEMENT =====================

async def admins_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all admins"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    
    msg = "👑 **Admin List**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for admin_id in ADMINS:
        role = "👑 Owner" if admin_id == OWNER_ID else "🛡️ Admin"
        msg += f"• `{admin_id}` - {role}\n"
    
    msg += f"\n📊 **Total Admins:** {len(ADMINS)}"
    await update.message.reply_text(msg)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new admin (Owner only)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can add admins.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/addadmin <user_id>`")
        return
    
    try:
        new_admin = int(context.args[0])
        if new_admin in ADMINS:
            await update.message.reply_text(f"❌ User `{new_admin}` is already an admin.")
            return
        
        ADMINS.append(new_admin)
        # Save to env or file for persistence
        admins_data = load_json("admins.json")
        admins_data["admins"] = ADMINS
        save_json("admins.json", admins_data)
        
        await update.message.reply_text(
            f"✅ **Admin Added!**\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 User ID: `{new_admin}`\n"
            f"👤 Added by: `{update.effective_user.id}`"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove an admin (Owner only)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can remove admins.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/removeadmin <user_id>`")
        return
    
    try:
        admin_to_remove = int(context.args[0])
        
        if admin_to_remove == OWNER_ID:
            await update.message.reply_text("❌ Cannot remove the owner.")
            return
        
        if admin_to_remove not in ADMINS:
            await update.message.reply_text(f"❌ User `{admin_to_remove}` is not an admin.")
            return
        
        ADMINS.remove(admin_to_remove)
        
        admins_data = load_json("admins.json")
        admins_data["admins"] = ADMINS
        save_json("admins.json", admins_data)
        
        await update.message.reply_text(
            f"✅ **Admin Removed!**\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 User ID: `{admin_to_remove}`\n"
            f"👤 Removed by: `{update.effective_user.id}`"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

# ===================== KEY GENERATION COMMANDS =====================

async def generatekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized. Only admins can generate keys.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/generatekey @username`\nExample: `/generatekey @rajkumar`")
        return
    
    friend_username = context.args[0]
    new_key = generate_new_key(friend_username, update.effective_user.id)
    
    await update.message.reply_text(
        f"🔑 **New API Key Generated!**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Friend:** {friend_username}\n"
        f"🔑 **API Key:** `{new_key}`\n"
        f"📅 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👤 **Generated by:** `{update.effective_user.id}`\n\n"
        f"📌 Send this key to your friend!"
    )

async def listkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    
    keys = load_json(GENERATED_KEYS_FILE)
    
    if not keys:
        await update.message.reply_text("📭 No keys generated yet.")
        return
    
    message = "🔑 **Generated API Keys**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for key, info in list(keys.items())[:20]:
        status = "✅ Active" if info.get('is_active', True) else "❌ Revoked"
        message += f"\n• `{key[:20]}...`\n  👤 {info.get('username', 'Unknown')} | {status}"
    
    message += f"\n\n📊 **Total Keys:** {len(keys)}"
    await update.message.reply_text(message)

async def revokekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/revokekey <key>`")
        return
    
    key_to_revoke = context.args[0]
    keys = load_json(GENERATED_KEYS_FILE)
    
    if key_to_revoke not in keys:
        await update.message.reply_text("❌ Key not found.")
        return
    
    keys[key_to_revoke]['is_active'] = False
    save_json(GENERATED_KEYS_FILE, keys)
    
    await update.message.reply_text(
        f"✅ **Key Revoked!**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 Key: `{key_to_revoke[:20]}...`\n"
        f"👤 Revoked by: `{update.effective_user.id}`"
    )

# ===================== MUSIC COMMANDS =====================

async def getapi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    api_key = get_user_api_key(user_id)
    usage = get_user_usage(user_id)
    remaining = DAILY_LIMIT - usage
    
    await update.message.reply_text(
        f"🔑 **Your API Key**\n━━━━━━━━━━━━━━━━━━━━━━\n`{api_key}`\n\n"
        f"📊 **Usage:** {usage}/{DAILY_LIMIT}\n⏳ **Remaining:** {remaining}\n\n"
        f"⚠️ Keep your API key secret!"
    )

async def myapi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keys = load_json(API_KEYS_FILE)
    user_id_str = str(user_id)
    
    if user_id_str not in keys:
        await update.message.reply_text("❌ No API key found. Use `/getapi` to generate one.")
        return
    
    api_key = keys[user_id_str]["api_key"]
    created = datetime.fromtimestamp(keys[user_id_str]["created_at"]).strftime("%Y-%m-%d %H:%M")
    usage = get_user_usage(user_id)
    remaining = DAILY_LIMIT - usage
    
    await update.message.reply_text(
        f"🔑 **Your API Key Details**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **Key:** `{api_key}`\n📅 **Created:** {created}\n"
        f"📊 **Today's Usage:** {usage}/{DAILY_LIMIT}\n⏳ **Remaining:** {remaining}\n"
        f"✅ **Status:** {'Active' if keys[user_id_str]['is_active'] else 'Revoked'}"
    )

# ===================== MUSIC SEARCH COMMANDS =====================

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/search <song_name>`")
        return
    
    user_id = update.effective_user.id
    
    if not can_make_request(user_id):
        await update.message.reply_text(f"⛔ **Daily limit reached!** ({DAILY_LIMIT}/{DAILY_LIMIT})")
        return
    
    query = " ".join(context.args)
    api_key = get_user_api_key(user_id)
    
    await update.message.reply_text(f"🔍 Searching for `{query}`...")
    
    results, error = call_api("search", {"query": query}, api_key=api_key)
    
    if error:
        await update.message.reply_text(f"❌ Error: {error}")
        return
    
    increment_usage(user_id)
    
    if not results:
        await update.message.reply_text(f"❌ No results found for `{query}`")
        return
    
    keyboard = []
    for song in results[:5]:
        title = song.get('name', 'Unknown')[:40]
        url = song.get('url', '')
        keyboard.append([InlineKeyboardButton(f"🎵 {title}", callback_data=f"stream_{url}")])
    
    await update.message.reply_text(
        f"🎵 **Results for:** `{query}`\n\n📊 Found {len(results)} songs.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/stream <youtube_url>`")
        return
    
    user_id = update.effective_user.id
    
    if not can_make_request(user_id):
        await update.message.reply_text(f"⛔ **Daily limit reached!**")
        return
    
    url = context.args[0]
    api_key = get_user_api_key(user_id)
    
    await update.message.reply_text("🔄 Getting stream URL...")
    
    result, error = call_api("stream", {"url": url}, api_key=api_key)
    
    if error:
        await update.message.reply_text(f"❌ Error: {error}")
        return
    
    increment_usage(user_id)
    
    if result and result.get('stream_url'):
        await update.message.reply_text(
            f"🎵 **Stream URL Ready!**\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 `{result['stream_url']}`\n\n"
            f"🎵 **Title:** {result.get('title', 'Unknown')}"
        )
    else:
        await update.message.reply_text("❌ Failed to get stream URL")

async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/recommend <song_name>`")
        return
    
    user_id = update.effective_user.id
    
    if not can_make_request(user_id):
        await update.message.reply_text(f"⛔ **Daily limit reached!**")
        return
    
    query = " ".join(context.args)
    api_key = get_user_api_key(user_id)
    
    await update.message.reply_text(f"🤖 Getting recommendations for `{query}`...")
    
    results, error = call_api("recommendations", {"song": query}, api_key=api_key)
    
    if error:
        await update.message.reply_text(f"❌ Error: {error}")
        return
    
    increment_usage(user_id)
    
    if results:
        songs = results[:10]
        await update.message.reply_text(
            f"🎵 **AI Recommendations for:** `{query}`\n━━━━━━━━━━━━━━━━━━━━━━\n" +
            "\n".join(f"{i+1}. {s}" for i, s in enumerate(songs))
        )
    else:
        await update.message.reply_text("❌ No recommendations found")

async def batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/batch <song1> <song2> <song3> ...`")
        return
    
    user_id = update.effective_user.id
    
    if not can_make_request(user_id):
        await update.message.reply_text(f"⛔ **Daily limit reached!**")
        return
    
    queries = context.args
    api_key = get_user_api_key(user_id)
    
    await update.message.reply_text(f"🔍 Searching {len(queries)} songs...")
    
    results, error = call_api("batch", json_data={"queries": queries}, api_key=api_key)
    
    if error:
        await update.message.reply_text(f"❌ Error: {error}")
        return
    
    increment_usage(user_id)
    
    if results:
        for song in results[:10]:
            await update.message.reply_text(
                f"🎵 **{song.get('name', 'Unknown')}**\n"
                f"👤 {song.get('artist_name', 'Unknown')}\n"
                f"🔗 {song.get('url', '')}"
            )
    else:
        await update.message.reply_text("❌ No results found")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("stream_"):
        user_id = query.from_user.id
        
        if not can_make_request(user_id):
            await query.message.reply_text(f"⛔ **Daily limit reached!**")
            return
        
        url = query.data.replace("stream_", "")
        api_key = get_user_api_key(user_id)
        
        await query.message.reply_text("🔄 Getting stream...")
        
        result, error = call_api("stream", {"url": url}, api_key=api_key)
        
        if error:
            await query.message.reply_text(f"❌ Error: {error}")
            return
        
        increment_usage(user_id)
        
        if result and result.get('stream_url'):
            await query.message.reply_text(f"🎵 **Stream URL:**\n`{result['stream_url']}`")
        else:
            await query.message.reply_text("❌ Failed")

# ===================== MAIN =====================

async def start_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getapi", getapi))
    app.add_handler(CommandHandler("myapi", myapi))
    
    # Music commands
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stream", stream))
    app.add_handler(CommandHandler("recommend", recommend))
    app.add_handler(CommandHandler("batch", batch))
    
    # Admin commands
    app.add_handler(CommandHandler("admins", admins_list))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("generatekey", generatekey))
    app.add_handler(CommandHandler("listkeys", listkeys))
    app.add_handler(CommandHandler("revokekey", revokekey))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🎵 Music Bot Started!")
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(start_bot())
