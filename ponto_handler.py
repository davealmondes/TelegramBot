import calendar
from datetime import datetime
import os
from typing import Any
import holidays
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes
from constantes import *
from database import Database
from utils import random_entrada, random_saida

db = Database()

async def menu_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the menu selection."""
    """Mostra o menu principal de ponto."""
    texto = context.user_data.pop(TEXTO, 'Menu de ponto...')
    context.user_data[EDITANDO] = None
    context.user_data[INICIO] = True

    buttons = [
        [
            InlineKeyboardButton(text='Gerar Planilha', callback_data=str(GERAR_PLANILHA)),
            InlineKeyboardButton(text='Baixar Planilha', callback_data=str(BAIXAR_PLANILHA))
        ],
        [InlineKeyboardButton(text='Voltar', callback_data=str(END))]
    ]

    await update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECAO_MENU_PONTO

async def gerar_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query.data == str(CANCELAR):
        mensagem: Message = context.user_data[MENSAGENS].pop()
        if mensagem:
            await mensagem.delete()
            
    mes = datetime.now().month
    ano = datetime.now().year
    meses = [f"{ mes - (-(12 - i) if mes -i <= 0 else i):02}-{ano - (1 if mes - i <= 0 else 0)}" for i in range(12)]
    buttons = [
        [InlineKeyboardButton(text=mes, callback_data=str(mes))] for mes in meses
    ]
    await update.callback_query.edit_message_reply_markup(InlineKeyboardMarkup([[InlineKeyboardButton(text='Voltar', callback_data=str(CANCELAR))]]))
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])
    mensagens.append(await context.bot.send_message(update.callback_query.from_user.id,
        "Selecione o mês para gerar a planilha.",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    ))
    return ACAO_PLANILHA

async def gerar_planilha_acoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = context.user_data.pop(TEXTO, 'Gerando planilha...')
    buttons = [
        [
            InlineKeyboardButton(text='Gerar dias faltantes.', callback_data=str(GERAR)),
            InlineKeyboardButton(text='Gerar dia específico.', callback_data=str(GERAR_DIA))
        ],
        [InlineKeyboardButton(text='Voltar', callback_data=str(END))]
    ]
    await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(buttons)) #callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
    return ACAO_PLANILHA

async def menu_ponto_superior(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await menu_ponto(update, context)
    return END

async def gerar_dia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ano = datetime.now().year
    mes = datetime.now().month
    dias = calendar.monthrange(ano, mes)[1]
    keyboard = [
         [f"{dia:02}", f"{dia +1:02}"] if dia + 1 <= dias else [f"{dia:02}"] for dia in range(1, dias + 1, 2)
    ]
    await update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Voltar', callback_data=str(CANCELAR))]]))
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])
    mensagens.append(await context.bot.send_message(update.callback_query.from_user.id,
        "Selecione o dia para gerar a planilha.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    ))
    return EDITANDO

async def campo_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe campos a preencher/editáveis do ponto."""
    
    if update.message:
        texto = "Campo atualizado..."
    else:

        if update.callback_query.data == str(EDITAR):
            context.user_data[CAMPOS] = {
                ENTRADA: context.user_data[EDITANDO][1],
                SAIDA: context.user_data[EDITANDO][2],
                OBSERVACAO: context.user_data[EDITANDO][3]
            }
            texto = "Editando lembrete..."
        else:
            if context.user_data.get(INICIO):
                context.user_data[CAMPOS] = {}
                context.user_data[INICIO] = False
            texto = context.user_data.pop(TEXTO, "Adicionando lembrete...")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Entrada", callback_data=str(ENTRADA)),
        InlineKeyboardButton("Saida", callback_data=str(SAIDA)),
        InlineKeyboardButton("Observação", callback_data=str(OBSERVACAO))],
        [InlineKeyboardButton("Cancelar", callback_data=str(CANCELAR)),
        InlineKeyboardButton("Concluir", callback_data=str(END))]
    ])

    if update.message:
        await update.message.reply_text(texto, reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_text(texto, reply_markup=keyboard)
    return SELECIONANDO_CAMPO

async def encerrar_edicao_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.callback_query.data
    usuario_id = update.callback_query.from_user.id

    if data == str(CANCELAR):
        context.user_data[CAMPOS] = {}
        context.user_data[TEXTO] = "Edição cancelada..."
        await menu_ponto(update, context)
        return END

    if data == str(END):
        dia = int(update.message.text) if update.message else int(update.callback_query.data)
        data_str: str = datetime.now().strftime(f"%Y-{datetime.now().month:02}-{dia:02}")
        entrada = context.user_data[CAMPOS].get(ENTRADA)
        saida = context.user_data[CAMPOS].get(SAIDA)
        observacao = context.user_data[CAMPOS].get(OBSERVACAO)

        db.insert_ponto(data_str, dia, entrada, saida, observacao)
        context.user_data[TEXTO] = "Ponto registrado com sucesso."
        await menu_ponto(update, context)
        return END

async def gerar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pontos_existentes: list[Any] = db.get_data_pontos()
    ano: int = datetime.now().year
    mes: int = datetime.now().month
    hoje: int = datetime.now().day
    feriados = holidays.BR(years=ano, state='SP', language='pt_BR')
    for dia in range(1, calendar.monthrange(ano, mes)[1] + 1):
        if dia > hoje:
            break
        data: datetime = datetime(ano, mes, dia)
        data_str: str = data.strftime("%Y-%m-%d")
        if (data_str,) in pontos_existentes:
            continue
        if data.weekday() == 1: # Terça-feira
            entrada = saida = None
            feriado_nome = 'Presencial'
        elif data.weekday() >= 5:
            entrada = saida = feriado_nome = None
        elif data in feriados:
            entrada = saida = None
            feriado_nome = feriados[data]
        else:
            entrada_dt = random_entrada(data)
            saida_dt = random_saida(entrada_dt)
            entrada = entrada_dt.strftime("%H:%M")
            saida = saida_dt.strftime("%H:%M")
            feriado_nome = None
        db.insert_ponto(data_str, dia, entrada, saida, feriado_nome)
    context.user_data[TEXTO] = f"Planilha gerada com sucesso para."
    await menu_ponto(update, context)
    return END

async def baixar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pontos: pd.DataFrame = db.get_pontos()
    if pontos.empty:
        context.user_data[TEXTO] = f"Não há pontos registrados."
        return await menu_ponto(update, context)

    # Corrigir coluna para exportação
    pontos["entrada"] = pontos.apply(lambda row: "PRESENCIAL" if row['feriado'] == 'Presencial' else ("FERIADO" if row['feriado'] else row['entrada']), axis=1)
    pontos["feriado"] = pontos.apply(lambda row: "" if row['feriado'] == 'Presencial' else row['feriado'], axis=1)
    pontos = pontos[["dia", "entrada", "saida", "feriado"]]
    pontos.columns = ["Dia", "Entrada", "Saída", "Observação"]

    # Exportar com mesclagem dos feriados
    pasta: str = f"uploads/{update.callback_query.from_user.id}"
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo: str = f"{pasta}/ponto.xlsx"
    with pd.ExcelWriter(nome_arquivo, engine='xlsxwriter') as writer:
        pontos.to_excel(writer, sheet_name='Ponto', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Ponto']

        center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
        
        for i, row in pontos.iterrows():
            if pd.isna(row['Saída']) and not pd.isna(row['Entrada']):
                if "FERIADO" in row['Entrada'] or "PRESENCIAL" in row['Entrada']:
                    worksheet.merge_range(i + 1, 1, i + 1, 2, row['Entrada'], center_format)

    await context.bot.send_document(update.callback_query.from_user.id, open(nome_arquivo, "rb"))
    context.user_data[TEXTO] = "Planilha resgatada..."
    return SELECAO_MENU_PONTO