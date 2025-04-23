import calendar
from datetime import datetime
import os
from typing import Any
import holidays
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
    texto = context.user_data.pop(TEXTO, 'Gerando planilha...')
    buttons = [
        [
            InlineKeyboardButton(text='Gerar Planilha', callback_data=str(GERAR)),
        ],
        [InlineKeyboardButton(text='Voltar', callback_data=str(END))]
    ]
    await update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
    return ACAO_PLANILHA

async def menu_ponto_superior(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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