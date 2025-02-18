import logging
import re
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your AdLinkFly API key and Telegram bot token
ADLINKFLY_API_KEY = "YOUR_ADLINKFLY_API_KEY"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# AdLinkFly API endpoint
ADLINKFLY_API_URL = "https://adlinkfly.com/api"

# Regular expression to find URLs in text
URL_REGEX = re.compile(r'https?://[^\s]+')

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    start_message = (
        "🤖 Welcome to AdLinkFly Bulk Link Shortener Bot!\n\n"
        "📌 **How to use:**\n"
        "1. Send or forward me a message containing links.\n"
        "2. I will find all the links, shorten them, and return the text with shortened links.\n\n"
        "⚙️ **Commands:**\n"
        "/start - Start the bot\n"
        "/help - Get help\n\n"
        "Made with ❤️ by YourName"
    )
    await update.message.reply_text(start_message)

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = (
        "🆘 **Help:**\n"
        "1. Send or forward me a message containing links.\n"
        "2. I will automatically detect and shorten all links in the text.\n"
        "3. I will return the same text with the links replaced by shortened ones.\n\n"
        "Example:\n"
        "Input: `Check out https://example.com and https://anotherexample.com`\n"
        "Output: `Check out https://adlinkfly.com/abc123 and https://adlinkfly.com/xyz456`"
    )
    await update.message.reply_text(help_message)

# Function to shorten a single link using AdLinkFly API
def shorten_link(link: str) -> str:
    try:
        params = {"api": ADLINKFLY_API_KEY, "url": link}
        response = requests.get(ADLINKFLY_API_URL, params=params)
        return response.json().get("shortenedUrl", link) if response.status_code == 200 else link
    except Exception as e:
        logger.error(f"Error shortening link: {e}")
        return link

# Process text and replace links
def process_text(text: str) -> str:
    return URL_REGEX.sub(lambda match: shorten_link(match.group(0)), text)

# Message handler for text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = update.message.text
        processed_text = process_text(text)
        await update.message.reply_text(processed_text)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

# Main function
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
