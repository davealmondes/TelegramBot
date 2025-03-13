import logging
import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

# Conexão com o banco de dados SQLite
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER, horario TEXT, mensagem TEXT, last_sent TEXT, PRIMARY KEY (user_id, horario))")
cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value INTEGER)")
conn.commit()

async def callback30(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().strftime("%H:%M")
    day = datetime.now().strftime("%Y-%m-%d")
    print(f"Buscando usuário para {now}")
    cursor.execute("SELECT user_id, mensagem FROM users WHERE horario = ? and (last_sent is null or last_sent != ?)", (now, day))
    users = cursor.fetchall()
    for user in users:
        await context.bot.send_message(chat_id=user[0], text=user[1])
        cursor.execute("UPDATE users SET last_sent = ? where user_id = ? and horario = ?", (day, user[0], now))
        conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Use o comando /inscrever HH:MM 'Mensagem' para adicionar um lembrete \n"
    "/limpar para apagar todos os lembretes")

async def inscrever(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Formato inválido! Use: /inscrever HH:MM")
        return

    horario = context.args[0]
    mensagem = "🔔 Lembrete diário!"
    if len(context.args) > 1:
        mensagem = ""
        for i in range(len(context.args)):
            if i == 0:
                continue
            mensagem += f"{context.args[i]} "
        mensagem = mensagem.rstrip()
    try:
        datetime.strptime(horario, "%H:%M")  # Valida o formato
    except ValueError:
        await update.message.reply_text("Formato inválido! Use HH:MM (exemplo: 14:30)")
        return

    user_id = update.message.chat_id
    print(f"[DEBUG] Inscrevendo usuário {user_id} para {horario}")  # Depuração

    # Verifica limite
    cursor.execute("SELECT value FROM config WHERE key = 'limite'")
    limite = cursor.fetchone()
    limite = limite[0] if limite else 3  # Padrão: 3 agendamentos por usuário

    cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    
    if count >= limite:
        await update.message.reply_text(f"⚠️ Você já tem {count} horários cadastrados. O limite é {limite}.")
        return

    cursor.execute("INSERT OR IGNORE INTO users (user_id, horario, mensagem) VALUES (?, ?, ?)", (user_id, horario, mensagem))
    conn.commit()
    
    await update.message.reply_text(f"✅ Inscrição confirmada! Você receberá '{mensagem}' todo dia às {horario}.")

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.chat_id)
    cursor.execute("DELETE FROM users WHERE user_id = ?", (update.message.chat_id,))
    conn.commit()
    await update.message.reply_text("Todos os seus alertas foram removidos.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    job_queue = application.job_queue
    job_minute = job_queue.run_repeating(callback30, interval=30, first=1)  

    start_handler = CommandHandler('start', start)
    inscrever_handler = CommandHandler('inscrever', inscrever)
    limpar_handler = CommandHandler('limpar', limpar)
    message_handler = MessageHandler(filters.TEXT &  (~filters.COMMAND), start)
    application.add_handler(start_handler)
    application.add_handler(inscrever_handler)
    application.add_handler(limpar_handler)
    application.add_handler(message_handler)

    application.run_polling()