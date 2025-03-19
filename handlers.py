from typing import Any
from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from datetime import datetime

db = Database()

# Estados para a conversa de edição
EDIT_CHOOSE, EDIT_FIELD, EDIT_TIME, EDIT_MESSAGE = range(4)


async def start(update: Update, _) -> None:
    usuario_id: int = update.message.chat_id
    nome: str = update.message.from_user.first_name
    nomeusuario: str = update.message.from_user.username
    idioma: str = update.message.from_user.language_code
    db.add_usuario(usuario_id, nomeusuario, nome, idioma)
    await update.message.reply_text("Bem vindo ao bot de lembrete. Digite /ajuda para ver a lista de comandos")

async def ajuda(update: Update, _) -> None:
    await update.message.reply_text("Os comandos disponíveis são:\n"
    "/inscrever HH:MM 'Mensagem' Para adicionar um lembrete\n"
    "/listar para ver seus lembretes\n"
    "/editar para editar um de seus lembretes\n"
    "/limpar para apagar todos os seus lembretes")

async def inscrever(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    usuario: Any = db.get_usuario(update.message.chat_id)
    if not usuario:
        await update.message.reply_text("Para pode começar: /start")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Formato inválido! Use: /inscrever HH:MM. Exemplo 12:00")
        return

    horario :str = context.args[0]
    if len(horario) != 5:
        await update.message.reply_text("Formato inválido! Use: /inscrever HH:MM. Exemplo 12:00")
        return
    
    mensagem = "🔔 Lembrete diário!" # Mensagem padrão
    if len(context.args) > 1:
        mensagem = " ".join(context.args[1:])

    try:
        datetime.strptime(horario, "%H:%M")
    except ValueError:
        await update.message.reply_text("Formato inválido! Use HH:MM (exemplo: 14:30)")
        return

    usuario_id :int = update.message.chat_id
    limite :int = db.get_limite()

    if len(db.get_lembretes_usuarios(usuario_id)) >= limite:
        await update.message.reply_text(f"⚠️ Você já tem {limite} lembretes cadastrados. O limite é {limite}.")
        return

    db.add_lembrete(usuario_id, horario, mensagem)
    await update.message.reply_text(f"✅ Inscrição confirmada! Você receberá '{mensagem}' todo dia às {horario}.")

async def limpar(update: Update, _) -> None:
    keyboard = [
        [InlineKeyboardButton("Sim", callback_data="limpar_sim")],
        [InlineKeyboardButton("Não", callback_data="limpar_nao")]
    ]
    await update.message.reply_text("Certeza que deseja apagar todos os seus lembretes?", reply_markup=InlineKeyboardMarkup(keyboard))

async def apagar_lembretes(update: Update, _) -> None:
    print("[DEBUG] Apagando lembretes...")
    query: CallbackQuery|None = update.callback_query
    usuario_id = query.message.chat_id
    opcao: str = query.data.split("_")[1]
    if opcao == 'sim':
        db.delete_lembretes_usuario(usuario_id)
        await query.edit_message_text("✅ Todos os seus lembretes foram apagados.")
    else:
        await query.edit_message_text("❌ Operação cancelada.")
    return ConversationHandler.END

async def listar(update: Update, _):
    lembretes :list[Any] = db.get_lembretes_usuarios(update.message.chat_id)
    if not lembretes:
        await update.message.reply_text("Sem lembretes registrados.")
        return
    
    keyboard = [
        [InlineKeyboardButton(f"✏️ {horario} - {mensagem[:15]}...", callback_data=f"info_{id}")]
        for id, horario, mensagem in lembretes
    ]
    await update.message.reply_text("📋 Seus Lembretes:", reply_markup=InlineKeyboardMarkup(keyboard))

async def editar(update: Update, _) -> int|None:
    usuario_id :int = update.message.chat_id
    lembretes :list[Any] = db.get_lembretes_usuarios(usuario_id)
    if not lembretes:
        await update.message.reply_text("❌ Você não tem lembretes para editar.")
        return
    
    keyboard = [
        [InlineKeyboardButton(f"{horario} - {mensagem[:10]}...", callback_data=f"editar_{id}")]
        for id, horario, mensagem in lembretes
    ]
    await update.message.reply_text("📝 Selecione o lembre que deseja editar: ", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_CHOOSE

async def escolher_campo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query :CallbackQuery|None = update.callback_query
    lembrete_id :int = query.data.split("_")[1]
    context.user_data['editando_lembrete'] = lembrete_id

    keyboard = [
        [InlineKeyboardButton("⏰ Horário", callback_data="horario")],
        [InlineKeyboardButton("📩 Mensagem", callback_data="mensagem")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]
    ]
    
    await query.edit_message_text("O que deseja editar?", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_FIELD

async def editar_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query :CallbackQuery|None = update.callback_query
    context.user_data['modo_de_edicao'] = 'horario'
    await query.edit_message_text("⏱️ Digite o novo horário (formato HH:MM): ")
    return EDIT_TIME

async def editar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query :CallbackQuery|None = update.callback_query
    context.user_data['modo_de_edicao'] = 'mensagem'
    await query.edit_message_text("📝 Digite a nova mensagem: ")
    return EDIT_MESSAGE

async def salvar_alteracoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lembrete_id :int = context.user_data['editando_lembrete']
    texto :str = update.message.text

    if context.user_data['modo_de_edicao'] == 'horario':
        try:
            datetime.strptime(texto, "%H:%M")
            db.update_lembrete(lembrete_id, novo_horario=texto)
            await update.message.reply_text("✅ Horário atualizado com sucesso.")
        except ValueError:
            await update.message.reply_text("❌ Formato inválido! Use HH:MM")

    else:
        db.update_lembrete(lembrete_id, nova_mensagem=texto)
        await update.message.reply_text("✅ Mensagem atualizada com sucesso.")

    return ConversationHandler.END

async def cancelar_edicao(update: Update, _) -> int:
    query :CallbackQuery|None = update.callback_query
    await query.edit_message_text("❌ Edição cancelada")
    return ConversationHandler.END

async def mostrar_detalhes_lembrete(update: Update, _) -> None:
    query :CallbackQuery|None = update.callback_query
    lembrete_id :int = query.data.split("_")[1]
    lembrete :Any = db.get_lembrete_por_id(lembrete_id)

    if lembrete:
        await query.edit_message_text(f"📆 Lembrete: \nHorário: {lembrete[0]}\nMensagem: {lembrete[1]}")
    else:
        await query.edit_message_text("❌ Lembrete não encontrado.")

async def limite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Parâmetros inválidos. Exemplo: /limite 3")
        return

    try:
        limite :int = int(context.args[0]) if int(context.args[0]) > 0 else 1
        db.set_limite(limite)
        await update.message.reply_text(f"Limite ajustado para {limite}.")
    except ValueError:
        await update.message.reply_text("O valor do limite deve ser um número inteiro.")

def limite(admin_id: str):
    async def limite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message.chat_id != admin_id:
            await update.message.reply_text("Comando disponível apenas para administradores.")
            return
        if len(context.args) != 1:
            await update.message.reply_text("Parâmetros inválidos. Exemplo: /limite 3")
            return

        try:
            limite :int = int(context.args[0]) if int(context.args[0]) > 0 else 1
            db.set_limite(limite)
            await update.message.reply_text(f"Limite ajustado para {limite}.")
        except ValueError:
            await update.message.reply_text("O valor do limite deve ser um número inteiro.")
    return limite
    