import logging
import re
import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Read environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7754090875:AAFvORs24VyZojKEqoNoX4nD6kfYZOlzbW8")
# Validate environment variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")

# AdLinkFly API endpoint
ADLINKFLY_API_URL = "https://adlinkfly.com/api"

# Regular expression to find URLs in text
URL_REGEX = re.compile(r'https?://[^\s]+')

# File to store user API keys
API_KEY_FILE = "user_api_keys.json"

# Load user API keys from file
def load_api_keys():
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as file:
            return json.load(file)
    return {}

# Save user API keys to file
def save_api_keys(api_keys):
    with open(API_KEY_FILE, "w") as file:
        json.dump(api_keys, file)

# In-memory storage for user API keys
user_api_keys = load_api_keys()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    start_message = (
        "🤖 Welcome to AdLinkFly Bulk Link Shortener Bot!\n\n"
        "📌 **How to use:**\n"
        "1. Set your AdLinkFly API key using the /setapi command.\n"
        "2. Send or forward me a message containing links.\n"
        "3. I will find all the links, shorten them, and return the text with shortened links.\n\n"
        "⚙️ **Commands:**\n"
        "/start - Start the bot\n"
        "/help - Get help\n"
        "/setapi <API_KEY> - Set your AdLinkFly API key\n"
        "/logout - Remove your API key\n\n"
        "Made with ❤️ by YourName"
    )
    await update.message.reply_text(start_message)

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = (
        "🆘 **Help:**\n"
        "1. Set your AdLinkFly API key using the /setapi command.\n"
        "   Example: `/setapi 04e8ee10b5f123456a640c8f33195abc`\n\n"
        "2. Send or forward me a message containing links.\n"
        "3. I will automatically detect and shorten all links in the text.\n"
        "4. I will return the same text with the links replaced by shortened ones.\n\n"
        "Example:\n"
        "Input: `Check out https://example.com and https://anotherexample.com`\n"
        "Output: `Check out https://adlinkfly.com/abc123 and https://adlinkfly.com/xyz456`"
    )
    await update.message.reply_text(help_message)

# Set API key command handler
async def set_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.message.from_user.id
        api_key = context.args[0] if context.args else None

        if not api_key:
            await update.message.reply_text("❌ Please provide an API key. Example: `/setapi 04e8ee10b5f123456a640c8f33195abc`")
            return

        # Store the API key in memory and save to file
        user_api_keys[user_id] = api_key
        save_api_keys(user_api_keys)
        await update.message.reply_text("✅ API key set successfully!")
    except Exception as e:
        logger.error(f"Error setting API key: {e}")
        await update.message.reply_text("❌ An error occurred while setting your API key. Please try again.")

# Logout command handler
async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.message.from_user.id
        if user_id in user_api_keys:
            del user_api_keys[user_id]
            save_api_keys(user_api_keys)
            await update.message.reply_text("✅ You have been logged out. Your API key has been removed.")
        else:
            await update.message.reply_text("❌ You are not logged in.")
    except Exception as e:
        logger.error(f"Error logging out: {e}")
        await update.message.reply_text("❌ An error occurred while logging out. Please try again.")

# Function to shorten a single link using AdLinkFly API
def shorten_link(link: str, api_key: str) -> str:
    try:
        params = {"api": api_key, "url": link}
        response = requests.get(ADLINKFLY_API_URL, params=params)
        return response.json().get("shortenedUrl", link) if response.status_code == 200 else link
    except Exception as e:
        logger.error(f"Error shortening link: {e}")
        return link

# Process text and replace links (skip Telegram links)
def process_text(text: str, api_key: str) -> str:
    def replace_link(match):
        link = match.group(0)
        if "https://t.me/" in link:
            return link  # Skip Telegram links
        return shorten_link(link, api_key)
    return URL_REGEX.sub(replace_link, text)

# Message handler for text, images, and captions
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.message.from_user.id
        api_key = user_api_keys.get(user_id)

        if not api_key:
            await update.message.reply_text("❌ Please set your AdLinkFly API key using the /setapi command.")
            return

        # Handle text messages
        if update.message.text:
            text = update.message.text
            processed_text = process_text(text, api_key)
            await update.message.reply_text(processed_text)

        # Handle images with captions
        elif update.message.caption:
            caption = update.message.caption
            processed_caption = process_text(caption, api_key)
            await update.message.reply_photo(update.message.photo[-1].file_id, caption=processed_caption)

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

# Main function
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setapi", set_api_key))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
