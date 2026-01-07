"""
Vercel Serverless Function for Telegram Bot
Path: api/webhook.py
"""

import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("FILE_SERVER_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID"))

F_SUB_CHANNEL_ID = int(os.getenv("F_SUB_CHANNEL_ID"))
F_SUB_CHANNEL_LINK = os.getenv("F_SUB_CHANNEL_LINK")

MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGO_DB_NAME")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "mappings")

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- MONGODB ----------------
try:
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB]
    mappings_col = mongo_db[MONGO_COLLECTION]
except PyMongoError as e:
    logger.error(f"❌ MongoDB connection failed: {e}")
    mappings_col = None

# ---------------- UTIL ----------------
async def is_user_joined(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(F_SUB_CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

def join_keyboard(mapping: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Now ✅", url=F_SUB_CHANNEL_LINK)],
        [InlineKeyboardButton("Join & Get File ♻️", url=f"https://t.me/{BOT_USERNAME}?start={mapping}")]
    ])

# ---------------- START HANDLER ----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if not context.args:
        logger.warning(f"⚠️ Invalid access by {user_id} (@{username})")
        await update.message.reply_text("❌ Invalid access.\nUse a valid file link.")
        return

    mapping = context.args[0]

    # Force Join Check
    joined = await is_user_joined(context.bot, user_id)
    if not joined:
        logger.info(f"📌 Force Join: {user_id} (@{username}) - {mapping}")
        await update.message.reply_text(
            "⚠️ You have not joined the main channel yet.\nTo access this file, please join the main channel first 👇",
            reply_markup=join_keyboard(mapping),
            disable_web_page_preview=True,
        )
        return

    # MongoDB Lookup
    if not mappings_col:
        await update.message.reply_text("❌ Database error. Try again later.")
        return
        
    doc = mappings_col.find_one({"mapping": mapping})
    if not doc or "message_id" not in doc:
        logger.warning(f"⚠️ File not found: {mapping} (user: {user_id})")
        await update.message.reply_text("❌ File not found or link expired.")
        return

    message_id = int(doc["message_id"])

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_DOCUMENT,
        )

        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=STORAGE_CHANNEL_ID,
            message_id=message_id,
        )
        
        logger.info(f"✅ File sent: {user_id} (@{username}) - msg_id: {message_id}")

    except Exception as e:
        logger.error(f"❌ Copy failed for {user_id}: {str(e)}")
        await update.message.reply_text("❌ File not found or access denied.")

# ---------------- APPLICATION BUILDER ----------------
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start_handler))

# ---------------- VERCEL HANDLER ----------------
async def handler(request):
    """Vercel serverless function handler"""
    if request.method == "POST":
        try:
            # Parse incoming update
            body = await request.body()
            update_data = json.loads(body.decode('utf-8'))
            
            # Process update
            update = Update.de_json(update_data, application.bot)
            await application.process_update(update)
            
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "ok"})
            }
        except Exception as e:
            logger.error(f"❌ Error processing update: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }
    
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "Bot is running"})
    }

# For Vercel
def lambda_handler(event, context):
    """AWS Lambda / Vercel compatibility"""
    import asyncio
    
    class Request:
        def __init__(self, event):
            self.method = event.get('httpMethod', 'GET')
            self._body = event.get('body', '').encode('utf-8')
        
        async def body(self):
            return self._body
    
    return asyncio.run(handler(Request(event)))
