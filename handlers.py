from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import Database

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Use o comando /inscrever HH:MM 'Mensagem' para adicionar um lembrete.\n"
        "/listar para ver seus lembretes.\n"
        "/limpar para apagar todos os lembretes."
    )

async def inscrever(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Formato inválido! Use: /inscrever HH:MM")
        return

    horario = context.args[0]
    mensagem = "🔔 Lembrete diário!"
    if len(context.args) > 1:
        mensagem = " ".join(context.args[1:])

    try:
        from datetime import datetime
        datetime.strptime(horario, "%H:%M")
    except ValueError:
        await update.message.reply_text("Formato inválido! Use HH:MM (exemplo: 14:30)")
        return

    user_id = update.message.chat_id
    limite = db.get_limit()

    if len(db.get_user_reminders(user_id)) >= limite:
        await update.message.reply_text(f"⚠️ Você já tem {limite} horários cadastrados. O limite é {limite}.")
        return

    db.add_reminder(user_id, horario, mensagem)
    await update.message.reply_text(f"✅ Inscrição confirmada! Você receberá '{mensagem}' todo dia às {horario}.")

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.delete_user_reminders(update.message.chat_id)
    await update.message.reply_text("Todos os seus alertas foram removidos.")

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = db.get_user_reminders(update.message.chat_id)
    if not reminders:
        await update.message.reply_text("Sem alertas registrados.")
    else:
        mensagem = "\n".join(f"{horario} - {msg}" for horario, msg in reminders)
        await update.message.reply_text(mensagem)

async def limite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Parâmetros inválidos. Exemplo: /limite 3")
        return

    try:
        valor = int(context.args[0])
        db.set_limit(valor)
        await update.message.reply_text(f"Limite ajustado para {valor}.")
    except ValueError:
        await update.message.reply_text("O valor do limite deve ser um número inteiro.")