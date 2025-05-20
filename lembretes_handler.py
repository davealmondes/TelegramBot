from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from constantes import *
from database import Database
from utils import MSG_CANCELADO, MSG_HORARIO_INVALIDO, MSG_HORARIO_OBRIGATORIO, MSG_LIMITE, MSG_SEM_LEMBRETES, MSG_SUCESSO, botoes_confirmacao, parse_horario

db = Database()

async def menu_lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra o menu principal de lembretes."""
    texto = context.user_data.pop(TEXTO, 'Menu de lembretes...')
    context.user_data[EDITANDO] = None
    context.user_data[INICIO] = True

    buttons = [
        [
            InlineKeyboardButton(text='Adicionar um lembrete', callback_data=str(ADICIONAR)),
            InlineKeyboardButton(text='Listar Lembretes', callback_data=str(LISTAR_LEMBRETES))
        ],
        [InlineKeyboardButton(text="Apagar todos os seus lembretes", callback_data=str(LIMPAR_LEMBRETES))],
        [InlineKeyboardButton(text='Voltar', callback_data=str(END))]
    ]

    await update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECAO_MENU_LEMBRETE

async def campo_lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe campos a preencher/editáveis do lembrete."""
    
    if update.message:
        texto = "Campo atualizado..."
    else:
    
        lembretes = db.get_lembretes_usuarios(update.callback_query.from_user.id)
        limite = db.get_limite()

        if len(lembretes) >= limite and context.user_data.get(EDITANDO) is None :
            context.user_data[TEXTO] = MSG_LIMITE
            await menu_lembrete(update, context)
            return END

        if update.callback_query.data == str(EDITAR):
            context.user_data[CAMPOS] = {
                HORARIO: context.user_data[EDITANDO][1],
                MENSAGEM: context.user_data[EDITANDO][2],
            }
            texto = "Editando lembrete..."
        else:
            if context.user_data.get(INICIO):
                context.user_data[CAMPOS] = {}
                context.user_data[INICIO] = False
            texto = context.user_data.pop(TEXTO, "Adicionando lembrete...")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Horário", callback_data=str(HORARIO)),
        InlineKeyboardButton("Mensagem", callback_data=str(MENSAGEM))],
        [InlineKeyboardButton("Cancelar", callback_data=str(CANCELAR)),
        InlineKeyboardButton("Concluir", callback_data=str(END))]
    ])

    if update.message:
        await update.message.reply_text(texto, reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_text(texto, reply_markup=keyboard)
    return SELECIONANDO_CAMPO

async def valor_campo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    campo = update.callback_query.data
    context.user_data[CAMPO_SELECIONADO] = campo
    atual = context.user_data.get(CAMPOS, {}).get(campo)
    texto = f'Digite um valor para o campo: (Valor atual: "{atual}")' if atual else "Digite um valor para o campo: "
    context.user_data[MENSAGENS].append(await update.callback_query.edit_message_text(texto))
    return DIGITANDO

async def encerrar_edicao_lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.callback_query.data
    usuario_id = update.callback_query.from_user.id

    if data == str(CANCELAR):
        context.user_data[CAMPOS] = {}
        await menu_lembrete(update, context)
        return END

    lembrete = context.user_data.get(CAMPOS)
    if not lembrete or HORARIO not in lembrete:
        context.user_data[TEXTO] = MSG_HORARIO_OBRIGATORIO
        return await campo_lembrete(update, context)

    horario = parse_horario(lembrete.get(HORARIO, ""))
    if not horario:
        context.user_data[TEXTO] = MSG_HORARIO_INVALIDO
        return await campo_lembrete(update, context)
    lembrete[HORARIO] = horario

    mensagem = lembrete.get(MENSAGEM, "🔔 Lembrete diário!").strip()
    if context.user_data.get(EDITANDO):
        db.update_lembrete(context.user_data[EDITANDO][0], lembrete[HORARIO], mensagem)
        context.user_data[TEXTO] = "✅ Lembrete atualizado!"
        context.user_data[EDITANDO] = None
    else:
        db.add_lembrete(usuario_id, lembrete[HORARIO], mensagem)
        context.user_data[TEXTO] = MSG_SUCESSO

    context.user_data[CAMPOS] = {}
    await menu_lembrete(update, context)
    return END

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lembretes = db.get_lembretes_usuarios(update.callback_query.from_user.id)
    if not lembretes:
        context.user_data[TEXTO] = MSG_SEM_LEMBRETES
        return await menu_lembrete(update, context)

    buttons = [[InlineKeyboardButton("Voltar", callback_data=str(MENU_LEMBRETES))]] + [
        [InlineKeyboardButton(f"✏️ {horario} - {mensagem[:15]}...", callback_data=f"info_{id}")]
        for id, horario, mensagem in lembretes
    ]
    await update.callback_query.edit_message_text("📋 Seus Lembretes:", reply_markup=InlineKeyboardMarkup(buttons))
    return SELECAO_MENU_LEMBRETE

async def mostrar_detalhes_lembrete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lembrete_id = int(update.callback_query.data.split("_")[1])
    lembrete = db.get_lembrete_por_id(lembrete_id)
    context.user_data[EDITANDO] = lembrete

    if not lembrete:
        text = "❌ Lembrete não encontrado."
    else:
        text = f"📆 Lembrete:\nHorário: {lembrete[1]}\nMensagem: {lembrete[2]}"

    buttons = [
        [InlineKeyboardButton("Editar", callback_data=str(EDITAR)),
         InlineKeyboardButton("Excluir", callback_data=str(EXCLUIR))],
        [InlineKeyboardButton("Voltar", callback_data=str(MENU_LEMBRETES))]
    ]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECAO_MENU_LEMBRETE

async def apagar_lembretes(update: Update, _) -> int:
    await update.callback_query.edit_message_text("Certeza que deseja apagar todos os seus lembretes?", reply_markup=botoes_confirmacao("limpar_sim", "limpar_nao"))
    return SELECAO_MENU_LEMBRETE

async def apagar_lembrete(update: Update, _) -> int:
    await update.callback_query.edit_message_text("Confirma exclusão de lembrete?", reply_markup=botoes_confirmacao("limpar_sim", "limpar_nao"))
    return SELECAO_MENU_LEMBRETE

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    opcao = update.callback_query.data.split("_")[1]
    usuario_id = update.callback_query.message.chat_id

    if opcao == 'sim':
        if context.user_data.get(EDITANDO):
            db.delete_lembrete_usuario(usuario_id, context.user_data[EDITANDO][0])
        else:
            db.delete_lembretes_usuario(usuario_id)
        context.user_data[TEXTO] = MSG_SUCESSO
    else:
        context.user_data[TEXTO] = MSG_CANCELADO

    return await menu_lembrete(update, context)
