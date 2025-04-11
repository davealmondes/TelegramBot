from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from constantes import *
from database import Database

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa e registra o usuário se necessário."""
    inicio = context.user_data.get(INICIO)
    usuario_id = update.message.chat_id if update.message else update.callback_query.from_user.id

    if inicio is None:
        user = update.message.from_user if update.message else update.callback_query.from_user
        usuario = db.get_usuario(usuario_id)
        if not usuario:
            db.add_usuario(usuario_id, user.username, user.first_name, user.language_code)

    buttons = [
        [InlineKeyboardButton(text="Lembretes", callback_data=str(MENU_LEMBRETES))],
        [InlineKeyboardButton(text="Encerrar", callback_data=str(END))]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if not inicio:
        await update.message.reply_text(text="Bem-vindo!", reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_text("Bem-vindo!", reply_markup=keyboard)

    context.user_data[INICIO] = False
    return SELECAO_MENU

async def voltar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Retorna ao menu principal."""
    context.user_data[INICIO] = True
    await start(update, context)
    return END

async def encerrar(update: Update, _) -> int:
    """Encerra a conversa."""
    if update.message:
        await update.message.reply_text("❌ Conversa encerrada")
    else:
        await update.callback_query.edit_message_text("❌ Conversa encerrada")
    return END
