import logging
import re
import os
import aiohttp
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Read environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7754090875:AAFvORs24VyZojKEqoNoX4nD6kfYZOlzbW8")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://aaroha:aaroha@cluster0.pnzoc.mongodb.net/Cluster0?retryWrites=true&w=majority&appName=Cluster0")
ADLINKFLY_API_URL = "https://shortner.in/api"

# Validate environment variables
if not TELEGRAM_BOT_TOKEN or not MONGODB_URI:
    raise ValueError("Missing required environment variables.")

# Parse MongoDB URI to extract database name
parsed_uri = parse_uri(MONGODB_URI)
db_name = parsed_uri.get("database")
if not db_name:
    raise ValueError("Database name not found in MONGODB_URI.")

# Initialize MongoDB client and database
client = MongoClient(MONGODB_URI)
db = client[db_name]
users_collection = db["users"]

# Regular expression to find URLs in text
URL_REGEX = re.compile(r'https?://[^\s]+')

async def shorten_link(link: str, api_key: str) -> str:
    try:
        params = {"api": api_key, "url": link}
        async with aiohttp.ClientSession() as session:
            async with session.get(ADLINKFLY_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("shortenedUrl", link)
        return link
    except Exception as e:
        logger.error(f"Error shortening link: {e}")
        return link

async def process_text(text: str, api_key: str) -> str:
    async def replace_link(match):
        link = match.group(0)
        if "https://t.me/" in link:
            return link  # Skip Telegram links
        return await shorten_link(link, api_key)
    
    tasks = [replace_link(match) for match in URL_REGEX.finditer(text)]
    shortened_links = await asyncio.gather(*tasks)
    for match, shortened in zip(URL_REGEX.finditer(text), shortened_links):
        text = text.replace(match.group(0), shortened)
    return text

# Health check server
async def health_check(request):
    return web.Response(text="OK")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    logger.info("Health check server started on port 8000.")

# Telegram bot functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("🔗 Sign Up on Shortner.in", url="https://shortner.in/auth/signup")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    start_message = (
        "🤖 Welcome to AdLinkFly Bulk Link Shortener Bot!\n\n"
        "📌 **How to use:**\n"
        "1. Set your AdLinkFly API key using the /login command.\n"
        "2. Send or forward me a message containing links.\n"
        "3. I will find all the links, shorten them, and return the text with shortened links.\n\n"
        "⚙️ **Commands:**\n"
        "/start - Start the bot\n"
        "/help - Get help\n"
        "/login <API_KEY> - Set your AdLinkFly API key\n"
        "/logout - Remove your API key\n\n"
        "🔽 Click the button below to **Sign Up**:"
    )

    await update.message.reply_text(start_message, reply_markup=reply_markup)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = (
        "ℹ️ **Help**:\n\n"
        "1. **/start** - Start the bot and get basic instructions.\n"
        "2. **/login <API_KEY>** - Set your AdLinkFly API key.\n"
        "3. **/logout** - Logout and remove your API key.\n"
        "4. **Send links** - Send links to be shortened automatically.\n\n"
        "If you face any issues, please contact support."
    )
    await update.message.reply_text(help_message)

async def features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    features_message = (
        "🔧 **Features**:\n\n"
        "1. Automatically shorten any URL sent to the bot.\n"
        "2. Set your AdLinkFly API key for seamless link shortening.\n"
        "3. Get a list of your shortened links by interacting with the bot.\n"
        "4. Integration with MongoDB to store user preferences and API keys.\n\n"
        "If you have any feature requests, feel free to share!"
    )
    await update.message.reply_text(features_message)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.message.from_user.id
        api_key = context.args[0] if context.args else None
        if not api_key:
            await update.message.reply_text("Please provide an API key. Example: /login <API_KEY>")
            return
        users_collection.update_one({"user_id": user_id}, {"$set": {"api_key": api_key}}, upsert=True)
        context.user_data["api_key"] = api_key
        await update.message.reply_text("API key set successfully!")
    except Exception as e:
        logger.error(f"Error setting API key: {e}")
        await update.message.reply_text("An error occurred. Please try again.")

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    users_collection.delete_one({"user_id": user_id})
    context.user_data.pop("api_key", None)
    await update.message.reply_text("You have been logged out.")

async def main_async():
    # Build your Telegram bot application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("features", features))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("logout", logout))

    # Run both the health check server and the Telegram polling concurrently
    await asyncio.gather(
        start_health_server(),
        application.run_polling(),
    )

if __name__ == "__main__":
    asyncio.run(main_async())
