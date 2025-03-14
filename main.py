import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from handlers import start, inscrever, limpar, listar, limite
from jobs import callback30

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    job_queue = application.job_queue
    job_queue.run_repeating(callback30, interval=30, first=1)

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('inscrever', inscrever))
    application.add_handler(CommandHandler('limpar', limpar))
    application.add_handler(CommandHandler('listar', listar))
    application.add_handler(CommandHandler('limite', limite))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    application.run_polling()

if __name__ == '__main__':
    main()