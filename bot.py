#!/usr/bin/env python3
"""
🎵 Music Bot with API Key Generator - Fixed Version
"""

import os
import json
import time
import secrets
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ===================== CONFIGURATION =====================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8736103437:AAH5NaIL-IehHboCIM7nPgGpyIaynZpiyOc")
OWNER_ID = int(os.environ.get("OWNER_ID", 8041502308))
API_BASE_URL = os.environ.get("API_BASE_URL", "https://zyra-yt-dlp-api.vercel.app")
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", 500))

# ===================== ADMINS =====================

ADMINS = os.environ.get("ADMINS", "").split(",")
ADMINS = [int(a.strip()) for a in ADMINS if a.strip().isdigit()]

if not ADMINS:
    ADMINS = [8041502308]

if OWNER_ID not in ADMINS:
    ADMINS.append(OWNER_ID)

def is_admin(user_id):
    return user_id in ADMINS or user_id == OWNER_ID

# ===================== DATA MANAGEMENT =====================

API_KEYS_FILE = "api_keys.json"
USAGE_FILE = "usage.json"
GENERATED_KEYS_FILE = "generated_keys.json"

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

# ===================== COMMAND HANDLERS =====================

def start(update: Update, context):
    user = update.effective_user
    msg = (
        f"🎵 **Welcome {user.first_name}!**\n\n"
        "📋 **Commands:**\n"
        "• `/getapi` - Get your free API key\n"
        "• `/myapi` - Show your API key & usage\n"
        "• `/search <song>` - Search song\n"
        "• `/stream <url>` - Get audio URL\n"
        "• `/recommend <song>` - AI recommendations\n"
        "• `/batch <song1> <song2> ...` - Multiple songs\n\n"
        f"⚡ **Daily Limit:** {DAILY_LIMIT} requests/day"
    )
    if is_admin(user.id):
        msg += (
            "\n👑 **Admin Commands:**\n"
            "• `/generatekey @username` - Generate key\n"
            "• `/listkeys` - List all keys\n"
            "• `/revokekey <key>` - Revoke a key\n"
            "• `/admins` - List all admins"
        )
    update.message.reply_text(msg)

def getapi(update: Update, context):
    user_id = update.effective_user.id
    api_key = get_user_api_key(user_id)
    usage = get_user_usage(user_id)
    remaining = DAILY_LIMIT - usage
    
    update.message.reply_text(
        f"🔑 **Your API Key**\n━━━━━━━━━━━━━━━━━━━━━━\n`{api_key}`\n\n"
        f"📊 **Usage:** {usage}/{DAILY_LIMIT}\n⏳ **Remaining:** {remaining}"
    )

def search(update: Update, context):
    if not context.args:
        update.message.reply_text("❌ Usage: `/search <song_name>`")
        return
    
    user_id = update.effective_user.id
    
    if not can_make_request(user_id):
        update.message.reply_text(f"⛔ **Daily limit reached!**")
        return
    
    query = " ".join(context.args)
    api_key = get_user_api_key(user_id)
    
    update.message.reply_text(f"🔍 Searching for `{query}`...")
    
    results, error = call_api("search", {"query": query}, api_key=api_key)
    
    if error:
        update.message.reply_text(f"❌ Error: {error}")
        return
    
    increment_usage(user_id)
    
    if not results:
        update.message.reply_text(f"❌ No results found for `{query}`")
        return
    
    keyboard = []
    for song in results[:5]:
        title = song.get('name', 'Unknown')[:40]
        url = song.get('url', '')
        keyboard.append([InlineKeyboardButton(f"🎵 {title}", callback_data=f"stream_{url}")])
    
    update.message.reply_text(
        f"🎵 **Results for:** `{query}`",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def callback_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    
    if query.data.startswith("stream_"):
        user_id = query.from_user.id
        
        if not can_make_request(user_id):
            query.message.reply_text(f"⛔ **Daily limit reached!**")
            return
        
        url = query.data.replace("stream_", "")
        api_key = get_user_api_key(user_id)
        
        query.message.reply_text("🔄 Getting stream...")
        
        result, error = call_api("stream", {"url": url}, api_key=api_key)
        
        if error:
            query.message.reply_text(f"❌ Error: {error}")
            return
        
        increment_usage(user_id)
        
        if result and result.get('stream_url'):
            query.message.reply_text(f"🎵 **Stream URL:**\n`{result['stream_url']}`")
        else:
            query.message.reply_text("❌ Failed")

def generatekey(update: Update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("❌ Unauthorized.")
        return
    
    if not context.args:
        update.message.reply_text("❌ Usage: `/generatekey @username`")
        return
    
    friend = context.args[0]
    new_key = generate_new_key(friend, update.effective_user.id)
    
    update.message.reply_text(
        f"🔑 **New Key Generated!**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Friend: {friend}\n🔑 Key: `{new_key}`"
    )

def listkeys(update: Update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("❌ Unauthorized.")
        return
    
    keys = load_json(GENERATED_KEYS_FILE)
    
    if not keys:
        update.message.reply_text("📭 No keys generated yet.")
        return
    
    msg = "🔑 **Generated Keys**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for key, info in list(keys.items())[:20]:
        status = "✅ Active" if info.get('is_active', True) else "❌ Revoked"
        msg += f"\n• `{key[:20]}...`\n  👤 {info.get('username', 'Unknown')} | {status}"
    
    msg += f"\n\n📊 Total: {len(keys)}"
    update.message.reply_text(msg)

def revokekey(update: Update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("❌ Unauthorized.")
        return
    
    if not context.args:
        update.message.reply_text("❌ Usage: `/revokekey <key>`")
        return
    
    key = context.args[0]
    keys = load_json(GENERATED_KEYS_FILE)
    
    if key not in keys:
        update.message.reply_text("❌ Key not found.")
        return
    
    keys[key]['is_active'] = False
    save_json(GENERATED_KEYS_FILE, keys)
    update.message.reply_text(f"✅ Key `{key[:20]}...` revoked.")

def admins_list(update: Update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("❌ Unauthorized.")
        return
    
    msg = "👑 **Admins**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for aid in ADMINS:
        role = "👑 Owner" if aid == OWNER_ID else "🛡️ Admin"
        msg += f"• `{aid}` - {role}\n"
    update.message.reply_text(msg)

# ===================== MAIN =====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getapi", getapi))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("generatekey", generatekey))
    app.add_handler(CommandHandler("listkeys", listkeys))
    app.add_handler(CommandHandler("revokekey", revokekey))
    app.add_handler(CommandHandler("admins", admins_list))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🎵 Bot Started!")
    app.run_polling()

if __name__ == "__main__":
    main()
