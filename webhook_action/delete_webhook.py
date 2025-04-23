import asyncio
import os
from telegram.ext import ApplicationBuilder
if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    application = application = ApplicationBuilder().token(token).build()
    asyncio.run(application.bot.delete_webhook())
    print("Webhook deleted successfully.")