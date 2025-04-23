import asyncio
import os
from telegram.ext import ApplicationBuilder
if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    application = application = ApplicationBuilder().token(token).build()
    asyncio.run(application.bot.set_webhook(
        url=os.getenv("WEBHOOK_URL"),
        secret_token=os.getenv("WEBHOOK_SECRET_TOKEN"),
    ))
    print("Webhook set successfully.")