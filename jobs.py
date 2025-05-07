from datetime import datetime
from typing import Any
from database import Database
from telegram.ext import ContextTypes

db = Database()

async def callback30(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Executa a cada 30s para enviar lembretes pendentes."""
    now = datetime.now().strftime("%H:%M")
    reminders = db.get_lembretes_a_enviar(now)

    for lembrete_id, usuario_id, mensagem in reminders:
        try:
            await context.bot.send_message(chat_id=usuario_id, text=mensagem)
            db.update_enviado_em(lembrete_id)
        except Exception as e:
            print(f"Erro ao enviar lembrete {lembrete_id}: {e}")
