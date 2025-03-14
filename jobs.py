from datetime import datetime
from database import Database

db = Database()

async def callback30(context):
    now = datetime.now().strftime("%H:%M")
    day = datetime.now().strftime("%Y-%m-%d")
    reminders = db.get_reminders_for_time(now, day)

    for user_id, mensagem in reminders:
        await context.bot.send_message(chat_id=user_id, text=mensagem)
        db.update_last_sent(user_id, now, day)