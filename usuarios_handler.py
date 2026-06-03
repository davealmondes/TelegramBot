"""
usuarios_handler.py
-------------------
Menu principal e ciclo de vida da conversa.
"""

from telegram import Message, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from constantes import *
from database import Database

db = Database()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa e registra o usuário se necessário."""
    inicio = context.user_data.get(INICIO)

    if update.message:
        usuario_id = update.message.chat_id
        user = update.message.from_user
    else:
        usuario_id = update.callback_query.from_user.id
        user = update.callback_query.from_user

    if inicio is None:
        if not db.get_usuario(usuario_id):
            db.add_usuario(usuario_id, user.username, user.first_name, user.language_code)

    buttons = [
        [InlineKeyboardButton(text="Ponto",     callback_data=str(MENU_PONTO))],
        [InlineKeyboardButton(text="Encerrar",  callback_data=str(END))],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    context.user_data.setdefault(MENSAGENS, [])
    mensagens: list[Message] = context.user_data[MENSAGENS]

    if not inicio:
        mensagens.append(update.message)
        mensagens.append(await update.message.reply_text("Bem-vindo! 👋", reply_markup=keyboard))
    else:
        mensagens.append(
            await update.callback_query.edit_message_text("Bem-vindo! 👋", reply_markup=keyboard)
        )

    context.user_data[INICIO] = False
    return SELECAO_MENU


async def voltar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Retorna ao menu principal."""
    context.user_data[INICIO] = True
    await start(update, context)
    return END


async def encerrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Encerra a conversa e remove todas as mensagens do chat."""
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])

    if update.message and update.message not in mensagens:
        try:
            await update.message.delete()
        except Exception:
            pass
    elif update.callback_query and update.callback_query.message not in mensagens:
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass

    while mensagens:
        msg = mensagens.pop()
        if msg:
            try:
                await msg.delete()
            except Exception:
                pass

    return END