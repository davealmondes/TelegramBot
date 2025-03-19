from datetime import datetime
from typing import Any
from database import Database

db = Database()

async def callback30(context :Any):
    now :str = datetime.now().strftime("%H:%M")
    reminders: list[Any] = db.get_lembretes_a_enviar(now)

    for id, usuario_id, mensagem in reminders:
        await context.bot.send_message(chat_id=usuario_id, text=mensagem)
        db.update_enviado_em(id)